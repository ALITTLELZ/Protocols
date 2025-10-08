
import json
import time
from platform import node
import pandas as pd
from collections import defaultdict
import networkx as nx
import re
from typing import List, Dict, Optional, Union, Sequence, Literal, Any
import networkx as nx
import os
from pathlib import Path
import inspect
_LABWARE_CACHE: Dict[tuple, Any] = {}
from typing import List, Dict, Any
import pprint as pp
from pylabrobot.resources.opentrons.tube_racks import *
from pylabrobot.resources.opentrons.tip_racks import *
from pylabrobot.resources.opentrons.reservoirs import *
import pylabrobot.resources.opentrons.reservoirs as reservoirs
from pylabrobot.resources.opentrons.plates import *
import pylabrobot.resources.opentrons.plates as plates
from pylabrobot.resources.opentrons.module import *
import pylabrobot.resources.opentrons.tip_racks as tip_racks_mod
import pylabrobot.resources.opentrons.tube_racks as tube_racks_mod

_DEF_WELL_COUNTS = (384, 96, 48, 24)

def _parse_well_count(name: str) -> int | None:
    s = name.lower()
    for k in _DEF_WELL_COUNTS:
        # 匹配独立数字（避免把 96 匹配到 196 等）
        if re.search(rf'(^|[^0-9]){k}([^0-9]|$)', s):
            return k
    return None

def _parse_capacity_ul(name: str) -> float | None:
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

