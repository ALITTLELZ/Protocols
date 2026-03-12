"""
通过静态解析 .ot2.apiv2.py 源码提取 steps，无需执行协议。
使用 AST 分析 aspirate/dispense/mix/transfer/pick_up_tip/drop_tip 等调用，
输出与 protocol_from_python 相同的 phases 格式。
当无法完全解析时使用占位符，避免因 mock 不完整导致执行失败。
"""
import ast
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

_DEFAULT_FLOW_RATE = 7.6


def _eval_literal(node) -> Optional[Any]:
    """尝试从 AST 节点提取字面量"""
    if node is None:
        return None
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Num):  # Python 3.7
        return node.n
    if isinstance(node, ast.Str):  # Python 3.7
        return node.s
    if isinstance(node, (ast.List, ast.Tuple)) and hasattr(node, "elts"):
        try:
            return [_eval_literal(e) for e in node.elts]
        except Exception:
            pass
    return None


def _get_call_name(node) -> Optional[str]:
    """获取调用对象名，如 pip.aspirate -> 'pip'"""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if isinstance(node.func.value, ast.Name):
            return node.func.value.id
        if isinstance(node.func.value, ast.Attribute):
            return getattr(node.func.value.value, "id", None) if hasattr(node.func.value.value, "id") else None
    return None


def _get_well_str(node) -> str:
    """从 AST 节点推测 well 字符串，如 plate['A1'] -> 'A1'"""
    if node is None:
        return "?"
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Str):
        return node.s
    if isinstance(node, ast.Subscript):
        if isinstance(node.slice, ast.Constant):
            return str(node.slice.value)
        if isinstance(node.slice, ast.Index) and hasattr(node.slice, "value"):
            v = _eval_literal(node.slice.value)
            return str(v) if v is not None else "?"
    # well.top(), well.bottom() 等，取 base
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        return _get_well_str(node.func.value)
    return "?"


def _get_labware_slot(ctx_map: Dict, load_name: str, default_slot: int) -> Tuple[str, int]:
    """根据 load_name 返回 (labware_label, slot)"""
    return load_name, default_slot


def _find_run_function(tree: ast.AST) -> Optional[ast.FunctionDef]:
    """定位 run(ctx) 或 run(protocol) 函数"""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "run":
            return node
    return None


def _collect_calls_in_order(node: ast.AST) -> List[ast.Call]:
    """按源码顺序收集所有 Call 节点"""
    calls = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            calls.append(child)
    return calls


def _extract_well_from_expr(node, labware_var: str, labware_info: Tuple[str, str, int]) -> Optional[Tuple[str, str, int]]:
    """从赋值表达式提取 (well_str, load_name, slot)，如 plate.rows()[0][0] -> A1"""
    if node is None:
        return None
    load_name, label, slot = labware_info
    # plate['A1']
    if isinstance(node, ast.Subscript):
        w = _eval_literal(node.slice) if hasattr(node.slice, "value") else _eval_literal(getattr(node.slice, "value", None))
        if isinstance(node.slice, ast.Constant):
            w = node.slice.value
        return (str(w), load_name, slot) if w else None
    # plate.wells_by_name()['P17']
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr == "wells_by_name" and node.args:
            arg = node.args[0] if isinstance(node, ast.Call) else None
            w = _eval_literal(arg) if arg and hasattr(arg, "value") else None
            if hasattr(node, "func") and hasattr(node.func, "value"):
                # 可能是 xxx.wells_by_name()['P17'] 的 Subscript 在外层
                pass
            return (str(w), load_name, slot) if w else None
    # plate.rows()[0][:2] -> 返回首个 well
    if isinstance(node, ast.Subscript) and hasattr(node.value, "func"):
        # rows()[0][:2] -> slice
        return ("A1", load_name, slot)  # 96孔 rows()[0][:2] = A1,A2，默认 A1
    return None


# 96孔 plate.rows() 行顺序 A-H，rows()[0]=A1..A12, wells()[0]=A1
_96_ROWS = "ABCDEFGH"
_96_WELLS_ORDER = [f"{r}{c}" for c in range(1, 13) for r in _96_ROWS]


def _compute_well_from_index(idx: int, ncols: int = 12) -> str:
    """根据索引计算 96 孔 well 名"""
    if idx < 0 or idx >= 96:
        return "A1"
    return _96_WELLS_ORDER[idx]


