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
    
    action_list = []
    for phase_idx, phase in enumerate(data):
        aspirate_wells = set()
        dispense_wells = set()
        aspirate_vols = []
        dispense_vols = []
        aspirate_flow_rates = []
        dispense_flow_rates = []
        
        # 收集tip_rack信息（从pick_tip操作中提取）
        tip_racks_info = []
        
        # 收集非移液操作（加热、磁吸、延迟等）
        non_pipette_actions = []
        
        for step in phase:
            action_type = step.get('action', '')
            
            if action_type == "pick_tip":
                # 提取tip_rack信息
                tip_rack_info = step.get('tip_rack', {})
                if tip_rack_info:
                    # 保存tip_rack信息：slot, type, 以及可能的well（虽然通常transfer_liquid不需要具体well）
                    tip_racks_info.append({
                        "slot": tip_rack_info.get('slot'),
                        "type": tip_rack_info.get('type'),
                        "well": tip_rack_info.get('well')  # 保留well信息以便后续需要时使用
                    })
                # 不再将pick_tip添加到non_pipette_actions，因为它会被整合到transfer_liquid中
                continue
            elif action_type == "aspirate":
                aspirate_wells.add((step['source']['slot'], step['source']['well']))
                # 提取体积信息
                if 'vol' in step:
                    aspirate_vols.append(step['vol'])
                # 提取流速信息
                if 'flow_rate' in step:
                    aspirate_flow_rates.append(step['flow_rate'])
            elif action_type == "dispense":
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
                    dispense_wells.add((step['target']['slot'], step['target']['well']))
                    # 提取体积信息
                    if 'vol' in step:
                        dispense_vols.append(step['vol'])
                    # 提取流速信息
                    if 'flow_rate' in step:
                        dispense_flow_rates.append(step['flow_rate'])
            elif action_type == "drop_tip":
                # drop_tip操作会被transfer_liquid自动处理，不需要单独保留
                continue
            else:
                # 保留所有其他非移液操作（magnet, temperature, delay, mix等）
                # 按原始格式保留，不做转换
                non_pipette_actions.append(step)
        
        # 计算平均体积
        avg_asp_vol = sum(aspirate_vols) / len(aspirate_vols) if aspirate_vols else 0
        avg_dis_vol = sum(dispense_vols) / len(dispense_vols) if dispense_vols else 0
        
        # 计算平均流速
        avg_asp_flow_rate = sum(aspirate_flow_rates) / len(aspirate_flow_rates) if aspirate_flow_rates else 0
        avg_dis_flow_rate = sum(dispense_flow_rates) / len(dispense_flow_rates) if dispense_flow_rates else 0
        
        action_list.append({
            "phase": phase_idx,  # 这里使用正确的phase索引
            "aspirate": list(aspirate_wells),
            "dispense": list(dispense_wells),
            "asp_vol": avg_asp_vol,
            "dis_vol": avg_dis_vol,
            "asp_flow_rate": avg_asp_flow_rate,
            "dis_flow_rate": avg_dis_flow_rate,
            "tip_racks": tip_racks_info,  # 保存tip_rack信息
            "non_pipette_actions": non_pipette_actions  # 保存非移液操作
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
        # 清洗 class_name 中的点
        class_name = re.sub(r'\.', 'point', class_name)

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
    # 使用基于脚本所在目录的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    detailed_action_file = os.path.join(current_dir, "detailed_action_json", f"{protocol_name}.json")
    
    if not os.path.exists(detailed_action_file):
        print(f"  ⚠️  未找到 {detailed_action_file}，将使用自动生成的液体名称")
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
            
            print(f"  ✅ 加载了 {len(well_to_varname)} 个原始试剂位置映射")
            return well_to_varname
            
    except Exception as e:
        print(f"  ⚠️  加载 liquid_locations 失败: {e}，将使用自动生成的液体名称")
        return {}


def load_protocol_metadata(protocol_name):
    """从 protoBuilds/{name}/ 读取 metadata.json 和 README.json，提取 description 和 tags。

    tags 来源：
      1. metadata.json -> files["OT 2 protocol"] 列表中的每个文件名
      2. README.json   -> categories 字典的 key 及 value（list 中每个 str）

    description 来源：
      README.json -> description 字段（纯文本）

    Returns:
        (description: str, tags: list[str])
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    proto_build_dir = os.path.join(os.path.dirname(current_dir), "protoBuilds", protocol_name)

    description = ""
    tags = []

    # --- 读取 README.json ---
    readme_file = os.path.join(proto_build_dir, "README.json")
    if os.path.exists(readme_file):
        try:
            with open(readme_file, "r", encoding="utf-8") as f:
                readme = json.load(f)

            # 提取 description
            description = readme.get("description", "").strip()

            # 提取 categories 的 key 和 value 作为 tags
            categories = readme.get("categories", {})
            if isinstance(categories, dict):
                for cat_key, cat_values in categories.items():
                    tags.append(cat_key)
                    if isinstance(cat_values, list):
                        tags.extend(str(v) for v in cat_values)
        except Exception as e:
            print(f"  ⚠️  读取 README.json 失败: {e}")

    # 去重并保持顺序
    seen = set()
    unique_tags = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            unique_tags.append(t)

    return description, unique_tags


def load_labware_from_protobuild(protocol_name):
    """从 protoBuilds/{name}/{name}.ot2.apiv2.py.json 中直接读取 labware 数组。

    返回:
        labware 列表，每个元素包含 name, slot, type 等字段。
        如果读取失败则返回空列表。
    """
    try:
        labware_json = get_labware_data(protocol_name)
        labware_list = labware_json.get("labware", [])
        if not isinstance(labware_list, list):
            return []
        # 只保留有用字段: name, slot, type（type 加上 lab_ 前缀）
        result = []
        for lw in labware_list:
            raw_type = lw.get("type", "")
            prefixed_type = f"lab_{raw_type}" if raw_type and not raw_type.startswith("lab_") else raw_type
            result.append({
                "name": lw.get("name", ""),
                "slot": lw.get("slot", ""),
                "type": prefixed_type,
            })
        return result
    except Exception as e:
        print(f"  ⚠️  读取 labware 失败: {e}")
        return []


def process_protocol(protocol_name):
    """处理单个protocol，返回action_list和labware_data"""
    print(f"Processing {protocol_name}...")
    
    # 获取action_list - 寻找对应的steps文件
    # 使用基于脚本所在目录的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    steps_dir = os.path.join(current_dir, "steps")
    
    if not os.path.exists(steps_dir):
        raise FileNotFoundError(f"Steps directory not found: {steps_dir}")
    
    # 先尝试找同名的steps文件
    steps_file = None
    possible_files = [
        f"{protocol_name}.json",
        f"{protocol_name}-steps.json", 
        f"steps-{protocol_name}.json"
    ]
    
    for filename in possible_files:
        file_path = os.path.join(steps_dir, filename)
        if os.path.exists(file_path):
            steps_file = file_path
            break
    
    # 如果找不到同名文件，使用第一个json文件
    if not steps_file:
        steps_files = [f for f in os.listdir(steps_dir) if f.endswith(".json")]
        if not steps_files:
            raise FileNotFoundError(f"No steps json files found in {steps_dir}")
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
            # 处理aspirate操作 - 同一phase中的所有aspirate孔位共享同一液体
            if action["aspirate"]:
                # 检查是否有已知的液体
                existing_aspirate_liquid = None
                for slot, well in action["aspirate"]:
                    well_key = (slot, well)
                    if well_key in well_to_liquid:
                        existing_aspirate_liquid = well_to_liquid[well_key]
                        break
                
                # 如果没有已知液体，创建新的
                if existing_aspirate_liquid is None:
                    # 使用第一个孔位来决定液体名称
                    first_slot, first_well = action["aspirate"][0]
                    aspirate_liquid_name = get_liquid_name_for_well(first_slot, first_well)
                    print(f"  新源液体: {aspirate_liquid_name} (Phase {phase_idx} aspirate)")
                else:
                    aspirate_liquid_name = existing_aspirate_liquid
                    print(f"  复用源液体: {aspirate_liquid_name} (Phase {phase_idx} aspirate)")
                
                # 为这个phase的所有aspirate孔位分配相同的液体
                for slot, well in action["aspirate"]:
                    well_key = (slot, well)
                    well_to_liquid[well_key] = aspirate_liquid_name
                
                action["source_liquids"] = [aspirate_liquid_name]
            else:
                action["source_liquids"] = []
            
            # 处理dispense操作 - 同一phase中的所有dispense孔位共享同一液体
            if action["dispense"]:
                # 检查是否有已知的液体
                existing_dispense_liquid = None
                for slot, well in action["dispense"]:
                    well_key = (slot, well)
                    if well_key in well_to_liquid:
                        existing_dispense_liquid = well_to_liquid[well_key]
                        break
                
                # 如果没有已知液体，创建新的
                if existing_dispense_liquid is None:
                    # 使用第一个孔位来决定液体名称
                    first_slot, first_well = action["dispense"][0]
                    dispense_liquid_name = get_liquid_name_for_well(first_slot, first_well)
                    print(f"  新目标液体: {dispense_liquid_name} (Phase {phase_idx} dispense)")
                else:
                    dispense_liquid_name = existing_dispense_liquid
                    print(f"  复用目标液体: {dispense_liquid_name} (Phase {phase_idx} dispense)")
                
                # 为这个phase的所有dispense孔位分配相同的液体
                for slot, well in action["dispense"]:
                    well_key = (slot, well)
                    well_to_liquid[well_key] = dispense_liquid_name
                
                action["target_liquids"] = [dispense_liquid_name]
            else:
                action["target_liquids"] = []
        
        # 更新labware_info中的液体信息
        for labware in labware_info:
            slot = labware["slot_on_deck"]
            
            # 找到这个slot上所有有液体的孔位
            slot_liquids = []
            slot_wells = []
            
            for (well_slot, well), liquid_name in well_to_liquid.items():
                if well_slot == slot:
                    if liquid_name not in slot_liquids:
                        slot_liquids.append(liquid_name)
                        slot_wells.append(well)
            
            # 更新labware的液体信息
            labware["liquid_type"] = slot_liquids
            labware["liquid_input_wells"] = slot_wells
            
            if slot_liquids:
                print(f"  Labware {labware['id']}: {len(slot_liquids)} 种液体在 {slot_wells}")
        
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
    生成transfer_liquid格式的actions，同时保留其他操作（加热、磁吸、延迟等）
    按正确的顺序保留所有操作
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
        
        # 生成所有actions（包括transfer_liquid和其他操作）
        all_actions = []
        
        for i, phase in enumerate(updated_action_list):
            # 首先处理非移液操作（加热、磁吸、延迟等），按原始格式保留
            # 注意：过滤掉pick_tip和drop_tip，因为transfer_liquid会自动处理这些操作
            non_pipette_actions = phase.get('non_pipette_actions', [])
            for non_pip_action in non_pipette_actions:
                action_type = non_pip_action.get('action', '')
                # 跳过pick_tip和drop_tip，因为transfer_liquid已经包含了tip_rack参数并会自动处理
                if action_type in ('pick_tip', 'drop_tip'):
                    continue
                # 直接保留原始格式，不做转换
                all_actions.append(non_pip_action)
            
            # 然后处理移液操作，转换为transfer_liquid格式
            # 跳过空的phase（没有aspirate或dispense）
            if phase['aspirate'] and phase['dispense']:
                # 确保有液体信息
                if phase.get('source_liquids') and phase.get('target_liquids'):
                    # 提取tip_rack信息
                    tip_racks_info = phase.get('tip_racks', [])
                    tip_racks = None
                    if tip_racks_info:
                        # 去重：使用slot、type和well作为唯一标识，保留well信息
                        seen = set()
                        unique_tip_racks = []
                        for tr in tip_racks_info:
                            # 使用(slot, type, well)作为唯一标识
                            key = (tr.get('slot'), tr.get('type'), tr.get('well'))
                            if key not in seen and key[0] is not None:  # 确保slot不为None
                                seen.add(key)
                                tip_rack_data = {
                                    "slot": tr.get('slot'),
                                    "type": tr.get('type')
                                }
                                # 如果well存在，也添加到数据中
                                if tr.get('well') is not None:
                                    tip_rack_data["well"] = tr.get('well')
                                unique_tip_racks.append(tip_rack_data)
                        
                        if unique_tip_racks:
                            # 如果只有一个tip_rack，直接使用它；否则使用列表
                            tip_racks = unique_tip_racks[0] if len(unique_tip_racks) == 1 else unique_tip_racks
                    
                    action = {
                        "action": "transfer_liquid",
                        "action_args": {
                            "sources": phase['source_liquids'][0] if len(phase['source_liquids']) == 1 else phase['source_liquids'],
                            "targets": phase['target_liquids'][0] if len(phase['target_liquids']) == 1 else phase['target_liquids'],
                            "asp_vol": phase.get('asp_vol', 0),
                            "dis_vol": phase.get('dis_vol', 0),
                            "asp_flow_rate": phase.get('asp_flow_rate', 0),
                            "dis_flow_rate": phase.get('dis_flow_rate', 0)
                        }
                    }
                    
                    # 如果存在tip_rack信息，添加到action_args中
                    if tip_racks is not None:
                        action["action_args"]["tip_racks"] = tip_racks
                    
                    all_actions.append(action)
        
        return all_actions, updated_labware_info
        
    except Exception as e:
        print(f"❌ 生成 transfer actions 失败: {e}")
        return [], []


def print_transfer_actions(protocol_name):
    """打印指定协议的transfer actions"""
    print(f"\n{'='*50}")
    print(f"协议: {protocol_name}")
    print(f"{'='*50}")
    
    transfer_actions, labware_info = generate_transfer_actions(protocol_name)
    
    if not transfer_actions:
        print("❌ 没有有效的transfer actions")
        return
    
    print(f"✅ 生成了 {len(transfer_actions)} 个有效actions:")
    
    for i, action in enumerate(transfer_actions, 1):
        print(f"\nAction {i}:")
        if action.get('action') == 'transfer_liquid':
            # transfer_liquid格式
            print(f"  {{")
            print(f"    \"action\": \"{action['action']}\",")
            print(f"    \"action_args\": {{")
            print(f"      \"sources\": \"{action['action_args']['sources']}\",")
            print(f"      \"targets\": \"{action['action_args']['targets']}\",")
            print(f"      \"asp_vol\": {action['action_args']['asp_vol']},")
            print(f"      \"dis_vol\": {action['action_args']['dis_vol']},")
            print(f"      \"asp_flow_rate\": {action['action_args']['asp_flow_rate']},")
            print(f"      \"dis_flow_rate\": {action['action_args']['dis_flow_rate']}")
            print(f"    }}")
            print(f"  }}")
        else:
            # 其他操作（magnet, temperature, delay等），按原始格式打印
            print(f"  {json.dumps(action, indent=4, ensure_ascii=False)}")
    
    # 显示液体分布信息
    liquid_summary = {}
    for labware in labware_info:
        if labware['liquid_type']:
            for liquid in labware['liquid_type']:
                if liquid not in liquid_summary:
                    liquid_summary[liquid] = []
                liquid_summary[liquid].append(f"槽{labware['slot_on_deck']}")
    
    # 显示reagent信息
    print(f"\n🧪 Reagent信息:")
    reagents = {}
    slot_to_labware = {}
    for labware in labware_info:
        slot_to_labware[labware['slot_on_deck']] = labware
    
    for labware in labware_info:
        if labware['liquid_type']:
            for liquid in labware['liquid_type']:
                if liquid not in reagents:
                    wells = labware['liquid_input_wells'] if labware['liquid_input_wells'] else []
                    reagents[liquid] = {
                        "slot": labware['slot_on_deck'],
                        "well": wells,
                        "labware": labware['id'].replace(f"_on_{labware['slot_on_deck']}", "")
                    }
    
    for liquid, info in reagents.items():
        wells_str = ', '.join(info['well'][:3])  # 显示前3个wells
        if len(info['well']) > 3:
            wells_str += f" (+{len(info['well'])-3}个)"
        print(f"  {liquid}: 槽{info['slot']} | {info['labware']} | wells: [{wells_str}]")


def export_transfer_actions(protocol_name, output_file=None):
    """导出transfer actions到JSON文件，保存到transfer_actions_copy文件夹"""
    transfer_actions, labware_info = generate_transfer_actions(protocol_name)
    
    if not transfer_actions:
        print(f"❌ 协议 {protocol_name} 没有有效的transfer actions")
        return
    
    # 生成reagent信息
    reagents = {}
    
    # 创建slot到labware的映射
    slot_to_labware = {}
    for labware in labware_info:
        slot_to_labware[labware['slot_on_deck']] = labware
    
    # 收集所有液体信息
    for labware in labware_info:
        if labware['liquid_type']:
            for i, liquid in enumerate(labware['liquid_type']):
                if liquid not in reagents:
                    # 获取该液体在这个labware中的wells
                    wells = labware['liquid_input_wells'] if labware['liquid_input_wells'] else []
                    
                    reagents[liquid] = {
                        "slot": labware['slot_on_deck'],
                        "well": wells,
                    }
    
    # 加载 description 和 tags
    description, tags = load_protocol_metadata(protocol_name)

    # 加载 labware 信息（从 protoBuilds 的 JSON 中直接复制）
    labware_list = load_labware_from_protobuild(protocol_name)

    output_data = {
        "description": description,
        "tags": tags,
        "labware": labware_list,
        "workflow": transfer_actions,
        "reagent": reagents
    }
    
    # 确保输出目录存在（使用基于脚本所在目录的绝对路径）
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(current_dir, "transfer_actions_copy")
    os.makedirs(output_dir, exist_ok=True)
    
    if output_file is None:
        output_file = os.path.join(output_dir, f"{protocol_name}.json")
    else:
        # 如果提供了output_file，确保它在正确的目录下
        if not os.path.dirname(output_file):
            output_file = os.path.join(output_dir, output_file)
        else:
            # 如果提供了完整路径，使用它
            pass
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Transfer actions已导出到: {output_file}")
    return output_data


def batch_generate_transfer_actions(output_dir="transfer_actions_copy"):
    """批量生成所有协议的transfer actions，保存到transfer_actions_copy文件夹"""
    import os
    
    # 使用基于脚本所在目录的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    steps_dir = os.path.join(current_dir, "steps")
    
    if not os.path.exists(steps_dir):
        print(f"❌ steps目录不存在: {steps_dir}")
        return
    
    # 确保输出目录是绝对路径
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(current_dir, output_dir)
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有协议
    protocols = [f.replace('.json', '') for f in os.listdir(steps_dir) if f.endswith('.json')]
    
    print(f"🔍 发现 {len(protocols)} 个协议")
    
    success_count = 0
    results_summary = []
    
    for i, protocol in enumerate(protocols, 1):
        try:
            print(f"[{i}/{len(protocols)}] 处理 {protocol}...")
            
            transfer_actions, labware_info = generate_transfer_actions(protocol)
            
            if not transfer_actions:
                print(f"  ⚠️  跳过 - 没有有效actions")
                continue
            
            # 导出单个协议的actions，文件名就是方案名.json
            output_file = os.path.join(output_dir, f"{protocol}.json")
            export_data = export_transfer_actions(protocol, output_file)
            
            # 计算液体种类数量（只统计transfer_liquid操作）
            transfer_liquid_actions = [a for a in transfer_actions if a.get('action') == 'transfer_liquid']
            all_liquids = set()
            for action in transfer_liquid_actions:
                if 'action_args' in action:
                    sources = action['action_args'].get('sources', [])
                    targets = action['action_args'].get('targets', [])
                    if isinstance(sources, str):
                        all_liquids.add(sources)
                    elif isinstance(sources, list):
                        all_liquids.update(sources)
                    if isinstance(targets, str):
                        all_liquids.add(targets)
                    elif isinstance(targets, list):
                        all_liquids.update(targets)
            
            results_summary.append({
                "protocol": protocol,
                "actions_count": len(transfer_actions),
                "transfer_liquid_count": len(transfer_liquid_actions),
                "liquids_count": len(all_liquids)
            })
            
            success_count += 1
            print(f"  ✅ 成功 - {len(transfer_actions)} actions (其中 {len(transfer_liquid_actions)} 个transfer_liquid)")
            
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            continue
    
    # 生成总览文件（放在输出目录的上一级，即 protocol_converter/ 下）
    summary_file = os.path.join(os.path.dirname(output_dir), "batch_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_protocols": len(protocols),
            "successful_protocols": success_count,
            "results": results_summary
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 批量处理完成!")
    print(f"  ✅ 成功: {success_count}/{len(protocols)}")
    print(f"  📁 输出目录: {output_dir}")
    print(f"  📊 总览文件: {summary_file}")


if __name__ == "__main__":
    # 选择运行模式
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "single":
        # 单文件模式 - 处理指定的单个协议
        protocol_name = sys.argv[2] if len(sys.argv) > 2 else "00c517-pt2"
        print_transfer_actions(protocol_name)
        export_transfer_actions(protocol_name)
    else:
        # 默认批量模式 - 处理steps文件夹下的所有文件
        output_dir = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "batch" else "transfer_actions_copy"
        if len(sys.argv) > 1 and sys.argv[1] == "batch":
            output_dir = sys.argv[2] if len(sys.argv) > 2 else "transfer_actions_copy"
        batch_generate_transfer_actions(output_dir)