def match_labware_class(class_name: str):
    """超简匹配：
    - 先看目标名里是否包含 well/pcr；若都不含，直接放弃匹配；
    - 提取孔数（仅 24/48/96/384），容量（若有）；
    - 在已导入的 plates 类（globals 里名称包含 'plate' 或 'wellplate' 或 'pcr'）中找同孔数；
    - 如有容量要求，挑 capacity >= 需求 且差值最小的；否则返回第一个同孔数候选。
    返回 (cls 或 None, 说明字符串)
    """
    name_l = class_name.lower()
    # Special case: trash – pick the largest reservoir available
    if 'trash' in name_l or 'reservoir' in name_l or 'waste' in name_l:

        trash_candidates = []  # (factory_fn, name, cap)
        for nm, obj in inspect.getmembers(reservoirs, inspect.isfunction):
            # 解析容量，选容量最大的
            cap = _parse_capacity_ul(nm) or 0.0
            trash_candidates.append((obj, nm, cap))
        if trash_candidates:
            trash_candidates.sort(key=lambda x: x[2], reverse=True)
            cls, nm, cap = trash_candidates[0]
            return cls, f"trash matched by max capacity: picked {nm} ({cap}uL)"
        return None, "no reservoir functions found for trash"
    
        # Tip racks: choose by tip volume (closest >= target if available)
    if 'tip' in name_l:
        import inspect
        target_cap = _parse_capacity_ul(class_name)  # may be None
        cands = []  # (factory_fn, name, cap)
        for nm, obj in inspect.getmembers(tip_racks_mod, inspect.isfunction):
            cap = _parse_capacity_ul(nm)
            cands.append((obj, nm, cap))
        if not cands:
            return None, 'no tip_rack factories found'
        if target_cap is not None:
            feasible = [(fn, nm, cap) for fn, nm, cap in cands if cap is not None and cap >= target_cap]
            if feasible:
                feasible.sort(key=lambda x: x[2] - target_cap)
                fn, nm, cap = feasible[0]
                return fn, f"tip rack by min over-cap: target={target_cap}uL, picked {nm} ({cap}uL)"
            # fallback: pick closest absolute difference if none are >=
            with_caps = [(fn, nm, cap) for fn, nm, cap in cands if cap is not None]
            if with_caps:
                with_caps.sort(key=lambda x: abs(x[2] - target_cap))
                fn, nm, cap = with_caps[0]
                return fn, f"tip rack by nearest: target={target_cap}uL, picked {nm} ({cap}uL)"
        # if no target cap or no caps in names, return first candidate
        fn, nm, cap = cands[0]
        return fn, f"tip rack fallback: chose {nm} (cap={cap})"

    # Tube racks (non-tip racks): try to match by capacity if present, else fallback
    if 'rack' in name_l and 'tip' not in name_l:
        import inspect
        target_cap = _parse_capacity_ul(class_name)  # may be None
        cands = []  # (factory_fn, name, cap)
        for nm, obj in inspect.getmembers(tube_racks_mod, inspect.isfunction):
            cap = _parse_capacity_ul(nm)
            cands.append((obj, nm, cap))
        if not cands:
            return None, 'no tube_rack factories found'
        if target_cap is not None:
            feasible = [(fn, nm, cap) for fn, nm, cap in cands if cap is not None and cap >= target_cap]
            if feasible:
                feasible.sort(key=lambda x: x[2] - target_cap)
                fn, nm, cap = feasible[0]
                return fn, f"tube rack by min over-cap: target={target_cap}uL, picked {nm} ({cap}uL)"
            with_caps = [(fn, nm, cap) for fn, nm, cap in cands if cap is not None]
            if with_caps:
                with_caps.sort(key=lambda x: abs(x[2] - target_cap))
                fn, nm, cap = with_caps[0]
                return fn, f"tube rack by nearest: target={target_cap}uL, picked {nm} ({cap}uL)"
        fn, nm, cap = cands[0]
        return fn, f"tube rack fallback: chose {nm} (cap={cap})"


    has_plate_keyword = ('well' in name_l) or ('pcr' in name_l)
    if not has_plate_keyword:
        return None, "skip: not a plate-like name (no 'well'/'pcr')"

    target_wells = _parse_well_count(class_name)
    if target_wells is None:
        return None, "skip: no 24/48/96/384 well count in name"

    target_cap = _parse_capacity_ul(class_name)


    candidates = []  # (factory_fn, name, wells, cap)
    for nm, obj in inspect.getmembers(plates, inspect.isfunction):
        nm_l = nm.lower()
        if not (('plate' in nm_l) or ('wellplate' in nm_l) or ('pcr' in nm_l) or ('well' in nm_l)):
            continue
        wells = _parse_well_count(nm)
        if wells != target_wells:
            continue
        cap = _parse_capacity_ul(nm)
        candidates.append((obj, nm, wells, cap))
    
    if not candidates:
        return None, f"no class with {target_wells}-well in imported plates"

    # 如果没有容量要求，返回第一个候选
    if target_cap is None:
        cls, nm, _, cap = candidates[0]
        return cls, f"matched by wells={target_wells} (no target cap); chose {nm} (cap={cap})"

    # 有容量要求：选择 cap>=target_cap 且 (cap-target_cap) 最小；若都无 cap 或 cap 小于需求，则退而选任一候选
    feasible = [(cls, nm, cap) for cls, nm, _, cap in candidates if (cap is not None and cap >= target_cap)]
    if feasible:
        feasible.sort(key=lambda x: x[2] - target_cap)
        cls, nm, cap = feasible[0]
        return cls, f"matched by wells={target_wells} and min over-cap: target={target_cap}uL, picked {nm} ({cap}uL)"

    # 没有容量信息或都不足，兜底：返回任一候选
    cls, nm, _, cap = candidates[0]
    return cls, f"fallback by wells={target_wells}; no feasible cap>=target ({target_cap}uL); chose {nm} (cap={cap})"



