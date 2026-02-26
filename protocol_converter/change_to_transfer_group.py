import json
import os
from pathlib import Path
from pprint import pprint
import re
from typing import List, Dict, Any, Optional, Tuple

_DEF_WELL_COUNTS = (384, 96, 48, 24)

def _parse_well_count(name: str) -> Optional[int]:
    s = name.lower()
    for k in _DEF_WELL_COUNTS:
        # 匹配独立数字（避免把 96 匹配到 196 等）
        if re.search(rf'(^|[^0-9]){k}([^0-9]|$)', s):
            return k
    return None

def _parse_capacity_ul(name: str) -> Optional[float]:
    s = name.lower()
    m = re.search(r'(\d+(?:\.\d+)?)(\s*(?:u?l|[µμ]l|ml))', s, re.IGNORECASE)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2).strip().lower()
    if unit == 'ml':
        return val * 1000.0
    # 兼容 'ul' / 'u l' / 'µl' / 'μl'
    return val

def get_action_list(steps_file):
    """从steps JSON文件提取action list，包含体积和流速信息"""
    with open(steps_file, "r") as f:
        data = json.load(f)

    # 收集所有step中的dispense wells（所有transfer的目标都是相同的）
    all_dispense_wells = set()
    all_dispense_vols = []
    all_dispense_flow_rates = []

    # 按source well分组收集aspirate信息
    source_to_vols = {}  # {(slot, well): [vol1, vol2, ...]}
    source_to_flow_rates = {}  # {(slot, well): [flow_rate1, flow_rate2, ...]}
    source_to_tip_racks = {}  # {(slot, well): set([slot1, slot2, ...])}

    current_tip_rack_slot = None  # 当前使用的tip rack slot

    for phase_idx, phase in enumerate(data):
        for step in phase:
            if step['action'] == "pick_tip":
                # 记录当前pick的tip rack slot
                current_tip_rack_slot = step['tip_rack']['slot']

            elif step['action'] == "aspirate":
                source_key = (step['source']['slot'], step['source']['well'])
                if source_key not in source_to_vols:
                    source_to_vols[source_key] = []
                    source_to_flow_rates[source_key] = []
                    source_to_tip_racks[source_key] = set()

                # 记录使用的tip rack slot
                if current_tip_rack_slot is not None:
                    source_to_tip_racks[source_key].add(current_tip_rack_slot)

                # 提取体积信息
                if 'vol' in step:
                    source_to_vols[source_key].append(step['vol'])
                # 提取流速信息
                if 'flow_rate' in step:
                    source_to_flow_rates[source_key].append(step['flow_rate'])

            elif step['action'] == "dispense":
                # 跳过 blow_out 操作（体积为 -1 或目标是 trash）
                # blow_out 是排空枪头中的残留液体，不是真正的移液操作，不应该被识别为 dispense
                vol = step.get('vol', 0)
                target = step.get('target', {})
                labware = target.get('labware', '').lower() if target else ''

                # 检查是否是 blow_out 操作（排空枪头）
                is_blowout = (
                    vol == -1 or  # 体积为 -1 表示 blow_out（排空枪头）
                    'trash' in labware or  # 目标是 trash（通常用于排空枪头）
                    target.get('slot') == 12  # Opentrons Fixed Trash 通常在 slot 12
                )

                if not is_blowout:
                    all_dispense_wells.add((step['target']['slot'], step['target']['well']))
                    # 提取体积信息
                    if 'vol' in step:
                        all_dispense_vols.append(step['vol'])
                    # 提取流速信息
                    if 'flow_rate' in step:
                        all_dispense_flow_rates.append(step['flow_rate'])

    # 计算dispense的平均值
    avg_dis_vol = sum(all_dispense_vols) / len(all_dispense_vols) if all_dispense_vols else 0
    avg_dis_flow_rate = sum(all_dispense_flow_rates) / len(all_dispense_flow_rates) if all_dispense_flow_rates else 0

    # 为每个source well生成一个action
    action_list = []
    for source_well, vols in source_to_vols.items():
        flow_rates = source_to_flow_rates[source_well]
        tip_rack_slots = source_to_tip_racks[source_well]

        # 计算平均体积和流速（用于向后兼容）
        avg_asp_vol = sum(vols) / len(vols) if vols else 0
        avg_asp_flow_rate = sum(flow_rates) / len(flow_rates) if flow_rates else 0

        # 生成tip_racks字符串（转换为tiprack_X格式）
        tip_racks = f"tiprack_{sorted(tip_rack_slots)[0]}" if tip_rack_slots else ""

        # 生成数组格式的体积和流速（单个source对应多个dispense）
        num_targets = len(all_dispense_wells)
        asp_vols_array = []
        asp_flow_rates_array = []
        dis_vols_array = []
        dis_flow_rates_array = []

        for i in range(num_targets):
            # aspirate的体积和流速：对于同一个source，所有dispense使用相同的
            asp_vols_array.append(avg_asp_vol)
            asp_flow_rates_array.append(avg_asp_flow_rate)

            # dispense的体积和流速：如果有对应的值就使用，否则使用平均值
            if i < len(all_dispense_vols):
                dis_vols_array.append(all_dispense_vols[i])
            else:
                dis_vols_array.append(avg_dis_vol)

            if i < len(all_dispense_flow_rates):
                dis_flow_rates_array.append(all_dispense_flow_rates[i])
            else:
                dis_flow_rates_array.append(avg_dis_flow_rate)

        action_list.append({
            "phase": len(action_list),  # 每个source对应一个phase索引
            "aspirate": [source_well],  # 单个source well
            "dispense": list(all_dispense_wells),  # 所有dispense wells
            "asp_vol": avg_asp_vol,  # 保留用于向后兼容
            "dis_vol": avg_dis_vol,  # 保留用于向后兼容
            "asp_flow_rate": avg_asp_flow_rate,  # 保留用于向后兼容
            "dis_flow_rate": avg_dis_flow_rate,  # 保留用于向后兼容
            "asp_vols": asp_vols_array,  # 新增：数组格式
            "dis_vols": dis_vols_array,  # 新增：数组格式
            "asp_flow_rates": asp_flow_rates_array,  # 新增：数组格式
            "dis_flow_rates": dis_flow_rates_array,  # 新增：数组格式
            "tip_racks": tip_racks  # 新增：使用的tip racks
        })

    return action_list