def parse_protocol_static(code: str, protocol_dir: Path) -> List[Dict]:
    """
    静态解析协议源码，返回 action 列表（未分 phases）。
    """
    actions: List[Dict] = []
    labware_map: Dict[str, Tuple[str, str, int]] = {}  # var -> (load_name, label, slot)
    well_bindings: Dict[str, Tuple[str, str, int]] = {}  # var -> (well, load_name, slot)
    pip_map: Dict[str, str] = {}
    slot_counter = 1
    tip_slot = 3

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return actions

    run_fn = _find_run_function(tree)
    scope = run_fn if run_fn else tree

    def next_slot():
        nonlocal slot_counter
        s = slot_counter
        slot_counter += 1
        return s

    def _resolve_well(well_node, default_labware="?", default_slot=1) -> Dict:
        # 若为变量，查 well_bindings（支持 well.top()/well.bottom() 的 base）
        if well_node is not None:
            base = well_node
            if isinstance(well_node, ast.Call) and isinstance(well_node.func, ast.Attribute):
                base = well_node.func.value
            if isinstance(base, ast.Name) and base.id in well_bindings:
                w, ln, sl = well_bindings[base.id]
                return {"well": w, "labware": ln, "slot": sl}
        # 从 AST 解析字面量
        well_str = _get_well_str(well_node)
        if labware_map:
            _, label, slot = next(iter(labware_map.values()))
            return {"well": well_str if well_str != "?" else "A1", "labware": label, "slot": slot}
        return {"well": well_str or "A1", "labware": default_labware, "slot": default_slot}

    def _get_labware_entry():
        if labware_map:
            return next(iter(labware_map.values()))
        return ("generic_96_wellplate", "plate", 1)

    class Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call):
            if not isinstance(node.func, ast.Attribute):
                self.generic_visit(node)
                return

            obj_name = _get_call_name(node) or ""
            attr = node.func.attr

            # ctx.load_labware(load_name, slot, label=...)
            if obj_name == "ctx" and attr == "load_labware":
                self._visit_load_labware(node)
                return

            # module.load_labware(...)
            if attr == "load_labware" and obj_name:
                self._visit_module_load_labware(node, obj_name)
                return

            # ctx.load_instrument(name, mount, tip_racks=...)
            if obj_name == "ctx" and attr == "load_instrument":
                self._visit_load_instrument(node)
                return

            # pip.aspirate(vol, well)
            if attr == "aspirate":
                self._visit_aspirate(node, obj_name)
                return

            # pip.dispense(vol, well)
            if attr == "dispense":
                self._visit_dispense(node, obj_name)
                return

            # pip.mix(reps, vol, well)
            if attr == "mix":
                self._visit_mix(node, obj_name)
                return

            # pip.pick_up_tip / pick_up_tip(well?)
            if attr in ("pick_up_tip", "pick_up_tip"):
                self._visit_pick_up_tip(node, obj_name)
                return

            # pip.drop_tip
            if attr == "drop_tip":
                self._visit_drop_tip(node, obj_name)
                return

            # ctx.delay(seconds=, minutes=)
            if obj_name == "ctx" and attr == "delay":
                self._visit_delay(node)
                return

            # pip.transfer(vol, src, dest, ...)
            if attr == "transfer":
                self._visit_transfer(node, obj_name)
                return

            self.generic_visit(node)

        def _visit_load_labware(self, node):
            nonlocal labware_map, slot_counter
            args = node.args
            kwargs = {k.arg: k.value for k in (node.keywords or [])}
            if len(args) >= 1:
                load_name_node = args[0]
                load_name = _eval_literal(load_name_node)
                if load_name is None and hasattr(load_name_node, "id"):
                    load_name = getattr(load_name_node, "id", "generic_96")
                load_name = str(load_name) if load_name else "generic_96_wellplate"
            else:
                load_name = "generic_96_wellplate"

            location = kwargs.get("location") or (args[1] if len(args) >= 2 else None)
            slot = 1
            if location is not None:
                v = _eval_literal(location)
                if isinstance(v, (int, float)):
                    slot = int(v)
                elif isinstance(v, str) and v.isdigit():
                    slot = int(v)
                else:
                    slot = next_slot()

            label = _eval_literal(kwargs.get("label")) or (args[2] if len(args) >= 3 else load_name)
            if not isinstance(label, str):
                label = load_name

            # 无法知道赋值给谁，用 slot 作为占位
            labware_map[f"_slot_{slot}"] = (load_name, str(label), slot)

        def _visit_module_load_labware(self, node, mod_var):
            nonlocal labware_map, slot_counter
            args = node.args
            kwargs = {k.arg: k.value for k in (node.keywords or [])}
            load_name = _eval_literal(args[0]) if args else "generic_96"
            load_name = str(load_name) if load_name else "generic_96_wellplate"
            label = _eval_literal(kwargs.get("label")) or (args[1] if len(args) >= 2 else load_name)
            if not isinstance(label, str):
                label = load_name
            slot = next_slot()
            labware_map[f"_mod_{mod_var}_{slot}"] = (load_name, str(label), slot)

        def _visit_load_instrument(self, node):
            nonlocal pip_map
            args = node.args
            if len(args) >= 2:
                name = _eval_literal(args[0]) or (getattr(args[0], "id", "p20_single") if hasattr(args[0], "id") else "p20_single")
                mount = _eval_literal(args[1]) or "left"
            else:
                name, mount = "p20_single", "left"
            # 无法从 AST 知道赋值变量，用 mount 作为 key
            pip_map[str(mount)] = str(name)

        def _visit_aspirate(self, node, pip_name):
            args = node.args
            vol = _eval_literal(args[0]) if args else 1.0
            if vol is None:
                vol = 1.0
            well_node = args[1] if len(args) >= 2 else None
            src = _resolve_well(well_node)
            actions.append({
                "action": "aspirate",
                "vol": float(vol),
                "source": src,
                "flow_rate": _DEFAULT_FLOW_RATE
            })

        def _visit_dispense(self, node, pip_name):
            args = node.args
            vol = _eval_literal(args[0]) if args else 1.0
            if vol is None:
                vol = 1.0
            well_node = args[1] if len(args) >= 2 else None
            tgt = _resolve_well(well_node)
            actions.append({
                "action": "dispense",
                "vol": float(vol),
                "target": tgt,
                "flow_rate": _DEFAULT_FLOW_RATE
            })

        def _visit_mix(self, node, pip_name):
            args = node.args
            reps = _eval_literal(args[0]) if args else 3
            vol = _eval_literal(args[1]) if len(args) >= 2 else 5.0
            well_node = args[2] if len(args) >= 3 else None
            pos = _resolve_well(well_node)
            if labware_map:
                _, label, slot = _get_labware_entry()
                pos = {"well": pos["well"] or "A1", "labware": label, "slot": slot}
            actions.append({
                "action": "mix",
                "vol": float(vol) if vol else 5.0,
                "position": pos,
                "flow_rate": _DEFAULT_FLOW_RATE,
                "mix_time": int(reps) if reps else 3
            })

        def _visit_pick_up_tip(self, node, pip_name):
            tip_type = "Opentrons OT-2 96 Tip Rack 20 uL"
            actions.append({
                "action": "pick_tip",
                "tip_rack": {"well": "A1", "type": tip_type, "slot": tip_slot}
            })

        def _visit_drop_tip(self, node, pip_name):
            actions.append({
                "action": "drop_tip",
                "location": {"well": "A1", "labware": "Opentrons Fixed Trash", "slot": 12}
            })

        def _visit_delay(self, node):
            kwargs = {k.arg: k.value for k in (node.keywords or [])}
            seconds = _eval_literal(kwargs.get("seconds")) or 0
            minutes = _eval_literal(kwargs.get("minutes")) or 0
            actions.append({
                "action": "delay",
                "minutes": int(minutes) if minutes else 0,
                "seconds": float(seconds) if seconds else 0
            })

        def _visit_transfer(self, node, pip_name):
            args = node.args
            vol = _eval_literal(args[0]) if args else 1.0
            if vol is None:
                vol = 1.0
            src_node = args[1] if len(args) >= 2 else None
            dst_node = args[2] if len(args) >= 3 else None
            src = _resolve_well(src_node)
            dst = _resolve_well(dst_node)
            actions.append({
                "action": "aspirate",
                "vol": float(vol),
                "source": src,
                "flow_rate": _DEFAULT_FLOW_RATE
            })
            actions.append({
                "action": "dispense",
                "vol": float(vol),
                "target": dst,
                "flow_rate": _DEFAULT_FLOW_RATE
            })

    def process_node(node):
        """按顺序处理：先处理赋值以更新 labware_map，再处理 Call"""
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    var = t.id
                    if isinstance(node.value, ast.Call):
                        fn = node.value.func
                        if isinstance(fn, ast.Attribute):
                            if fn.attr == "load_labware":
                                obj = getattr(fn.value, "id", None)
                                if obj == "ctx":
                                    args = node.value.args
                                    kwargs = {k.arg: k.value for k in (node.value.keywords or [])}
                                    load_name = _eval_literal(args[0]) if args else "generic"
                                    load_name = str(load_name) if load_name else "generic_96"
                                    loc = _eval_literal(args[1]) if len(args) >= 2 else _eval_literal(kwargs.get("location"))
                                    slot = int(loc) if loc is not None and str(loc).replace(".", "").isdigit() else next_slot()
                                    label = _eval_literal(kwargs.get("label")) or (_eval_literal(args[2]) if len(args) >= 3 else load_name)
                                    labware_map[var] = (load_name, str(label) if label else load_name, slot)
                            elif fn.attr == "load_instrument":
                                args = node.value.args
                                name = _eval_literal(args[0]) if args else "p20"
                                pip_map[var] = str(name)
        elif isinstance(node, ast.Call):
            v.visit_Call(node)
        # 递归进 For/With/If 等
        if hasattr(node, "body"):
            for child in node.body:
                process_node(child)
        if hasattr(node, "orelse"):
            for child in node.orelse:
                process_node(child)

    v = Visitor()
    def extract_load_labware_from_call(call_node) -> Optional[Tuple[str, str, int]]:
        if not isinstance(call_node, ast.Call) or not isinstance(call_node.func, ast.Attribute):
            return None
        fn = call_node.func
        if fn.attr != "load_labware":
            return None
        obj = getattr(fn.value, "id", None)
        if obj not in ("ctx", "protocol"):
            return None
        args = call_node.args
        kwargs = {k.arg: k.value for k in (call_node.keywords or [])}
        load_name = _eval_literal(args[0]) if args else "generic"
        load_name = str(load_name) if load_name else "generic_96"
        loc = _eval_literal(args[1]) if len(args) >= 2 else _eval_literal(kwargs.get("location"))
        slot = int(loc) if loc is not None and str(loc).replace(".", "").replace("-", "").isdigit() else next_slot()
        label = _eval_literal(kwargs.get("label")) or (_eval_literal(args[2]) if len(args) >= 3 else load_name)
        return (load_name, str(label) if label else load_name, slot)

    def extract_well_from_assign(target_var: str, value_node) -> None:
        """从赋值右侧提取 well 绑定"""
        if value_node is None:
            return
        # plate.wells()[0]
        if isinstance(value_node, ast.Subscript) and isinstance(value_node.value, ast.Call):
            call = value_node.value
            if isinstance(call.func, ast.Attribute):
                if call.func.attr == "wells" and isinstance(call.func.value, ast.Name):
                    obj = call.func.value.id
                    if obj in labware_map:
                        info = labware_map[obj]
                        idx = 0
                        if isinstance(value_node.slice, ast.Constant):
                            idx = int(value_node.slice.value) if isinstance(value_node.slice.value, (int, float)) else 0
                        elif hasattr(value_node.slice, "value"):
                            idx = int(_eval_literal(value_node.slice.value) or 0)
                        well_bindings[target_var] = (_compute_well_from_index(idx), info[0], info[2])
                    return
                if call.func.attr == "wells_by_name":
                    obj = getattr(call.func.value, "id", None) if isinstance(call.func.value, ast.Name) else None
                    if obj and obj in labware_map:
                        info = labware_map[obj]
                        w = _eval_literal(value_node.slice) if hasattr(value_node.slice, "value") else None
                        if isinstance(value_node.slice, ast.Constant):
                            w = value_node.slice.value
                        well_bindings[target_var] = (str(w) if w else "A1", info[0], info[2])
                    return
        # plate['A1'] 或 plate.rows()[0][0]
        if isinstance(value_node, ast.Subscript):
            plate_node = value_node.value
            if isinstance(plate_node, ast.Name) and plate_node.id in labware_map:
                info = labware_map[plate_node.id]
                w = None
                if isinstance(value_node.slice, ast.Constant):
                    w = value_node.slice.value
                elif hasattr(value_node.slice, "value"):
                    w = _eval_literal(value_node.slice.value)
                if w is not None:
                    well_bindings[target_var] = (str(w), info[0], info[2])
                return
            elif isinstance(plate_node, ast.Subscript):
                # plate.rows()[0][0]
                if isinstance(plate_node.value, ast.Name) and plate_node.value.id in labware_map:
                    info = labware_map[plate_node.value.id]
                    row_idx = _eval_literal(plate_node.slice) or 0
                    if isinstance(value_node.slice, ast.Constant):
                        col_idx = value_node.slice.value
                    else:
                        col_idx = _eval_literal(getattr(value_node.slice, "value", value_node.slice)) or 0
                    well = _compute_well_from_index(row_idx * 12 + (col_idx if isinstance(col_idx, int) else 0))
                    well_bindings[target_var] = (well, info[0], info[2])
            return
        # plate.wells()[0]
        if isinstance(value_node, ast.Call) and isinstance(value_node.func, ast.Attribute):
            fn = value_node.func
            obj = getattr(fn.value, "id", None) if isinstance(fn.value, ast.Name) else None
            if obj and obj in labware_map:
                info = labware_map[obj]
                if fn.attr == "wells":
                    idx = _eval_literal(value_node.args[0]) if value_node.args else 0
                    if hasattr(value_node.args[0], "value"):
                        idx = _eval_literal(value_node.args[0].value) if value_node.args else 0
                    well_bindings[target_var] = (_compute_well_from_index(int(idx) if idx is not None else 0), info[0], info[2])
                elif fn.attr == "wells_by_name" and isinstance(value_node.func.value, ast.Subscript):
                    pass  # wells_by_name()['X'] 需在 Subscript 处理
            return
        # plate.wells_by_name()['P17'] - 外层是 Subscript
        if isinstance(value_node, ast.Subscript) and isinstance(value_node.value, ast.Call):
            call = value_node.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == "wells_by_name":
                obj = getattr(call.func.value, "id", None) if isinstance(call.func.value, ast.Name) else None
                if obj and obj in labware_map:
                    info = labware_map[obj]
                    w = _eval_literal(value_node.slice) if hasattr(value_node.slice, "value") else value_node.slice.value if isinstance(value_node.slice, ast.Constant) else None
                    if w is None and hasattr(value_node.slice, "value"):
                        w = _eval_literal(value_node.slice.value)
                    well_bindings[target_var] = (str(w) if w else "A1", info[0], info[2])
            return
        # mm = plate.rows()[0][:2] 等切片，或 all_dest = plate.rows()[0]
        if isinstance(value_node, ast.Subscript):
            inner = value_node.value
            if isinstance(inner, ast.Subscript) or (isinstance(inner, ast.Call) and getattr(inner.func, "attr", None) == "rows"):
                call = inner if isinstance(inner, ast.Call) else getattr(inner.value, None)
                if isinstance(inner, ast.Subscript):
                    call = inner.value
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == "rows":
                    obj = getattr(call.func.value, "id", None) if isinstance(call.func.value, ast.Name) else None
                    if obj and obj in labware_map:
                        info = labware_map[obj]
                        well_bindings[target_var] = ("A1", info[0], info[2])
                return
        # var2 = var1[idx]，如 mm_source = mm[i//24]
        if isinstance(value_node, ast.Subscript) and isinstance(value_node.value, ast.Name):
            src_var = value_node.value.id
            if src_var in well_bindings:
                w, ln, sl = well_bindings[src_var]
                well_bindings[target_var] = (w, ln, sl)

    nodes_to_process = list(ast.walk(scope))
    # 先处理所有赋值（含 list comp 内的 load_labware 和 well 绑定）
    for node in nodes_to_process:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    var = t.id
                else:
                    continue
                val = node.value
                if isinstance(val, ast.Call):
                    fn = val.func
                    if isinstance(fn, ast.Attribute):
                        if fn.attr == "load_labware":
                            res = extract_load_labware_from_call(val)
                            if res:
                                labware_map[var] = res
                        elif fn.attr == "load_instrument":
                            args = val.args
                            name = _eval_literal(args[0]) if args else "p20"
                            pip_map[var] = str(name)
                elif isinstance(val, (ast.ListComp, ast.List)) or (isinstance(val, ast.Subscript) and isinstance(val.value, ast.ListComp)):
                    if isinstance(val, ast.Subscript):
                        val = val.value  # [...][:n] -> 取 ListComp
                    for n in ast.walk(val):
                        if isinstance(n, ast.Call):
                            res = extract_load_labware_from_call(n)
                            if res:
                                labware_map[f"{var}_item"] = res
                                break
                    # ListComp 的 well 绑定
                    if isinstance(val, ast.ListComp) and val.generators:
                        # ntc_dests = [pcr_plate.wells_by_name()[w] for w in ['P17','P18','P19']]
                        if isinstance(val.elt, ast.Subscript):
                            if isinstance(val.elt.value, ast.Call) and getattr(val.elt.value.func, "attr", None) == "wells_by_name":
                                plate_var = getattr(val.elt.value.func.value, "id", None)
                                if plate_var and plate_var in labware_map:
                                    info = labware_map[plate_var]
                                    first_well = None
                                    it = val.generators[0].iter
                                    if isinstance(it, (ast.List, ast.Tuple)) and it.elts:
                                        first_well = _eval_literal(it.elts[0])
                                    well_bindings[var] = (str(first_well) if first_well else "A1", info[0], info[2])
                        # all_destinations = [well for row in pcr_plate.rows()[:2] for well in row]
                        elif isinstance(val.elt, ast.Name):
                            gen0 = val.generators[0]
                            it = gen0.iter
                            plate_var = None
                            if isinstance(it, ast.Subscript):
                                # pcr_plate.rows()[:2]
                                inner = it.value
                                if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute) and inner.func.attr == "rows":
                                    plate_var = getattr(inner.func.value, "id", None)
                            elif isinstance(it, ast.Name):
                                # all_samples: for plate in sample_plates
                                iter_var = it.id
                                if f"{iter_var}_item" in labware_map:
                                    info = labware_map[f"{iter_var}_item"]
                                    well_bindings[var] = ("A1", info[0], info[2])
                                    plate_var = "__done__"
                            if plate_var and plate_var != "__done__" and plate_var in labware_map:
                                info = labware_map[plate_var]
                                well_bindings[var] = ("A1", info[0], info[2])
                else:
                    extract_well_from_assign(var, val)
    def _set_loop_bindings(target, iter_node):
        if isinstance(target, ast.Name) and isinstance(iter_node, ast.Name):
            if iter_node.id in well_bindings:
                well_bindings[target.id] = well_bindings[iter_node.id]
        elif isinstance(target, ast.Tuple) and isinstance(iter_node, ast.Call):
            fn_id = getattr(iter_node.func, "id", None) if isinstance(iter_node.func, ast.Name) else None
            if fn_id == "zip" and iter_node.args:
                for i, t in enumerate(target.elts):
                    if i < len(iter_node.args) and isinstance(t, ast.Name) and isinstance(iter_node.args[i], ast.Name):
                        if iter_node.args[i].id in well_bindings:
                            well_bindings[t.id] = well_bindings[iter_node.args[i].id]
            elif fn_id == "enumerate" and iter_node.args and isinstance(iter_node.args[0], ast.Name):
                if iter_node.args[0].id in well_bindings and len(target.elts) >= 2 and isinstance(target.elts[-1], ast.Name):
                    well_bindings[target.elts[-1].id] = well_bindings[iter_node.args[0].id]

    def _walk_body(nodes):
        for node in nodes:
            if isinstance(node, ast.For):
                _set_loop_bindings(node.target, node.iter)
                _walk_body(node.body)
                if getattr(node, "orelse", None):
                    _walk_body(node.orelse)
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                v.visit_Call(node.value)
            elif isinstance(node, ast.Call):
                v.visit_Call(node)
            else:
                if hasattr(node, "body"):
                    _walk_body(getattr(node, "body", []))
                if hasattr(node, "handlers"):
                    for h in node.handlers:
                        _walk_body(getattr(h, "body", []))

    body = getattr(scope, "body", [])
    _walk_body(body)

    return actions


