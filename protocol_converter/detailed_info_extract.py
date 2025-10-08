import importlib.util
import os
import sys
sys.path.insert(0, '/Users/guangxinzhang/Documents/Deep_Potential/opentrons/api/src')
sys.path.insert(0, '/Users/guangxinzhang/Documents/Deep_Potential/opentrons/shared-data/python')
from pathlib import Path
from opentrons.simulate import simulate, format_runlog
import builtins
import inspect
import json
import os


def get_values(*names):
    caller_globals = inspect.stack()[1].frame.f_globals
    caller_file = caller_globals.get("__protocol_file__")
    if not caller_file:
        raise RuntimeError("Cannot locate the original protocol file path (__protocol_file__ not set).")
    json_path = os.path.join(os.path.dirname(caller_file), "fields.json")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"JSON config not found: {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    fields = config
    values = []
    for name in names:
        value = None
        for field in fields:
            if field.get("name") == name:
                if "default" in field:
                    value = field["default"]
                elif "options" in field and field["options"]:
                    value = field["options"][0]["value"]
                break
        if value is None:
            raise ValueError(f"Field '{name}' not found or missing default/options in {json_path}")
        values.append(value)
    return tuple(values)

builtins.get_values = get_values

error_log = Path("log/error.txt")
for file in Path("original copy").rglob("*.py"):
    print(f"Simulating: {file}")
    labware_dir = (file.parent / "labware").resolve()
    try:

        runlog, bundled = simulate(
            protocol_file=open(file, "r"),
            custom_labware_paths=[str(labware_dir)] if labware_dir.exists() and labware_dir.is_dir() else []
        )
        # delete the file name, only keep the folder name
        FOLDERNAME = file.parent.name 
        log_name = FOLDERNAME + ".log"
        log_path = Path("log") / log_name
        with open(log_path, "w") as f:
            f.write(format_runlog(runlog))
    except Exception as e:
        # 追加写入错误日志
        with open(error_log, "a") as errf:
            errf.write(f"{file} : {repr(e)}\n")
        print(f"Error simulating {file}: {e}")