def _parse_liquid_ops(step_lines: List[str]) -> List[Dict]:
    """
    返回按原始顺序的动作列表；将连续的 Heater-Shaker 行聚合为一条:
      {"action":"heater_shaker",
       "target_temperature":float|None,
       "wait_for_temp":bool,
       "shake_speed":float|None,
       "duration_minutes":int|None,
       "deactivate_heater":bool,
       "deactivate_shaker":bool}
    其它动作同之前：aspirate/dispense/pick_tip/drop_tip/air_gap/blow_out/touch_tip/delay/magnet/temperature/raw
    """
    import re
    from typing import Optional, Dict, Union, List

    def f_after(s: str, kw: str) -> Optional[float]:
        m = re.search(rf'{re.escape(kw)}\s+([\d.]+)', s)
        return float(m.group(1)) if m else None

    def parse_container(line: str, mode_kw: str) -> Optional[Dict[str, Union[str, int]]]:
        # 只匹配 from / into，不要把 "at ..." 误当分隔词
        m = re.search(
            rf'{re.escape(mode_kw)}\s+[\d.]+\s*u?L.*?(?:from|into)\s+([A-H]\d+)\s+of\s+(.*?)\s+on\s+(\d+)',
            line
        )
        if not m:
            return None
        return {"well": m.group(1), "labware": m.group(2).strip(), "slot": int(m.group(3))}

    actions: List[Dict] = []
    # —— Heater-Shaker 聚合状态（遇到非 HS 行时 flush）——
    hs = None  # dict | None

    def flush_hs():
        nonlocal hs, actions
        if hs is not None:
            actions.append(hs)
            hs = None

    for raw in step_lines:
        s = raw.strip()
        if not s:
            continue

        # ===== Heater-Shaker 聚合 =====
        if s.startswith("Setting Target Temperature of Heater-Shaker") \
           or s.startswith("Waiting for Heater-Shaker") \
           or s.startswith("Setting Heater-Shaker to Shake at") \
           or s.startswith("Deactivating Heater") \
           or s.startswith("Deactivating Shaker"):

            if hs is None:
                hs = {
                    "action": "heater_shaker",
                    "target_temperature": None,
                    "wait_for_temp": False,
                    "shake_speed": None,
                    "duration_minutes": None,
                    "deactivate_heater": False,
                    "deactivate_shaker": False
                }

            if s.startswith("Setting Target Temperature of Heater-Shaker"):
                # “… to XX”
                hs["target_temperature"] = f_after(s, "to")

            elif s.startswith("Waiting for Heater-Shaker"):
                hs["wait_for_temp"] = True

            elif s.startswith("Setting Heater-Shaker to Shake at"):
                m = re.search(r'Shake at\s+([\d.]+)\s*RPM', s)
                if m:
                    hs["shake_speed"] = float(m.group(1))

            elif s.startswith("Delaying"):
                m = re.search(r'Delaying for\s+(\d+)\s+minutes', s)
                if m:
                    hs["duration_minutes"] = int(m.group(1))

            elif s.startswith("Deactivating Heater"):
                hs["deactivate_heater"] = True

            elif s.startswith("Deactivating Shaker"):
                hs["deactivate_shaker"] = True

            # 注意：是“聚合”而不是立即落表，所以 continue
            continue

        # 走到这里说明当前行**不是** Heater-Shaker，先把上一个 hs flush 掉
        flush_hs()

        # ===== 常规液体学 / 其它模块 =====
        matched = False

        if s.startswith("Aspirating") and "from" in s:

            m = re.search(
                r'Aspirating\s+([\d.]+)\s*u?L\s+from\s+([A-Z]\d+)\s+of\s+(.*?)\s+on\s+(?:slot\s*)?(\d+)\s+at\s+([\d.]+)\s*[µu]L/sec',
                s,
                re.IGNORECASE
            )         

            if m:
                vol = float(m.group(1))
                src = {"well": m.group(2), "labware": m.group(3).strip(), "slot": int(m.group(4))}
                flow_rate = float(m.group(5))
                actions.append({"action": "aspirate",
                            "vol": vol,
                            "source": src,
                            "flow_rate": flow_rate  
                        })
                matched = True

            # pp.pprint(actions)
            # print(s)

        elif s.startswith("Dispensing") and "into" in s:
            m = re.search(
                r'Dispensing\s+([\d.]+)\s*u?L\s+into\s+([A-Z]\d+)\s+of\s+(.*?)\s+on\s+(?:slot\s*)?(\d+)\s+at\s+([\d.]+)\s*[µu]L/sec',
                s,
                re.IGNORECASE
            )         

            if m:
                vol = float(m.group(1))
                tgt = {"well": m.group(2), "labware": m.group(3).strip(), "slot": int(m.group(4))}
                flow_rate = float(m.group(5))
                actions.append({"action": "dispense",
                            "vol": vol,
                            "target": tgt,
                            "flow_rate": flow_rate
                        })
                matched = True

        elif s.startswith("Picking up tip"):
            
            m = re.search(r'from ([A-H]\d+) of (.*?) on (?:slot\s*)?(\d+)', s, re.IGNORECASE)
            tip = {"well": m.group(1), "type": m.group(2).strip(), "slot": int(m.group(3))} if m else None
            actions.append({"action": "pick_tip", "tip_rack": tip})
            matched = True

        elif s.startswith("Dropping tip"):
            m = re.search(r'into ([A-H]\d+) of (.*?) on (\d+)', s)
            loc = {"well": m.group(1), "labware": m.group(2).strip(), "slot": int(m.group(3))} if m else None
            actions.append({"action": "drop_tip", "location": loc})
            matched = True

        elif s.startswith("Air gap"):
            m = re.search(r'Air gap(?:\s+with)?\s+([\d.]+)\s*u?L', s, re.IGNORECASE)
            vol = float(m.group(1)) if m else f_after(s, "Aspirating")
            actions.append({"action": "air_gap", "vol": vol})
            matched = True

        elif s.startswith("Blowing out"):
            m = re.search(r'Blowing out at\s+([A-H]\d+)\s+of\s+(.*?)\s+on\s+(\d+)', s)
            at = {"well": m.group(1), "labware": m.group(2).strip(), "slot": int(m.group(3))} if m else None
            actions.append({"action": "blow_out", "at": at})
            matched = True

        elif "Touching tip" in s:
            actions.append({"action": "touch_tip"})
            matched = True

        elif s.startswith("Delaying"):
            # 注意：此 delay 是**非** Heater-Shaker 的普通延时（因为前面已经 flush 了 hs）
            m = re.search(r'Delaying for\s+(\d+)\s+minutes(?:\s+and\s+([\d.]+)\s*seconds)?', s)
            minutes = int(m.group(1)) if m else None
            seconds = float(m.group(2)) if (m and m.group(2)) else None
            actions.append({"action": "delay", "minutes": minutes, "seconds": seconds})
            matched = True

        elif s.startswith("Engaging Magnetic Module"):
            actions.append({"action": "magnet", "state": "engage"})
            matched = True
        elif s.startswith("Disengaging Magnetic Module"):
            actions.append({"action": "magnet", "state": "disengage"})
            matched = True

        elif s.startswith("Setting Temperature Module temperature"):
            temp = f_after(s, "to")
            actions.append({"action": "temperature", "target": temp})
            matched = True
        elif s.startswith("Deactivating Temperature Module"):
            actions.append({"action": "temperature", "state": "off"})
            matched = True

        if not matched:
            actions.append({"action": "raw", "text": s})

    # 文件结尾如果还有挂着的 HS，别忘了收尾
    flush_hs()
    return actions