def extract_labware_info_from_json(json_data: dict, total_slots: int) -> Tuple[list, dict]:
    """
    从 Opentrons JSON 配置中提取板位信息，并根据 `total_slots` 进行槽位映射：
      - 若 total_slots >= 12：不映射，保留原始 slot。
      - 若 total_slots < 12：将出现过的原始 slot（去重、按出现顺序）紧凑映射到 1..total_slots。
        若去重后的原始 slot 数量 > total_slots，则报错。
    返回:
      output: 规范化后的 labware 列表
      replace_map: {原始slot: 新slot}
    """
    labware_list = json_data.get("labware", [])
    if not isinstance(labware_list, list):
        raise ValueError("json_data['labware'] must be a list.")

    if len(labware_list) > 12:
        # 你原来文本里已经放宽到 12，这里沿用
        raise ValueError("Labware list exceeds 12 items, which is not supported by the PRCXI 9320.")

    # 1) 收集"原始 slot"出现顺序（去重），转换为整数
    orig_slots_in_order = []
    for lw in labware_list:
        s = lw.get("slot")
        if s is None:
            raise ValueError(f"Labware item missing 'slot': {lw}")
        # 转换为整数
        try:
            s_int = int(s)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid slot value (must be convertible to int): {s}")
        if s_int not in orig_slots_in_order:
            orig_slots_in_order.append(s_int)

    # 2) 计算映射表 replace_map
    replace_map: Dict[int, int] = {}

    if total_slots >= 12:
        # 不映射：保留原始 slot
        replace_map = {s: s for s in orig_slots_in_order}
    else:
        # 紧凑映射到 1..total_slots
        if len(orig_slots_in_order) > total_slots:
            raise ValueError(
                f"Cannot compact-map {len(orig_slots_in_order)} distinct slots into total_slots={total_slots}."
            )
        # 依出现顺序映射：第1个 → 1，第2个 → 2，…
        replace_map = {s: i + 1 for i, s in enumerate(orig_slots_in_order)}

    # 3) 组装输出
    output = []
    container_char = ['wellplate', 'well', 'pcr']

    for lw in labware_list:
        class_name = (lw.get("type") or "").strip()
        if not class_name:
            raise ValueError(f"Labware item missing 'type': {lw}")
        # 清洗 class_name 中的点和特殊字符
        class_name = re.sub(r'\.', 'point', class_name)
        class_name = re.sub(r'[µμ]', 'u', class_name)

        # 默认体积
        liquid_vol = 200.0
        # 若名字看起来像盛液板，尝试解析体积
        if any(c in class_name.lower() for c in container_char):
            # 先小数：12.5ul / 0.5ml
            m = re.search(r'(\d+)\.(\d+)([mu]l)', class_name, re.IGNORECASE)
            if m:
                num1, num2, unit = m.groups()
                value = float(f"{num1}.{num2}")
                if unit.lower() == "ml":
                    liquid_vol = value * 1000.0
                else:  # 'ul'
                    liquid_vol = value
            else:
                # 再整数：200ul / 1ml
                m2 = re.search(r'(\d+)([mu]l)', class_name, re.IGNORECASE)
                if m2:
                    num, unit = m2.groups()
                    value = float(num)
                    if unit.lower() == "ml":
                        liquid_vol = value * 1000.0
                    else:  # 'ul'
                        liquid_vol = value

        # 计算新 slot
        orig_slot_raw = lw.get("slot")
        try:
            orig_slot = int(orig_slot_raw)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid slot value (must be convertible to int): {orig_slot_raw}")
        new_slot = replace_map.get(orig_slot)
        if new_slot is None:
            raise RuntimeError(f"Internal mapping error: slot {orig_slot} not in replace_map.")

        # 生成新 id：把 "on X" 改成 "on {new_slot}"，再把空格换成下划线
        prcxi_id = (lw.get("name") or "").strip()
        # 替换特殊字符
        prcxi_id = re.sub(r'[µμ]', 'u', prcxi_id)
        if not prcxi_id:
            # 没有名字就用类型占位，防止空
            prcxi_id = f"{class_name} on {orig_slot_raw}"
        new_id = re.sub(r'on \d+', f'on {new_slot}', prcxi_id)
        new_id = re.sub(r'\s+', '_', new_id)

        output.append({
            "id": new_id,
            "parent": "deck",
            "slot_on_deck": new_slot,
            "class_name": class_name,
            "liquid_type": [],
            "liquid_volume": [liquid_vol],
            "liquid_input_wells": []
        })
    # print('=== Lawbare Info ===')
    # pp.pprint(output)
    # pp.pprint(replace_map)

    return output, replace_map


