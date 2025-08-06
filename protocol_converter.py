import json
import uuid

import requests
import os.path
import glob
import traceback

import pandas as pd

from Protocols.scripts.mine_pl_v2 import readme_path

text__ = """
 ------------- TRANSFERRING WATER ------------
Setting Temperature Module temperature to 4.0 °C (rounded off to nearest integer)

Picking up tip from A1 of Opentrons OT-2 96 Filter Tip Rack 200 µL on 6
Transferring 21.5 from A1 of Agilent 1 Well Reservoir 290 mL on 1 to A1 of Bio-Rad 96 Well Plate 200 µL PCR on 3
        Aspirating 21.5 uL from A1 of Agilent 1 Well Reservoir 290 mL on 1 at 92.86 uL/sec
        Dispensing 21.5 uL into A1 of Bio-Rad 96 Well Plate 200 µL PCR on 3 at 92.86 uL/sec
Dropping tip into A1 of Opentrons Fixed Trash on 12
Deactivating Temperature Module


 ------------- TRANSFERRING DNA ------------

Engaging Magnetic Module
Picking up tip from B1 of Opentrons OT-2 96 Filter Tip Rack 200 µL on 6
Transferring 10.5 from A1 of Bio-Rad 96 Well Plate 200 µL PCR on 2 to A1 of Bio-Rad 96 Well Plate 200 µL PCR on 3
        Aspirating 10.5 uL from A1 of Bio-Rad 96 Well Plate 200 µL PCR on 2 at 92.86 uL/sec
        Dispensing 10.5 uL into A1 of Bio-Rad 96 Well Plate 200 µL PCR on 3 at 92.86 uL/sec
Dropping tip into A1 of Opentrons Fixed Trash on 12

Delaying for 5 minutes and 0.0 seconds
Disengaging Magnetic Module

 ------------- Operating the heater shaker------------

Setting Target Temperature of Heater-Shaker to 37 °C
Waiting for Heater-Shaker to reach target temperature
Setting Heater-Shaker to Shake at 200 RPM and waiting until reached
Delaying for 60 minutes and 0.0 seconds
Deactivating Heater


"""
import re
from collections import defaultdict
from typing import List, Dict, Optional, Union, Sequence, Literal  # ← 提前导入


# ---------------------------------------------------------------------------
# ---------- Heater‑Shaker phase parser ----------
def build_heater_shaker_dict(step_lines: List[str]) -> Dict:
    """
    Extracts key parameters for a Heater‑Shaker phase:
    target_temperature, shake_speed, duration, wait flag, deactivate flags
    """
    data = {
        "template": "heater_shaker",
        "target_temperature": None,
        "wait_for_temp": False,
        "shake_speed": None,
        "duration_minutes": None,
        "deactivate_heater": False,
        "deactivate_shaker": False
    }
    for line in step_lines:
        if line.startswith("Setting Target Temperature of Heater-Shaker"):
            data["target_temperature"] = extract_float_after_keyword(line, "to")
        elif line.startswith("Waiting for Heater-Shaker"):
            data["wait_for_temp"] = True
        elif line.startswith("Setting Heater-Shaker to Shake at"):
            m = re.search(r'Shake at ([\d.]+) RPM', line)
            if m:
                data["shake_speed"] = float(m.group(1))
        elif line.startswith("Delaying"):
            dm = re.search(r'Delaying for (\d+) minutes', line)
            if dm:
                data["duration_minutes"] = int(dm.group(1))
        elif line.startswith("Deactivating Heater"):
            data["deactivate_heater"] = True
        elif line.startswith("Deactivating Shaker"):
            data["deactivate_shaker"] = True
    return data
# -----------------------------------------------


import re
from typing import List, Dict, Optional, Union, Sequence, Literal

def extract_float_after_keyword(text: str, keyword: str) -> Optional[float]:
    match = re.search(fr'{keyword} ([\d.]+)', text)
    return float(match.group(1)) if match else None