def collapse_mixes(phases: list[list[dict]]) -> list[list[dict]]:

    """
    如果某一相位只包含 aspirate（且没有 dispense），
    则把该相位的所有动作并到下一相位的前面，并删除该相位。
    """

    def extract_src_dst(phase: List[Dict[str, Any]]):
        """
        提取一个 phase 中 aspirate/dispense 涉及的源/目标槽位和孔位。
        返回：
        {
            "src": {"slots": {...}, "wells": {...}},
            "dst": {"slots": {...}, "wells": {...}}
        }
        """
        src_slots = {a['source']['slot'] for a in phase
                    if a.get('action') == 'aspirate' and a.get('source') and 'slot' in a['source']}
        src_wells = {a['source']['well'] for a in phase
                    if a.get('action') == 'aspirate' and a.get('source') and 'well' in a['source']}

        dst_slots = {a['target']['slot'] for a in phase
                    if a.get('action') == 'dispense' and a.get('target') and 'slot' in a['target']}
        dst_wells = {a['target']['well'] for a in phase
                    if a.get('action') == 'dispense' and a.get('target') and 'well' in a['target']}

        return {
            "src": {"slots": src_slots, "wells": src_wells},
            "dst": {"slots": dst_slots, "wells": dst_wells}
        }
    
    def squeeze_asperate(phases: list[list[dict]]) -> list[list[dict]]:
        i = 0
        while i < len(phases) - 1:  # 至少要有“下一相位”才能合并
            cur = phases[i]
            kinds = {a.get("action") for a in cur}

            # 只有 aspirate（可允许有别的辅助动作），但绝对没有 dispense
            if "aspirate" in kinds and "dispense" not in kinds:
                # 并到下一相位的前面：保持时间顺序
                phases[i + 1] = cur + phases[i + 1]
                # 删除当前相位，不递增 i，这样新的 i 位置就是原来的 “下一相位”
                del phases[i]
            else:
                i += 1
        return phases

    def detect_mixes(phases: list[list[dict]]) -> list[list[dict]]:
        """把路由完全一致（src/dst 的 slot 与 well 各自都是唯一且相同）的相邻若干 phase 连续合并，
        并且在每个合并后的 phase 内，把成对的 Aspirate→Dispense（同一容器）替换为一条 `mix` 动作：
          {
            "action": "mix",
            "vol": (asp_vol, dis_vol),
            "position": {"well": str, "labware": str, "slot": int},
            "flow_rate": (asp_rate, dis_rate),
            "mix_time": int
          }
        其它动作按原顺序保留。
        """
        def _is_single(info: dict) -> bool:
            # 每个 phase 必须各自只有唯一 src_slot, dst_slot, src_well, dst_well
            return (
                len(info["src"]["slots"]) == 1 and
                len(info["dst"]["slots"]) == 1 and
                len(info["src"]["wells"]) == 1 and
                len(info["dst"]["wells"]) == 1
            )

        def _same_route(a: dict, b: dict) -> bool:
            # 路由比较：四个集合都完全相等
            return (
                a["src"]["slots"] == b["src"]["slots"] and
                a["src"]["wells"] == b["src"]["wells"] and
                a["dst"]["slots"] == b["dst"]["slots"] and
                a["dst"]["wells"] == b["dst"]["wells"]
            )

        # 先：连续合并相邻、路由完全一致的 phase
        i = 0
        while i < len(phases) - 1:
            base_info = extract_src_dst(phases[i])
            if not _is_single(base_info):
                i += 1
                continue

            j = i + 1
            merged_any = False
            while j < len(phases):
                next_info = extract_src_dst(phases[j])
                if not _is_single(next_info):
                    break
                if not _same_route(base_info, next_info):
                    break
                phases[i].extend(phases[j])
                del phases[j]
                merged_any = True
            if not merged_any:
                i += 1

        # 再：把每个 phase 内部的 AD 对替换成 mix
        def _same_container(src: dict | None, tgt: dict | None) -> bool:
            return bool(
                src and tgt and
                src.get("well") == tgt.get("well") and
                src.get("labware") == tgt.get("labware") and
                src.get("slot") == tgt.get("slot")
            )

        def _fold_pairs_into_mix(actions: list[dict]) -> list[dict]:
            out: list[dict] = []
            k = 0
            n = len(actions)
            while k < n:
                a = actions[k]
                # 尝试以 a 开头聚合一段连续 AD（同容器、同体积）的混匀
                if k + 1 < n and a.get("action") == "aspirate":
                    b = actions[k + 1]
                    if b.get("action") == "dispense" and _same_container(a.get("source"), b.get("target")):
                        base_src = a.get("source") or {}
                        base_vol_asp = a.get("vol")
                        base_vol_dis = b.get("vol")
                        base_rates = (a.get("flow_rate"), b.get("flow_rate"))
                        times = 1
                        j = k + 2
                        # 继续吞并后续完全相同的 AD 对（同容器、同体积）。速率可能不同，times 只计数，速率保留第一对。
                        while j + 1 < n:
                            x, y = actions[j], actions[j + 1]
                            if not (x.get("action") == "aspirate" and y.get("action") == "dispense"):
                                break
                            if not _same_container(x.get("source"), y.get("target")):
                                break
                            if x.get("vol") != base_vol_asp or y.get("vol") != base_vol_dis:
                                break
                            times += 1
                            j += 2
                        out.append({
                            "action": "mix",
                            "vol": (base_vol_asp, base_vol_dis),
                            "position": {
                                "well": base_src.get("well"),
                                "labware": base_src.get("labware"),
                                "slot": base_src.get("slot"),
                            },
                            "flow_rate": base_rates,
                            "mix_time": times
                        })
                        k = j
                        continue
                # 不是可折叠的一对，原样放入
                out.append(a)
                k += 1
            return out

        for idx in range(len(phases)):
            phases[idx] = _fold_pairs_into_mix(phases[idx])

        return phases
    phases = squeeze_asperate(phases)
    phases = detect_mixes(phases)
    return phases