def get_labware_data(protocol_name):
    """获取protocol的labware数据"""
    # 使用相对路径，从当前脚本所在目录找protoBuilds
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(os.path.dirname(current_dir), "protoBuilds")
    
    # 先试标准命名
    standard_file = f"{base_dir}/{protocol_name}/{protocol_name}.ot2.apiv2.py.json"
    if os.path.exists(standard_file):
        with open(standard_file, "r") as f:
            return json.load(f)
    
    # 如果标准文件不存在，找其他json文件
    proto_dir = f"{base_dir}/{protocol_name}/"
    if not os.path.exists(proto_dir):
        raise FileNotFoundError(f"Protocol directory not found: {proto_dir}")
    
    for filename in os.listdir(proto_dir):
        if filename.endswith(".json") and filename not in ("metadata.json", "README.json"):
            with open(os.path.join(proto_dir, filename), "r") as f:
                return json.load(f)
    
    raise FileNotFoundError(f"No protocol json found in {proto_dir}")


def load_liquid_locations(protocol_name):
    """加载原始的liquid_locations映射"""
    detailed_action_file = f"./detailed_action_json/{protocol_name}.json"
    
    if not os.path.exists(detailed_action_file):
        print(f"  未找到 {detailed_action_file}，将使用自动生成的液体名称")
        return {}
    
    try:
        with open(detailed_action_file, "r") as f:
            data = json.load(f)
            liquid_locs = data.get("liquid_locations", {})
            
            # 构建从 (slot, well) 到变量名的映射
            well_to_varname = {}
            for var_name, loc_info in liquid_locs.items():
                slot = int(loc_info.get("slot", 0))
                well = loc_info.get("well", "")
                if slot and well:
                    # 清理变量名：去掉数组索引 [0], [1] 等
                    clean_name = re.sub(r'\[\d+\]$', '', var_name)
                    well_to_varname[(slot, well)] = clean_name
            
            print(f"  加载了 {len(well_to_varname)} 个原始试剂位置映射")
            return well_to_varname
            
    except Exception as e:
        print(f"  加载 liquid_locations 失败: {e}，将使用自动生成的液体名称")
        return {}