def extract_container_from_line(line: str, keyword: str) -> Optional[Dict[str, Union[str, int, float]]]:
    # 匹配 from 模式
    match = re.search(fr'{keyword} [\d.]+ uL .*?from ([A-H]\d+) of (.*?) on (\d+).*?at ([\d.]+) uL/sec', line)
    if not match:
        # 匹配 into 模式
        match = re.search(fr'{keyword} [\d.]+ uL .*?into ([A-H]\d+) of (.*?) on (\d+).*?at ([\d.]+) uL/sec', line)
    if match:
        return {
            "well": match.group(1),
            "labware": match.group(2).strip(),
            "slot": int(match.group(3))
        }
    return None

def is_full_row(wells: List[str]) -> bool:
    """Returns True if all wells in a row (e.g., A1 to A12) are included"""
    if len(wells) < 12:
        return False
    row = wells[0][0]
    indices = sorted([int(w[1:]) for w in wells if w[0] == row])
    return indices == list(range(1, 13))

def build_transfer_liquid_dict_complete(step_lines: List[str]) -> Dict:
    asp_vols = []
    dis_vols = []
    sources = []
    targets = []
    tip_rack_info = None
    asp_flow_rate = None
    dis_flow_rate = None
    blow_out_air_volume = 0.0
    mix_times = 0
    mix_vol = None
    mix_rate = None
    touch_tip = False
    delays = None

    # --- module flags that accompany liquid handling ---
    temperature_target = None
    temperature_deactivate = False
    magnetic_engage = False
    magnetic_delay_minutes = None
    magnetic_disengage = False
    # ---------------------------------------------------

    aspirate_index = None
    dispense_index = None
    mixing_indices = []

    # First pass: gather line indices for logic
    for i, line in enumerate(step_lines):
        if line.startswith(" "):  # ignore indented substeps
            continue
        stripped = line.strip()
        if stripped.startswith("Aspirating") and "from" in stripped and aspirate_index is None:
            aspirate_index = i
        elif stripped.startswith("Dispensing") and "into" in stripped and dispense_index is None:
            dispense_index = i
        elif stripped.startswith("Mixing"):
            mixing_indices.append(i)
        elif stripped.startswith("Picking up tip"):
            tip_match = re.search(r'from ([A-H]\d+) of (.*?) on (\d+)', stripped)
            if tip_match:
                tip_rack_info = {
                    "well": tip_match.group(1),
                    "type": tip_match.group(2).strip(),
                    "slot": int(tip_match.group(3))
                }

    # Determine mix_stage
    mix_stage = "none"
    for idx in mixing_indices:
        if aspirate_index is not None and idx < aspirate_index:
            mix_stage = "before" if mix_stage == "none" else "both"
        elif dispense_index is not None and idx > dispense_index:
            mix_stage = "after" if mix_stage == "none" else "both"

    # Second pass: parse actual values
    for i, line in enumerate(step_lines):
        if line.startswith(" "):  # ignore indented substeps
            continue
        stripped = line.strip()

        if stripped.startswith("Aspirating") and "from" in stripped:
            asp_vols = extract_float_after_keyword(stripped, "Aspirating")
            source = extract_container_from_line(stripped, "Aspirating")
            if source:
                sources.append(source)
            asp_flow_rate = extract_float_after_keyword(stripped, "at")
        elif stripped.startswith("Dispensing") and "into" in stripped:
            dis_vols = extract_float_after_keyword(stripped, "Dispensing")
            target = extract_container_from_line(stripped, "Dispensing")
            if target:
                targets.append(target)
            dis_flow_rate = extract_float_after_keyword(stripped, "at")
        
        elif stripped.startswith("Transferring"):
            asp_vols = extract_float_after_keyword(stripped, "Aspirating")
            dis_vols = extract_float_after_keyword(stripped, "Dispensing")
            source = extract_container_from_line(stripped, "Aspirating")
            if source:
                sources.append(source)
            target = extract_container_from_line(stripped, "Dispensing")
            if target:
                targets.append(target)    
                # 新增：分别提取Aspirating和Dispensing的流速
            asp_match = re.search(r"Aspirating.*?at ([\d.]+)", stripped)
            dis_match = re.search(r"Dispensing.*?at ([\d.]+)", stripped)
            asp_flow_rate = float(asp_match.group(1)) if asp_match else None
            dis_flow_rate = float(dis_match.group(1)) if dis_match else None

        # Temperature Module commands
        elif stripped.startswith("Setting Temperature Module temperature"):
            temperature_target = extract_float_after_keyword(stripped, "to")
        elif stripped.startswith("Deactivating Temperature Module"):
            temperature_deactivate = True

        # Magnetic Module commands
        elif stripped.startswith("Engaging Magnetic Module"):
            magnetic_engage = True
        elif stripped.startswith("Disengaging Magnetic Module"):
            magnetic_disengage = True
        elif stripped.startswith("Delaying") and magnetic_engage and not magnetic_disengage:
            delay_match2 = re.search(r'Delaying for (\d+) minutes', stripped)
            if delay_match2:
                magnetic_delay_minutes = int(delay_match2.group(1))

        elif stripped.startswith("Air gap"):
            blow_out_air_volume = extract_float_after_keyword(stripped, "Aspirating")
        elif stripped.startswith("Mixing"):
            mix_match = re.search(r'Mixing (\d+) times.*?(\d+\.?\d*)', stripped)
            if mix_match:
                mix_times = [int(mix_match.group(1))]
                mix_vol = float(mix_match.group(2))
                mix_rate = extract_float_after_keyword(stripped, "at")
        elif "Touching tip" in stripped:
            touch_tip = True
        elif stripped.startswith("Delaying"):
            delay_match = re.search(r'Delaying for \d+ minutes and ([\d.]+)', stripped)
            if delay_match:
                delays = [int(float(delay_match.group(1)))]

    # Determine 96-well multichannel use
    source_wells = [s['well'] for s in sources]
    target_wells = [t['well'] for t in targets]
    is_96_well = is_full_row(source_wells) and is_full_row(target_wells)

    basic_info = {
        "sources": sources,
        "targets": targets,
        "tip_racks": [tip_rack_info] if tip_rack_info else [],
        "use_channels": None,
        "asp_vols": asp_vols,
        "asp_flow_rates": [asp_flow_rate] if asp_flow_rate else None,
        "disp_vols": dis_vols,
        "dis_flow_rates": [dis_flow_rate] if dis_flow_rate else None,
        "offsets": None,
        "touch_tip": touch_tip,
        "liquid_height": None,
        "blow_out_air_volume": [blow_out_air_volume] if blow_out_air_volume else [0.0],
        "is_96_well": is_96_well,
        "mix_stage": mix_stage,
        "mix_times": mix_times,
        "mix_vol": mix_vol,
        "mix_rate": mix_rate,
        "mix_liquid_height": None,
        "delays": delays
    }

    if magnetic_engage or magnetic_disengage:
        template = "liquid_handler-transfer_with_magnetic"
        return {
            "template": template,
            **basic_info,
            "magnetic_engage": magnetic_engage,
            "magnetic_delay_minutes": magnetic_delay_minutes,
            "magnetic_disengage": magnetic_disengage
        }
    elif temperature_target is not None:
        template = "liquid_handler-transfer_with_temperature"
        return {
            "template": template,
            **basic_info,
            "temperature_target": temperature_target,
            "temperature_deactivate": temperature_deactivate
        }
    else:
        template = "liquid_handler-transfer_liquid"
        return {"template": template, **basic_info}


