#!/usr/bin/env python
"""
从 original/*.ot2.apiv2.py 生成 steps 的入口脚本。
可单独运行，不依赖 prcxi 的 pandas/networkx/pylabrobot。
"""
import sys
from pathlib import Path

if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    sys.path.insert(0, str(base))

    from protocol_from_python import batch_process_original

    if len(sys.argv) > 1:
        name = sys.argv[1]
        proto_dir = base / "original" / name
        steps_dir = base / "steps"
        if proto_dir.exists():
            from protocol_from_python import process_protocol_from_python
            process_protocol_from_python(proto_dir, steps_dir)
        else:
            print(f"协议目录不存在: {proto_dir}")
            sys.exit(1)
    else:
        print("Processing all protocols...")
        batch_process_original()