def process_protocol(protocol_name):
    """处理单个protocol，返回action_list和labware_data"""
    print(f"Processing {protocol_name}...")
    
    # 获取action_list - 寻找对应的steps文件
    steps_dir = "./steps/"
    
    # 先尝试找同名的steps文件
    steps_file = None
    possible_files = [
        f"{protocol_name}.json",
        f"{protocol_name}-steps.json", 
        f"steps-{protocol_name}.json"
    ]
    
    for filename in possible_files:
        if os.path.exists(os.path.join(steps_dir, filename)):
            steps_file = os.path.join(steps_dir, filename)
            break
    
    # 如果找不到同名文件，使用第一个json文件
    if not steps_file:
        steps_files = [f for f in os.listdir(steps_dir) if f.endswith(".json")]
        if not steps_files:
            raise FileNotFoundError("No steps json files found")
        steps_file = os.path.join(steps_dir, steps_files[0])
        print(f"  Warning: 使用默认steps文件: {steps_files[0]}")
    else:
        print(f"  找到对应steps文件: {os.path.basename(steps_file)}")
    
    action_list = get_action_list(steps_file)
    
    # 获取labware_data
    labware_json = get_labware_data(protocol_name)
    labware_info, replace_map = extract_labware_info_from_json(labware_json, 12)
    
    return action_list, labware_info


def set_liquid_info(results, well_to_varname=None):
    """
    设置液体信息：为每个protocol的每个phase分配液体名称
    
    新逻辑：
    1. 同一个phase中所有被aspirate的孔位 = 同一种液体
    2. 同一个phase中所有被dispense的孔位 = 同一种液体
    3. 如果孔位已经在之前的phase中分配过液体，使用已有的液体名称
    4. 更新labware_info中的liquid_type和liquid_input_wells
    5. 优先使用原始的变量名（从well_to_varname映射），如果没有则使用Liquid_N格式
    """
    
    if well_to_varname is None:
        well_to_varname = {}
    
    for protocol_name, (action_list, labware_info) in results.items():
        print(f"处理 {protocol_name} 的液体信息...")
        
        # 跟踪每个孔位对应的液体名称: {(slot, well): liquid_name}
        well_to_liquid = {}
        
        # 液体计数器，用于生成唯一的液体名称
        liquid_counter = 1
        # 已使用的液体名称（用于避免重复）
        used_liquid_names = set()
        
        def get_liquid_name_for_well(slot, well):
            """为孔位获取液体名称，优先使用原始变量名"""
            well_key = (slot, well)
            
            # 如果已经分配过，直接返回
            if well_key in well_to_liquid:
                return well_to_liquid[well_key]
            
            # 尝试使用原始变量名
            if well_key in well_to_varname:
                original_name = well_to_varname[well_key]
                # 如果原始名称未被使用，直接用
                if original_name not in used_liquid_names:
                    used_liquid_names.add(original_name)
                    return original_name
                # 如果已被使用，添加后缀
                counter = 2
                while f"{original_name}_{counter}" in used_liquid_names:
                    counter += 1
                new_name = f"{original_name}_{counter}"
                used_liquid_names.add(new_name)
                return new_name
            
            # 没有原始名称，生成 Liquid_N 格式
            nonlocal liquid_counter
            while f"Liquid_{liquid_counter}" in used_liquid_names:
                liquid_counter += 1
            liquid_name = f"Liquid_{liquid_counter}"
            liquid_counter += 1
            used_liquid_names.add(liquid_name)
            return liquid_name
        
        # 遍历每个phase
        for phase_idx, action in enumerate(action_list):
            # 处理aspirate操作 - 每个action只有一个source well
            if action["aspirate"]:
                # 每个action只有一个source well，直接为其分配液体名称
                slot, well = action["aspirate"][0]  # 只有一个well
                well_key = (slot, well)
                aspirate_liquid_name = get_liquid_name_for_well(slot, well)
                well_to_liquid[well_key] = aspirate_liquid_name
                action["source_liquids"] = [aspirate_liquid_name]
                print(f"  源液体: {aspirate_liquid_name} ({slot}:{well})")
            else:
                action["source_liquids"] = []

            # 处理dispense操作 - 同一action中的所有dispense孔位共享同一液体
            if action["dispense"]:
                # 为这个action的所有dispense孔位分配相同的target液体
                # 使用一个固定的target名称，因为所有dispense都是到同一个地方
                target_liquid_name = "samples"
                if target_liquid_name not in used_liquid_names:
                    used_liquid_names.add(target_liquid_name)

                # 为这个action的所有dispense孔位分配相同的液体
                for slot, well in action["dispense"]:
                    well_key = (slot, well)
                    well_to_liquid[well_key] = target_liquid_name

                action["target_liquids"] = [target_liquid_name]
                print(f"  目标液体: {target_liquid_name} ({len(action['dispense'])} 个wells)")
            else:
                action["target_liquids"] = []
        
        # 更新labware_info中的液体信息
        for labware in labware_info:
            slot = labware["slot_on_deck"]

            # 为每个slot创建液体到wells的映射
            liquid_to_wells = {}

            for (well_slot, well), liquid_name in well_to_liquid.items():
                if well_slot == slot:
                    if liquid_name not in liquid_to_wells:
                        liquid_to_wells[liquid_name] = []
                    liquid_to_wells[liquid_name].append(well)

            # 更新labware的液体信息
            labware["liquid_type"] = list(liquid_to_wells.keys())
            # 对于多个液体的情况，我们需要展开所有wells
            all_wells = []
            for wells in liquid_to_wells.values():
                all_wells.extend(wells)
            labware["liquid_input_wells"] = all_wells

            if labware["liquid_type"]:
                print(f"  Labware {labware['id']}: {len(labware['liquid_type'])} 种液体在 {all_wells}")
        
        print(f"  {protocol_name}: 总共识别了 {len(used_liquid_names)} 种液体")
    
    return results




