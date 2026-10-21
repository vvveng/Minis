#!/usr/bin/env python3
"""
生成 Scripting 项目脚手架。
用法:
  python3 new_project.py <脚本名> [--type finite|page|resident|widget] [--dir /var/minis/shared/scripting] [--desc "说明"]
"""
import argparse
import json
import os
import shutil

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

TEMPLATES = {
    "finite": ("index-finite.tsx", "index.tsx"),
    "page": ("index-page.tsx", "index.tsx"),
    "resident": ("index-resident.tsx", "index.tsx"),
    "widget": ("widget.tsx", "widget.tsx"),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("name", help="脚本名")
    ap.add_argument("--type", default="page", choices=list(TEMPLATES))
    ap.add_argument("--dir", default="/var/minis/shared/scripting")
    ap.add_argument("--desc", default="")
    ap.add_argument("--icon", default="sparkles")
    ap.add_argument("--color", default="rgba(10, 132, 255, 1)")
    ap.add_argument("--author", default="WWWeng🐝")
    ap.add_argument("--version", default="1.0.0")
    args = ap.parse_args()

    root = os.path.join(os.path.abspath(args.dir), args.name)
    os.makedirs(root, exist_ok=True)

    meta = {
        "name": args.name,
        "icon": args.icon,
        "color": args.color,
        "version": args.version,
        "description": args.desc or f"{args.name} script",
        "author": {"name": args.author, "email": "", "homepage": ""},
        "contributors": [],
    }
    with open(os.path.join(root, "script.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    src, dst = TEMPLATES[args.type]
    shutil.copyfile(os.path.join(ASSETS, src), os.path.join(root, dst))
    if args.type == "widget":
        # 小组件项目也通常需要主入口
        shutil.copyfile(os.path.join(ASSETS, "index-finite.tsx"), os.path.join(root, "index.tsx"))

    print(f"已创建项目: {root}")
    print(f"  类型: {args.type}")
    for f in sorted(os.listdir(root)):
        print(f"  - {f}")
    print("\n下一步: bash scripts/check_project.sh " + root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