def extract_asp_params(line):
# 例子：Aspirating 30.0 uL from A2 of reagent stock on 3 at 940.0 uL/sec
    m = re.match(r"Aspirating ([\d.]+) uL from ([A-H]\d+) of (.+) on (\d+) at ([\d.]+) uL/sec", line)
    if m:
        # 只返回体积和其它参数
        return {
            "vol": float(m.group(1)),
            "well": m.group(2),
            "labware": m.group(3).strip(),
            "slot": int(m.group(4)),
            "flow": float(m.group(5)),
        }
    return None

_MODULE_START_PATTERNS = [
    r"Setting Target Temperature of Heater-Shaker",
    r"Engaging Magnetic Module",
    r"Deactivating Temperature Module",
    r"Disengaging Magnetic Module",
    r"Setting Temperature Module",
    r"Incubating"
]
_PREPOSITIONS = [' from ', ' to ', ' on ', ' of ', ' into ']

def _read_log_text(filename: str) -> str:
    """Return log text: prefer `text` arg, else read from `filename`."""
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()

def _preprocess_text(raw: str) -> list[str]:
    """Normalize indentation-after-newline and split into non-empty lines."""
    text_ = re.sub(r'\n[ \t]+', '\n', raw)
    text_ = re.sub(r'\u00b5', 'u', text_)
    return [ln for ln in text_.strip().split('\n')]