def process_all_protocols():
    """处理所有protocols"""
    original_dir = "/Users/guangxinzhang/Documents/Deep_Potential/opentrons/convert/protocols/original"
    
    # 获取所有protocol名称
    protocol_names = [d for d in os.listdir(original_dir) 
                     if os.path.isdir(os.path.join(original_dir, d))]
    
    results = {}
    errors = []
    
    for name in protocol_names:
        try:
            action_list, labware_data = process_protocol(name)
            results[name] = (action_list, labware_data)
            print(f"✓ {name} - success")
        except Exception as e:
            error_msg = f"✗ {name} - error: {str(e)}"
            print(error_msg)
            errors.append(error_msg)
    
    # 写错误日志
    if errors:
        os.makedirs("protocols/log", exist_ok=True)
        with open("protocols/log/error_converting.txt", "w") as f:
            for error in errors:
                f.write(f"{error}\n")
    
    print(f"\n完成处理: {len(results)} 成功, {len(errors)} 失败")
    return results




def generate_transfer_actions(protocol_name):
    """
    生成transfer_liquid格式的actions
    只包含同时有aspirate和dispense的有效phases
    """
    try:
        action_list, labware_info = process_protocol(protocol_name)
        results = {protocol_name: (action_list, labware_info)}
        
        # 加载原始试剂名称映射
        well_to_varname = load_liquid_locations(protocol_name)
        
        # 设置液体信息（静默处理）
        import sys
        from io import StringIO
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        results = set_liquid_info(results, well_to_varname)
        sys.stdout = old_stdout
        
        updated_action_list, updated_labware_info = results[protocol_name]
        
        # 生成有效的transfer actions
        transfer_actions = []
        
        for i, phase in enumerate(updated_action_list):
            # 跳过空的phase（没有aspirate或dispense）
            if not phase['aspirate'] or not phase['dispense']:
                continue
            
            # 确保有液体信息
            if not phase['source_liquids'] or not phase['target_liquids']:
                continue
            
            # 使用数组格式的体积和流速（标准格式要求）
            asp_vols = phase.get('asp_vols', [phase.get('asp_vol', 0)])
            dis_vols = phase.get('dis_vols', [phase.get('dis_vol', 0)])
            asp_flow_rates = phase.get('asp_flow_rates', [phase.get('asp_flow_rate', 0)])
            dis_flow_rates = phase.get('dis_flow_rates', [phase.get('dis_flow_rate', 0)])
            
            action = {
                "action": "transfer_liquid",
                "action_args": {
                    "sources": phase['source_liquids'][0] if len(phase['source_liquids']) == 1 else phase['source_liquids'],
                    "targets": phase['target_liquids'][0] if len(phase['target_liquids']) == 1 else phase['target_liquids'],
                    "asp_vols": asp_vols,
                    "dis_vols": dis_vols,
                    "asp_flow_rates": asp_flow_rates,
                    "dis_flow_rates": dis_flow_rates,
                    "tip_racks": phase.get('tip_racks', [])
                }
            }
            
            transfer_actions.append(action)
        
        return transfer_actions, updated_labware_info
        
    except Exception as e:
        print(f"生成 transfer actions 失败: {e}")
        return [], []