def actions_to_phases(actions: List[Dict]) -> List[List[Dict]]:
    """与 protocol_from_python 相同的分组逻辑"""
    phases = []
    current = []
    for a in actions:
        if a.get("action") == "pick_tip":
            if current:
                phases.append(current)
            current = [a]
        elif a.get("action") == "dispense" and a.get("vol") == -1:
            continue  # blow_out 不输出，跳过
        else:
            current.append(a)
    if current:
        phases.append(current)
    return phases


def process_protocol_static(protocol_dir: Path, output_dir: Path, verbose: bool = True) -> Optional[List[List[Dict]]]:
    """
    通过静态解析生成 steps，不执行协议。
    返回 phases 或 None（解析失败时）。
    """
    py_files = list(protocol_dir.glob("*.ot2.apiv2.py"))
    if not py_files:
        return None

    with open(py_files[0], "r", encoding="utf-8") as f:
        code = f.read()

    actions = parse_protocol_static(code, protocol_dir)
    if not actions:
        return None

    phases = actions_to_phases(actions)
    output_dir.mkdir(parents=True, exist_ok=True)
    name = protocol_dir.name
    out_path = output_dir / f"{name}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(phases, f, indent=4, ensure_ascii=False)

    if verbose:
        print(f"  静态解析 steps: {out_path}")
    return phases
