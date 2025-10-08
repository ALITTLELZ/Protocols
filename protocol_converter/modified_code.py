import os
import ast

INJECT_CODE = '''
from opentrons.protocol_api.labware import Well, Labware
import re
import json
all_vars = locals()

# Wells that have been processed 
processed_wells = set()
liquid_locations = {}

for var_name, var_value in all_vars.items():
    if isinstance(var_value, list) and len(var_value) > 0 and isinstance(var_value[0], Well):
        for i, well in enumerate(var_value):
            processed_wells.add(well)   
            display_name = well.display_name
            well_position = display_name.split(" of ")[0] if " of " in display_name else "unknown"
            slot_match = re.search(r" on (\\d+)$", display_name)
            slot_number = slot_match.group(1) if slot_match else "unknown"
            name_with_index = f"{var_name}[{i}]"
            liquid_locations[name_with_index] = {
                "well": well_position,
                "slot": slot_number
            }

for var_name, var_value in all_vars.items():
    if isinstance(var_value, Well):
        if var_value in processed_wells:
            continue
            
        display_name = var_value.display_name
        well_position = display_name.split(" of ")[0] if " of " in display_name else "unknown"
        slot_match = re.search(r" on (\\d+)$", display_name)
        slot_number = slot_match.group(1) if slot_match else "unknown"
        liquid_locations[var_name] = {
            "well": well_position,
            "slot": slot_number
        }
filename = f"detailed_action_json/{FOLDERNAME}.json"
output_data = {
    "event_logs": builtins.event_logs,
    "liquid_locations": liquid_locations
}

with open(filename, 'w') as f:
    json.dump(output_data, f, indent=2, default=str)
'''

def insert_code_in_run(py_path, foldername):
    with open(py_path, 'r', encoding='utf-8') as f:
        code = f.read()

    lines = code.splitlines()

    # -------- Preprocess: remove backslash line continuations --------
    processed_lines = []
    idx = 0
    while idx < len(lines):
        current = lines[idx]
        if current.rstrip().endswith('\\'):
            # 始终在行之间插入一个空格，防止关键字或运算符黏连
            stripped = current.rstrip()[:-1]
            if idx + 1 < len(lines):
                next_line = lines[idx + 1]
                merged = stripped + ' ' + next_line.lstrip()
                processed_lines.append(merged)
                idx += 2
                continue
        processed_lines.append(current)
        idx += 1
    lines = processed_lines

    # 检查整文件是否已含 event_logs 初始化
    need_eventlog = not any("builtins.event_logs" in ln for ln in lines)

    from pathlib import Path

    abs_path = str(Path(py_path).resolve())  # py_path 是你当前循环处理的 py 文件绝对路径

    eventlog_init = [
        "import builtins",
        "builtins.event_logs = []",
        f"__protocol_file__ = r\"{abs_path}\""
    ]
    if need_eventlog:
        insert_pos = 0
        # 保留 shebang 或 coding 行在文件顶部
        if lines and lines[0].startswith("#!"):
            insert_pos = 1
        if len(lines) > insert_pos and "coding" in lines[insert_pos]:
            insert_pos += 1
        lines = lines[:insert_pos] + eventlog_init + [""] + lines[insert_pos:]

    # Parse AST to locate run() definition and its indentation
    tree = ast.parse('\n'.join(lines))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "run":
            start = node.body[-1].end_lineno  # end of last line in function
            break
    else:
        print(f"run() not found in {py_path}")
        return

    # Find run() start to get indent
    for i, line in enumerate(lines):
        if line.strip().startswith('def run'):
            run_indent = len(line) - len(line.lstrip())
            break
    else:
        run_indent = 0

    # Prepare injected code with correct indentation
    indent = ' ' * (run_indent + 4)  # function body indent
    folder_code = INJECT_CODE.replace('{FOLDERNAME}', foldername)
    inject_lines = [(indent + l if l.strip() else l) for l in folder_code.splitlines()]
    
    # Insert after the last function body line
    inject_at = start #func_lines[-1] + 1
    new_lines = lines[:inject_at] + inject_lines + lines[inject_at:]
    with open(py_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    print(f"Injected into {py_path}")

def main():
    base = 'original copy/'
    for root, dirs, files in os.walk(base):
        foldername = os.path.basename(root)
        for file in files:
            if file.endswith('.py'):
                py_path = os.path.join(root, file)
                insert_code_in_run(py_path, foldername)

if __name__ == "__main__":
    main()