def print_transfer_actions(protocol_name):
    """打印指定协议的transfer actions"""
    print(f"\n{'='*50}")
    print(f"协议: {protocol_name}")
    print(f"{'='*50}")
    
    transfer_actions, labware_info = generate_transfer_actions(protocol_name)
    
    if not transfer_actions:
        print("没有有效的transfer actions")
        return
    
    print(f"生成了 {len(transfer_actions)} 个有效actions:")
    
    for i, action in enumerate(transfer_actions, 1):
        print(f"\nAction {i}:")
        print(f"  {{")
        print(f"    \"action\": \"{action['action']}\",")
        print(f"    \"action_args\": {{")
        print(f"      \"sources\": \"{action['action_args']['sources']}\",")
        print(f"      \"targets\": \"{action['action_args']['targets']}\",")
        print(f"      \"asp_vols\": {action['action_args']['asp_vols']},")
        print(f"      \"dis_vols\": {action['action_args']['dis_vols']},")
        print(f"      \"asp_flow_rates\": {action['action_args']['asp_flow_rates']},")
        print(f"      \"dis_flow_rates\": {action['action_args']['dis_flow_rates']}")
        print(f"    }}")
        print(f"  }}")
    
    # 显示液体分布信息
    liquid_summary = {}
    for labware in labware_info:
        if labware['liquid_type']:
            for liquid in labware['liquid_type']:
                if liquid not in liquid_summary:
                    liquid_summary[liquid] = []
                liquid_summary[liquid].append(f"slot{labware['slot_on_deck']}")
    
    # 显示reagent信息
    print(f"\nReagent信息:")

    # 从原始liquid_locations映射中获取准确的reagent信息
    well_to_varname = load_liquid_locations(protocol_name)

    # 构建liquid到well的映射
    liquid_to_info = {}
    for (slot, well), liquid_name in well_to_varname.items():
        if liquid_name not in liquid_to_info:
            liquid_to_info[liquid_name] = {
                "slot": slot,
                "wells": [well],  # 直接设置单个well
                "labware": ""
            }
        else:
            # 如果已经存在，添加到列表中
            liquid_to_info[liquid_name]["wells"].append(well)

    # 为每个labware设置labware类型（使用type而不是name）
    # 获取protoBuilds中的原始JSON数据来获取type信息
    slot_to_type = {}
    try:
        proto_json = get_labware_data(protocol_name)
        if 'labware' in proto_json:
            for labware in proto_json['labware']:
                slot = int(labware.get('slot', 0))
                labware_type = labware.get('type', '')
                slot_to_type[slot] = labware_type
    except Exception as e:
        pass

    # 为每个labware设置labware类型
    for labware in labware_info:
        slot = labware['slot_on_deck']
        for liquid_info in liquid_to_info.values():
            if liquid_info["slot"] == slot:
                # 使用type而不是name
                liquid_info["labware"] = slot_to_type.get(slot, "")

    # 处理transfer_actions中的liquids
    for action in transfer_actions:
        sources = action['action_args']['sources']
        targets = action['action_args']['targets']

        if isinstance(sources, str):
            sources = [sources]
        if isinstance(targets, str):
            targets = [targets]

        all_liquids = sources + targets

        for liquid in all_liquids:
            if liquid not in liquid_to_info and liquid == "samples":
                # 对于samples，找到对应的wells
                for labware in labware_info:
                    if labware['liquid_type'] and "samples" in labware['liquid_type']:
                        liquid_to_info[liquid] = {
                            "slot": labware['slot_on_deck'],
                            "wells": labware['liquid_input_wells'] if labware['liquid_input_wells'] else [],
                            "labware": slot_to_type.get(labware['slot_on_deck'], "")
                        }
                        break

    # 添加tiprack信息
    try:
        proto_json = get_labware_data(protocol_name)
        if 'labware' in proto_json:
            for labware in proto_json['labware']:
                labware_type = labware.get('type', '').lower()
                # 检查是否是tiprack
                if 'tip' in labware_type and 'rack' in labware_type:
                    slot = int(labware.get('slot', 0))
                    labware_type_name = labware.get('type', '')

                    # 生成tiprack key，根据slot命名，如 tiprack_1, tiprack_2 等
                    tiprack_key = f"tiprack_{slot}"
                    liquid_to_info[tiprack_key] = {
                        "slot": slot,
                        "labware": labware_type_name
                    }
    except Exception as e:
        pass

    # 显示所有reagent信息
    for liquid, info in liquid_to_info.items():
        if 'wells' in info:
            wells_str = ', '.join(info['wells'][:3])  # 显示前3个wells
            if len(info['wells']) > 3:
                wells_str += f" (+{len(info['wells'])-3}个)"
            print(f"  {liquid}: slot{info['slot']} | {info['labware']} | wells: [{wells_str}]")
        else:
            # 对于tiprack等没有wells信息的项目
            print(f"  {liquid}: slot{info['slot']} | {info['labware']}")