def _filter_step_lines(lines: list[str]) -> list[str]:
    """Drop headers/noise and keep candidate step lines."""
    excluded_prefixes = [
        "Distributing",
        "Transferring",
        "/Users",
        "Congratulations!",
        "Caught exception:",
        "Deck calibration",
        "WARNING",
        "Protocol complete",
        "Seal and shake",
        "Pausing robot operation",
        "TRANSFERRING",
        "Centrifuge",
        "Removing",
        "Logs",
        "ERROR",
        "Moving to",
        "Returning tip",
        "Mixing",
        "Touching tip",
        "Transfer",
        "Protocol",
        "Air gap",
        "========",
        "~~","--",
        "THIS",
        "protocol",
        "There",
        "This protocol",
        "Homing"
              ]
    steps = []
    for line in lines:
        if not line.strip():
            continue
        if line.startswith("        "):   # deep‑indented subline
            continue
        if line.endswith(":"):            # section headers
            continue
        if any(line.startswith(p) for p in excluded_prefixes):
            continue
        # cosmetic: show semicolon-separated subphrases on next visual line
        steps.append(line.replace(";", "\n        ").strip())
    return steps

def _group_phases(steps: list[dict], module_start_regex: re.Pattern) -> list[list[str]]:
    """Group raw lines into phases separated by module ops and 'new aspirate/tip' starts."""
    grouped_phases: list[list[str]] = []
    current_phase: list[str] = []
    aspirating_seen = False
    last_sentence = ""

    for step in steps:

        if module_start_regex.search(step):
            if current_phase:
                grouped_phases.append(current_phase)
                current_phase = []
                aspirating_seen = False

        # new liquid series if a 'standalone' Aspirating or a 'Picking up tip'
        starts_with_asp = step.startswith("Aspirating")
        #guard_prev = all(x not in last_sentence for x in ("Air gap","Transferring", "Picking up tip", "Aspirating"))
        guard_prev = all(x not in last_sentence for x in (
    "Picking up tip", "Aspirating"# "Dispensing"
))
        is_tip_pick = "Picking up tip" in step

        if is_tip_pick:
            if current_phase:
                grouped_phases.append(current_phase)
                current_phase = []
            aspirating_seen = True  # 新系列开始
        elif starts_with_asp and guard_prev:
            if aspirating_seen:
                grouped_phases.append(current_phase)
                current_phase = []
            aspirating_seen = True

        last_sentence = step
        current_phase.append(step)

    if current_phase:
        grouped_phases.append(current_phase)
    return grouped_phases