def merge_same_slot_phases(param_dicts: List[Dict]) -> List[Dict]:
    merged = []
    last_key = None
    last_block = None

    for d in param_dicts:
        if not d.get("sources") or not d.get("targets"):
            merged.append(d)
            last_key = None
            last_block = None
            continue

        key = (
            d["template"],
            d["sources"][0]["slot"],
            d["targets"][0]["slot"],
            d.get("mix_stage"),
            d.get("is_96_well"),
            d.get("touch_tip"),
            d.get("blow_out_air_volume", [0])[0]
        )

        if last_key == key and last_block:
            for field in ['asp_vols', 'disp_vols', 'sources', 'targets',
                          'tip_racks', 'asp_flow_rates', 'dis_flow_rates',
                          'blow_out_air_volume', 'delays']:
                if field in d:
                    if not isinstance(last_block[field], list):
                        last_block[field] = [last_block[field]]
                    last_block[field].extend(d[field] if isinstance(d[field], list) else [d[field]])
        else:
            merged.append(d)
            last_key = key
            last_block = d

    return merged


def process_liquid_handler_log(filename: str = "test.log", text: str = "") -> List[Dict]:
    """
    Process the liquid handler log text and return a list of dictionaries
    containing the parsed information.
    """
    if not text:
        text = open(filename, "r", encoding="utf-8").read()

    # Define regex patterns for module start commands

    MODULE_START_PATTERNS = [
        r"Setting Target Temperature of Heater-Shaker",
        r"Engaging Magnetic Module"
    ]

    # Compile once for quick matching of Heater‑Shaker commands
    module_start_regex = re.compile("|".join(MODULE_START_PATTERNS))

    # Input: Multiline protocol text
    # with open("/mnt/data/opentrons_protocol.txt", "r", encoding="utf-8") as file:
    #     lines = file.readlines()
    text_ = text.replace("\n        ", ";")
    text_ = text_.replace("\n\t", ";")
    lines = text_.strip().split('\n')

    excluded_patterns = [
        "/Users",
        "Congratulations!",
        "Caught exception:",
        "Deck calibration",
        "WARNING",
        "Protocol complete",
        "Seal and shake",
        "Pausing robot operation",
        "TRANSFERRING",
        "Centrifuge"
    ]
    steps = [line.replace(";", "\n        ").strip() for line in lines if line.strip() and
             not line.startswith("        ") and not line.startswith("~~") and
             not "--" in line and not line.endswith(":") and
             not sum([line.startswith(patt) for patt in excluded_patterns])]

    # Define prepositions to split on
    PREPOSITIONS = [' from ', ' to ', ' on ', ' of ', ' into ']

    # Structure for collecting parsed results
    parsed_steps = []

    # Parse each line
    for line in steps:
        tokens = [line]
        for prep in PREPOSITIONS:
            new_tokens = []
            for token in tokens:
                new_tokens.extend(token.split(prep))
            tokens = new_tokens
        parsed_steps.append({
            "raw": line,
            "tokens": [t.strip() for t in tokens if t.strip()]
        })

    # -------- Build phases: split on Heater‑Shaker OR liquid‑logic breaks --------
    grouped_phases = []
    current_phase = []
    aspirating_seen = False
    last = ""

    for step in parsed_steps:
        line_raw = step["raw"]

        # ① 如果遇到 Heater‑Shaker 指令，立即结束当前 phase
        if module_start_regex.search(line_raw):
            if current_phase:
                grouped_phases.append(current_phase)
                current_phase = []
                aspirating_seen = False    # reset for next liquid series

        # ② 维持原有移液逻辑的切割
        if (line_raw.startswith("Aspirating") and not ("Picking up tip" in last) and not ("Moving to" in last) and not ("Transferring" in last)) \
            or ("Picking up tip" in line_raw) \
            or ("Moving to" in line_raw and not ("Picking up tip" in last)):
            if aspirating_seen:
                grouped_phases.append(current_phase)
                current_phase = []
            aspirating_seen = True

        last = line_raw
        current_phase.append(line_raw)

    # 别忘了收集最后一个 phase
    if current_phase:
        grouped_phases.append(current_phase)

    print(grouped_phases)
     # -------- Build dicts for each phase (liquid vs HS) --------
    outputs = []
    for phase_lines in grouped_phases:
        if any("Heater-Shaker" in l for l in phase_lines):
            outputs.append(build_heater_shaker_dict(phase_lines))
        else:
            outputs.append(build_transfer_liquid_dict_complete(phase_lines))
    # -----------------------------------------------------------

    final_outputs = merge_same_slot_phases(outputs)

    # ------------- Output the final DataFrame -------------
    print(final_outputs)
    json.dump(final_outputs, open(f"{filename}.json", "w"), indent=4)
    # ddf = pd.DataFrame({"Phase {}".format(i + 1): phase for i, phase in enumerate(final_outputs)})
    return final_outputs


