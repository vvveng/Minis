#!/usr/bin/env python3
"""
把 Scripting 项目目录打包成可导入的 .scripting（本质是 zip，结构为 <脚本名>/...）。
用法: python3 build_scripting.py <项目目录> [--out 输出路径]
"""
import argparse
import json
import os
import shutil
import sys
import zipfile


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", help="项目目录（含 script.json / index.tsx）")
    ap.add_argument("--out", help="输出 .scripting 路径")
    args = ap.parse_args()

    project = os.path.abspath(args.project)
    if not os.path.isdir(project):
        print(f"项目目录不存在: {project}", file=sys.stderr)
        return 2
    sj = os.path.join(project, "script.json")
    if not os.path.isfile(sj):
        print("缺少 script.json", file=sys.stderr)
        return 2
    try:
        meta = json.load(open(sj, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"script.json 解析失败: {e}", file=sys.stderr)
        return 2
    missing = [k for k in ("name", "icon", "color", "version") if not meta.get(k)]
    if missing:
        print(f"script.json 缺少必填字段: {missing}", file=sys.stderr)
        return 2
    if not os.path.isfile(os.path.join(project, "index.tsx")):
        print("缺少 index.tsx", file=sys.stderr)
        return 2

    name = meta["name"]
    out = args.out or os.path.join(os.path.dirname(project), f"{name}.scripting")
    out = os.path.abspath(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)

    skip_dirs = {".git", "node_modules", ".idea", ".vscode", "__pycache__"}
    tmp = out + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(project):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
            for f in sorted(files):
                if f.startswith("."):
                    continue
                full = os.path.join(root, f)
                rel = os.path.relpath(full, project)
                z.write(full, os.path.join(name, rel))
    shutil.move(tmp, out)

    with zipfile.ZipFile(out) as z:
        entries = z.namelist()
    print(f"打包完成: {out}")
    print(f"  脚本名: {name}  版本: {meta['version']}")
    print(f"  文件数: {len(entries)}")
    for e in entries[:20]:
        print(f"    {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