def export_transfer_actions(protocol_name, output_file=None):
    """导出transfer actions到JSON文件"""
    transfer_actions, labware_info = generate_transfer_actions(protocol_name)
    
    if not transfer_actions:
        print(f"协议 {protocol_name} 没有有效的transfer actions")
        return
    
    # 生成reagent信息
    reagents = {}
    
    # 创建slot到labware的映射
    slot_to_labware = {}
    for labware in labware_info:
        slot_to_labware[labware['slot_on_deck']] = labware
    
    # 从原始liquid_locations映射中获取准确的reagent信息
    well_to_varname = load_liquid_locations(protocol_name)

    # 构建liquid到well的映射
    liquid_to_info = {}
    for (slot, well), liquid_name in well_to_varname.items():
        if liquid_name not in liquid_to_info:
            liquid_to_info[liquid_name] = {
                "slot": slot,
                "wells": [well],  # 直接设置单个well
                "labware": ""
            }
        else:
            # 如果已经存在，添加到列表中
            liquid_to_info[liquid_name]["wells"].append(well)

    # 为每个labware设置labware类型（使用type而不是name）
    # 获取protoBuilds中的原始JSON数据来获取type信息
    slot_to_type = {}
    try:
        proto_json = get_labware_data(protocol_name)
        if 'labware' in proto_json:
            for labware in proto_json['labware']:
                slot = int(labware.get('slot', 0))
                labware_type = labware.get('type', '')
                slot_to_type[slot] = labware_type
    except Exception as e:
        pass

    # 为每个labware设置labware类型
    for labware in labware_info:
        slot = labware['slot_on_deck']
        for liquid_info in liquid_to_info.values():
            if liquid_info["slot"] == slot:
                # 使用type而不是name
                liquid_info["labware"] = slot_to_type.get(slot, "")

    # 处理transfer_actions中的liquids
    for action in transfer_actions:
        sources = action['action_args']['sources']
        targets = action['action_args']['targets']

        if isinstance(sources, str):
            sources = [sources]
        if isinstance(targets, str):
            targets = [targets]

        all_liquids = sources + targets

        for liquid in all_liquids:
            if liquid not in reagents and liquid in liquid_to_info:
                info = liquid_to_info[liquid]
                reagents[liquid] = {
                    "slot": info["slot"],
                    "well": info["wells"],
                    "labware": info["labware"]
                }

    # 对于没有在原始映射中找到的liquids（比如"samples"），从labware_info中获取
    for action in transfer_actions:
        sources = action['action_args']['sources']
        targets = action['action_args']['targets']

        if isinstance(sources, str):
            sources = [sources]
        if isinstance(targets, str):
            targets = [targets]

        all_liquids = sources + targets

        for liquid in all_liquids:
            if liquid not in reagents:
                # 从labware_info中查找
                for labware in labware_info:
                    if labware['liquid_type'] and liquid in labware['liquid_type']:
                        slot = labware['slot_on_deck']
                        wells = labware['liquid_input_wells']
                        labware_name = labware['id'].replace(f"_on_{slot}", "").replace("_", " ")

                        reagents[liquid] = {
                            "slot": slot,
                            "well": wells,
                            "labware": slot_to_type.get(slot, "")
                        }
                        break

    # 添加tiprack信息
    # 获取protoBuilds中的原始JSON数据
    try:
        proto_json = get_labware_data(protocol_name)
        if 'labware' in proto_json:
            for labware in proto_json['labware']:
                labware_type = labware.get('type', '').lower()
                # 检查是否是tiprack
                if 'tip' in labware_type and 'rack' in labware_type:
                    slot = int(labware.get('slot', 0))
                    labware_type_name = labware.get('type', '')

                    # 生成tiprack key，根据slot命名，如 tiprack_1, tiprack_2 等
                    tiprack_key = f"tiprack_{slot}"
                    reagents[tiprack_key] = {
                        "slot": slot,
                        "labware": labware_type_name
                    }
    except Exception as e:
        print(f"  加载protoBuilds数据失败: {e}")

    output_data = {
        "workflow": transfer_actions,
        "reagent": reagents
    }
    
    if output_file is None:
        output_file = f"{protocol_name}_transfer_actions.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"Transfer actions已导出到: {output_file}")
    return output_data