def extract_labware_info_from_json(json_data: dict) -> list:
    """
    从 Opentrons JSON 配置中提取板位信息，转换为结构化格式。
    """
    labware_list = json_data.get("labware", [])

    output = []
    for i, lw in enumerate(labware_list):
        output.append({
            "id": lw.get("name"),
            "parent": "deck",
            "slot_on_deck": int(lw.get("slot")),
            "class_name": lw.get("type"),
            "liquid_type": [],      # 默认填写
            "liquid_volume": [],                # 默认每个液体体积
            "liquid_input_wells": []                # 默认输入孔位索引
        })

    return output


# Re-import necessary libraries after kernel reset
from typing import List, Dict, Any
import networkx as nx
import json

def build_protocol_graph(labware_info: List[Dict[str, Any]], protocol_steps: List[Dict[str, Any]]) -> nx.DiGraph:
    """
    构建包含物料创建和步骤节点的 protocol graph。
    每个节点代表一个操作或物料；每条边表示数据/物料流动。
    """
    G = nx.DiGraph()
    slot_last_writer = {}  # 记录每个 slot 上次的输出节点（transfer/heater_shaker）

    labware_ids = {lw["id"] for lw in labware_info}
    # Step 1: 添加物料创建节点
    for labware in labware_info:
        node_id = labware["id"]
        G.add_node(node_id, template="host_node-add_resource_from_outer_easy", **labware)
        slot = labware["slot_on_deck"]
        slot_last_writer[slot] = node_id

    # Step 2: 添加 protocol 步骤节点及边
    for i, step in enumerate(protocol_steps):
        node_id = f"step_{i+1}"
        G.add_node(node_id, **step)

        if step["template"].startswith("liquid_handler"):
            for port_type, port_name in [("sources", "sources"), ("targets", "targets"), ("tip_racks", "tip_racks")]:
                items = step.get(port_type, [])
                item = items[0]
                slot = item.get("slot")
                if slot is not None:
                    prev_node = slot_last_writer.get(slot)
                    if prev_node:
                        source_port = "labware" if prev_node in labware_ids else f"{port_name}_out"
                        G.add_edge(prev_node, node_id, source_port=source_port, target_port=port_name)
                    if port_type != "tip_racks":
                        slot_last_writer[slot] = node_id
                G.nodes[node_id][port_type] = step[port_type] = [item["well"] for item in items]

        elif step["template"] == "heater_shaker":
            slot = step.get("targets", [{}])[0].get("slot", None)
            if slot is not None:
                prev_node = slot_last_writer.get(slot)
                if prev_node:
                    G.add_edge(prev_node, node_id, source_port="plate", target_port="plate")
                slot_last_writer[slot] = node_id

    return G