def coalesce_transfer_phases(phases):
    """把相邻、方向兼容的 phase 连续合并为更大的块。返回合并后的 phases 列表（每元素仍是动作列表）。"""

    def _phase_route(actions):
        """返回 (src_slot, dst_slot) 或 None。
           - 若存在 aspirate/dispense，并且各自 slot 唯一 -> (s,d)
           - 若只有 mix，并且 mix 的 slot 唯一 -> (m,m)（就地段）
           - 否则 None
        """
        src_slots = {
            a["source"]["slot"]
            for a in actions
            if a.get("action") == "aspirate" and a.get("source") and "slot" in a["source"]
        }
        dst_slots = {
            a["target"]["slot"]
            for a in actions
            if a.get("action") == "dispense" and a.get("target") and "slot" in a["target"]
        }
        mix_slots = {
            a["position"]["slot"]
            for a in actions
            if a.get("action") == "mix" and a.get("position") and "slot" in a["position"]
        }

        if src_slots and dst_slots and len(src_slots) == 1 and len(dst_slots) == 1:
            return (next(iter(src_slots)), next(iter(dst_slots)))
        if not src_slots and not dst_slots and len(mix_slots) == 1:
            m = next(iter(mix_slots))
            return (m, m)  # 就地段
        return None

    def is_inplace(r):  # r 是 (s,d) 或 None
        return r is not None and r[0] == r[1]
    
    def can_chain(block_route, nxt_route):
        """判断 block_route 与 nxt_route 是否可合并。"""
        if block_route is None or nxt_route is None:
            return False
        # 路由完全一致
        if nxt_route == block_route:
            return True
        # 下一个是就地段，且它的 slot 与当前块的 s 或 d 重合
        if is_inplace(nxt_route) and (nxt_route[0] in block_route):
            return True
        # 当前块是就地段，而下一个是有向段：把块“定向”为下一个，并允许合并
        if is_inplace(block_route) and not is_inplace(nxt_route) and (block_route[0] in nxt_route):
            return True
        return False

    def fix_blowout(actions):

        """把blow_out动作的模版改成dispense，体积为-1，flowrate为100"""

        for a in actions:
            if a.get("action") == "blow_out":
                a["action"] = "dispense"
                a["vol"] = -1
                a["flow_rate"] = 100
                if a.get("at"):
                    a["target"] = a["at"]
                del a["at"]

    result = []
    i = 0
    while i < len(phases):
        # 以第 i 段为起点，形成一个“合并块”
        block = list(phases[i])  # 拷贝内容
        block_route = _phase_route(block)

        j = i + 1
        while j < len(phases):
            rj = _phase_route(phases[j])

            # 如果当前块是就地段，下一段是有向段且可合并，顺带把块路由“定向”为下一段的路由
            if block_route is not None and is_inplace(block_route) and rj is not None and not is_inplace(rj) and (block_route[0] in rj):
                block_route = rj  # 定向

            if can_chain(block_route, rj):
                block.extend(phases[j])
                j += 1
                continue
            break

        result.append(block)
        i = j  
    for block in result:
        fix_blowout(block)

    return result


def process_liquid_handler_log(filename: str = "test.log", name: str = "") -> List[Dict]:
    """
    Parse an Opentrons liquid‑handler log into structured phases and summarize them.
    Steps:
      1) read + preprocess
      2) filter candidate lines
      3) tokenize (debug) and group into phases
      4) merge mixing/air‑gap/consecutive ops
      5) build structured dicts and merge adjacent compatible blocks
    """
    
    raw = _read_log_text(filename)
    lines = _preprocess_text(raw)
    steps = _filter_step_lines(lines)
    module_start_regex = re.compile("|".join(_MODULE_START_PATTERNS))
    grouped_phases = _group_phases(steps, module_start_regex)
    phases = []
    for i, phase_lines in enumerate(grouped_phases):
        phases.append(_parse_liquid_ops(phase_lines))
    phases = collapse_mixes(phases)
    high_level_steps = coalesce_transfer_phases(phases)
    with open(f"steps/{name}.json", "w") as f:
        json.dump(high_level_steps, f, indent=4)

    return high_level_steps