def batch_generate_transfer_actions(output_dir="transfer_actions"):
    """批量生成所有协议的transfer actions"""
    import os
    
    steps_dir = "./steps/"
    if not os.path.exists(steps_dir):
        print("steps目录不存在")
        return
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有协议
    protocols = [f.replace('.json', '') for f in os.listdir(steps_dir) if f.endswith('.json')]
    
    print(f"发现 {len(protocols)} 个协议")
    
    success_count = 0
    results_summary = []
    
    for i, protocol in enumerate(protocols, 1):
        try:
            print(f"[{i}/{len(protocols)}] 处理 {protocol}...")
            
            transfer_actions, labware_info = generate_transfer_actions(protocol)
            
            if not transfer_actions:
                print(f"  跳过 - 没有有效actions")
                continue
            
            # 导出单个协议的actions，文件名就是方案名.json
            output_file = os.path.join(output_dir, f"{protocol}.json")
            export_data = export_transfer_actions(protocol, output_file)
            
            # 计算液体种类数量
            all_liquids = set([action['action_args']['sources'] for action in transfer_actions] + 
                             [action['action_args']['targets'] for action in transfer_actions])
            
            results_summary.append({
                "protocol": protocol,
                "actions_count": len(transfer_actions),
                "liquids_count": len(all_liquids)
            })
            
            success_count += 1
            print(f"  成功 - {len(transfer_actions)} actions")
            
        except Exception as e:
            print(f"  失败: {e}")
            continue
    
    # 生成总览文件
    summary_file = os.path.join(output_dir, "batch_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_protocols": len(protocols),
            "successful_protocols": success_count,
            "results": results_summary
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n批量处理完成!")
    print(f"  成功: {success_count}/{len(protocols)}")
    print(f"  输出目录: {output_dir}")
    print(f"  总览文件: {summary_file}")


if __name__ == "__main__":
    # 选择运行模式
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        # 批量模式 - 支持自定义输出目录
        output_dir = sys.argv[2] if len(sys.argv) > 2 else "transfer_actions"
        batch_generate_transfer_actions(output_dir)
    else:
        # 示例模式
        output_dir = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "batch" else "transfer_actions_copy3"
        if len(sys.argv) > 1 and sys.argv[1] == "batch":
            output_dir = sys.argv[2] if len(sys.argv) > 2 else "transfer_actions_copy3"
        batch_generate_transfer_actions(output_dir)