def parse_protocol(name: str):
    logfile = f"/Users/chang/Design_projects/LabOS/opentrons/Protocols/success/{name}.ot2.apiv2.log"
    infofile = f"/Users/chang/Design_projects/LabOS/opentrons/Protocols/protoBuilds/{name}/{name}.ot2.apiv2.py.json"

    if not os.path.exists(logfile) or not os.path.exists(infofile):
        print(f"File not found: {logfile} or {infofile}")
        return

    protocol_steps = process_liquid_handler_log(logfile)
    with open(infofile, "r") as f:
        labware_data = json.load(f)
    labware_info = extract_labware_info_from_json(labware_data)
    protocol_graph = build_protocol_graph(labware_info, protocol_steps)
    data = nx.node_link_data(protocol_graph)
    # get edges for each node and append to node data

    node_dict = {}
    for i, node in enumerate(data["nodes"]):
        onode = {"template": node.pop("template"), "id": node["id"]}
        onode["params"] = {}
        onode["params"]["default"] = node
        data["nodes"][i] = onode.copy()
        onode["handles"] = {}
        for edge_data in data["links"]:
            source, target = edge_data["source"], edge_data["target"]
            if onode["id"] == target:
                onode["handles"][edge_data["target_port"]] = [source]

        node_dict[onode["id"]] = onode
    with open(f"/Users/chang/Design_projects/LabOS/opentrons/Protocols/protocols/{name}/graph.json", "w") as f:
        json.dump(data, f, indent=4)
    with open(f"/Users/chang/Design_projects/LabOS/opentrons/Protocols/protocols/{name}/nodes.json", "w") as f:
        json.dump(node_dict, f, indent=4)

    return data