def extract_labware_info_from_json(json_data: dict, total_slots: int) -> tuple[list, dict]:
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

    # 1) 收集“原始 slot”出现顺序（去重）
    orig_slots_in_order = []
    for lw in labware_list:
        s = lw.get("slot")
        if s is None:
            raise ValueError(f"Labware item missing 'slot': {lw}")
        if s not in orig_slots_in_order:
            orig_slots_in_order.append(s)

    # 2) 计算映射表 replace_map
    replace_map: dict[int, int] = {}

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
        orig_slot = lw.get("slot")
        new_slot = replace_map.get(orig_slot)
        if new_slot is None:
            raise RuntimeError(f"Internal mapping error: slot {orig_slot} not in replace_map.")

        # 生成新 id：把 "on X" 改成 "on {new_slot}"，再把空格换成下划线
        prcxi_id = (lw.get("name") or "").strip()
        if not prcxi_id:
            # 没有名字就用类型占位，防止空
            prcxi_id = f"{class_name} on {orig_slot}"
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


    return output, replace_map

def expend_labware_info(class_name: str, name: str = "labware", slot: int = 1):
    """
    传入：class_name（字符串），可选 name（将作为资源名；会清洗为[a-zA-Z0-9_]），slot（整数）
    返回：实例对象 或 None
    """
    if not isinstance(class_name, str) or not class_name:
        #print(f"[WARN] expend_labware_info: invalid class_name={class_name!r}")
        return None

    safe_name = f"{sanitize_name(name or 'labware')}_on_{slot}"

    try:
        cls = globals().get(class_name)
        if cls is None:
            cand, reason = match_labware_class(class_name)
            if cand is None:
                print(f"[WARN] No match for '{class_name}': {reason}")
                return None
            #print(f"[INFO] Matched '{class_name}' -> '{getattr(cand,'__name__',str(cand))}' ({reason})")
            cls = cand

        # 尝试实例化：优先带 name；如果签名里没有 name 就无参
        if isinstance(cls, type):
            try:
                inst = cls(name=safe_name)
            except TypeError:
                inst = cls()
        elif callable(cls):
            sig = inspect.signature(cls)
            if "name" in sig.parameters:
                inst = cls(name=safe_name)
            else:
                inst = cls()
        else:
            #print(f"[WARN] Candidate not callable/type: {cls}")
            return None

        #print(f"[OK] Instantiated {getattr(cls,'__name__',str(cls))} as name='{safe_name}'")
        #pprint(inst.serialize())
        return inst

    except Exception as e:
        #print(f"[ERROR] expend_labware_info('{class_name}', name='{safe_name}') -> {e}")
        return None
    
def sanitize_name(name: str) -> str:
    name = (name
            .replace("µL", "ul").replace("μL", "ul")
            .replace("µl", "ul").replace("μl", "ul")
            .replace("uL", "ul").replace("UL", "ul"))
    name = re.sub(r"[^0-9a-zA-Z_]", "_", name)
    return name

        

def _clean_micro_symbol(obj):
    if isinstance(obj, str):
        return obj.replace("\u00b5", "u").replace("µ", "u").replace("μ", "u")
    elif isinstance(obj, dict):
        return {k: _clean_micro_symbol(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_clean_micro_symbol(v) for v in obj]
    else:
        return obj


def parse_protocol(name: str):

    logfile = f"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/log/{name}.log"
    infofile = f"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protoBuilds/{name}/{name}.ot2.apiv2.py.json"

    # first check if the files exist
    if not os.path.exists(infofile):
        proto_dir = f"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protoBuilds/{name}/"
        candidates = [
            os.path.join(proto_dir, f)
            for f in os.listdir(proto_dir)
            if f.endswith(".json") and f not in ("metadata.json", "README.json")
        ]
        if candidates:
            infofile = candidates[0]
        else:
            raise FileNotFoundError(f"No protocol json found in {proto_dir}, except metadata.json/README.json")

    protocol_steps = process_liquid_handler_log(logfile, name)

if __name__ == "__main__":
    # 测试代码
    file_dir = "/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original"
    error_log = Path("log/error_converting.txt")
    protocol_names = [d for d in os.listdir(file_dir) if os.path.isdir(os.path.join(file_dir, d))]
    for name in protocol_names:
        try:
            parse_protocol(name)
        except Exception as e:
            with open(error_log, "a") as f:
                f.write(f"Error processing {name}: {str(e)}\n")