import requests

import http.client
import json

def publish_protocol(
    name: str,
    data: dict,

    base_url = "https://uni-lab.bohrium.com"
) -> Dict:
    """
    将 protocol_graph 发布到 Uni-Lab API。
    参数：
        protocol_graph: 已构建的 NetworkX 有向图
        name: 工作流程名称
        readme_path: README 文件路径，用于生成 title 和 description
        token: 用户授权的 Bearer token（用于认证）
    返回：
        包含 uuid 和 URL 的响应内容
    """
    readme_path = f"/Users/chang/Design_projects/LabOS/opentrons/Protocols/protocols/{name}/README.md"
    readme_detail = f"/Users/chang/Design_projects/LabOS/opentrons/Protocols/protoBuilds/{name}/README.json"

    categories_d = json.load(open(readme_detail, "r", encoding="utf-8")).get("categories", {})
    categories = []
    for k, v in categories_d.items():
        categories.append(k)
        categories += v

    # cookies = {
    #     "access_token": access_token,
    #     "refresh_token": refresh_token
    # }
    #
    # headers = {
    #     "Content-Type": "application/json",
    #     "Accept": "application/json"
    # }
    headers = {
        "Content-Type": "application/json",
        "Authorization": "lab 5A43D7A9",
    }

    with open(readme_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        title = lines[0].strip()[2:] if lines is not None else name
        description = "".join(lines[1:]).strip() if len(lines) > 1 else ""

    # Step 1: POST to /api/workflows/
    graph_data = {"name": title, **data}
    payload = json.dumps(graph_data)
    workflow_url = f"{base_url}/api/v1/workflow/"
    resp1 = requests.post(workflow_url, json=graph_data, headers=headers)
    resp1.raise_for_status()

    workflow_info = resp1.json()
    print("Workflow创建成功:", workflow_info)
    workflow_uuid = workflow_info["uuid"]

    # Step 2: POST to /api/workflows/library

    lib_payload = {
        "workflow_uuid": workflow_uuid,
        "title": title,
        "description": description,
        "labels": ["Synthetic Biology"] + categories,
    }

    payload = json.dumps(lib_payload)
    library_url = f"{base_url}/api/flociety/vs/workflows/library/"
    resp2 = requests.post(library_url, json=lib_payload, headers=headers)
    resp2.raise_for_status()

    library_info = resp2.json()
    print("Library添加成功:", library_info)

    return {
        "uuid": workflow_uuid,
        "workflow_url": workflow_info.get("url"),
        "title": title,
        "description": description
    }


LAB_NAME = "SynBioFactory"

DEVICE_NAME = "liquid_handler"


if __name__ == "__main__":
    conn = http.client.HTTPSConnection("uni-lab.bohrium.com")
    # 测试代码
    # process_liquid_handler_log("/Users/chang/Design_projects/LabOS/opentrons/Protocols/success/sci-lucif-assay4.ot2.apiv2.log")
    # process_liquid_handler_log(text=text__)
    paths = sorted(glob.glob("/Users/chang/Design_projects/LabOS/opentrons/Protocols/protocols/*"))
    for d in paths:
        name = os.path.basename(d)
        try:
            # data = parse_protocol(name)
            data = json.load(open(f"/Users/chang/Design_projects/LabOS/opentrons/Protocols/graph/{name}.graph.json", "r"))
            node_dict = {}
            for i, node in enumerate(data["nodes"]):
                onode = {"template": node.pop("template"), "id": str(uuid.uuid4())}

                if onode["template"] == "create_resource":
                    onode["template"] = f"{LAB_NAME}-host_node-{onode['template']}"
                else:
                    onode["template"] = f"{LAB_NAME}-{DEVICE_NAME}-{onode['template']}"
                onode["params"] = {}
                onode["params"]["default"] = node
                data["nodes"][i] = onode.copy()
            if data is not None:
                publish_protocol(name, data)
            else:
                print(f"Failed to parse protocol: {name}")
        except:
            print(f"Error processing protocol: {name}")
            traceback.print_exc()
            continue
