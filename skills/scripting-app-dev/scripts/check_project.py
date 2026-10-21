#!/usr/bin/env python3
"""
Scripting 项目结构校验 + TypeScript 静态检查。

用法:
  python3 check_project.py <项目目录> [--no-tsc] [--skill-dir <skill目录>]

注意：静态检查通过 ≠ 真机运行通过。Widget / Intent / 富通知 / Live Activity
等宿主行为只能在真机验证。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REQUIRED_FIELDS = ("name", "icon", "color", "version")
ENTRY_FILES = (
    "widget.tsx",
    "live_activity.tsx",
    "notification.tsx",
    "intent.tsx",
    "app_intents.tsx",
    "browser.tsx",
    "keyboard.tsx",
    "spotlight.tsx",
)
# 这些 TS 错误码表示「类型没收录」，不算硬错误
SOFT_CODES = ("TS2305", "TS7016")


def default_skill_dir() -> str:
    # Scripting App 的 Python 运行时可能没有 __file__
    try:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        return os.path.abspath(".")


def check_structure(project: str) -> list[tuple[str, str]]:
    problems: list[tuple[str, str]] = []
    notes: list[tuple[str, str]] = []

    sj = os.path.join(project, "script.json")
    if not os.path.isfile(sj):
        problems.append(("FAIL", "缺少 script.json"))
    else:
        try:
            meta = json.load(open(sj, encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            problems.append(("FAIL", f"script.json 解析失败: {exc}"))
            meta = None
        if isinstance(meta, dict):
            missing = [k for k in REQUIRED_FIELDS if not meta.get(k)]
            if missing:
                problems.append(("FAIL", f"script.json 缺少必填字段: {', '.join(missing)}"))
            else:
                notes.append(
                    ("OK", f"script.json: name={meta['name']} version={meta['version']}")
                )

    if not os.path.isfile(os.path.join(project, "index.tsx")):
        problems.append(("FAIL", "缺少 index.tsx（主入口）"))
    else:
        notes.append(("OK", "index.tsx"))

    for f in ENTRY_FILES:
        if os.path.isfile(os.path.join(project, f)):
            notes.append(("INFO", f"额外入口: {f}"))

    return problems, notes


REAL_DTS = "/var/minis/shared/scripting/dts"


def run_tsc(project: str, skill_dir: str) -> tuple[list[str], list[str], str]:
    """返回 (硬错误, 软告警, 说明)"""
    if shutil.which("npx") is None:
        return [], [], "未找到 npx，跳过 tsc（可 apk add nodejs）"

    tmp = tempfile.mkdtemp(prefix="scripting-check-")
    try:
        for item in os.listdir(project):
            src = os.path.join(project, item)
            dst = os.path.join(tmp, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copyfile(src, dst)

        # 优先用 App 同步下来的真实类型声明（CLI 工作区 dts/），否则退回宽松 stub
        real_dts = os.path.join(REAL_DTS, "scripting.d.ts")
        if os.path.isfile(real_dts):
            os.makedirs(os.path.join(tmp, "dts"), exist_ok=True)
            for f in os.listdir(REAL_DTS):
                if f.endswith(".d.ts"):
                    shutil.copyfile(os.path.join(REAL_DTS, f), os.path.join(tmp, "dts", f))
            tsconfig = {
                "compilerOptions": {
                    "target": "ESNext",
                    "lib": ["esnext"],
                    "strict": True,
                    "esModuleInterop": True,
                    "allowSyntheticDefaultImports": True,
                    "module": "CommonJS",
                    "moduleResolution": "node",
                    "resolveJsonModule": True,
                    "skipLibCheck": True,
                    "noEmit": True,
                    "jsx": "react",
                    "jsxFactory": "createElement",
                    "jsxFragmentFactory": "Fragment",
                    "types": [],
                    "paths": {"scripting": ["./dts/scripting.d.ts"]},
                },
                "include": ["./dts/*.d.ts", "**/*.ts", "**/*.tsx"],
                "exclude": ["./dts/scripting.d.ts"],
            }
            mode = "真实 dts"
        else:
            stub = os.path.join(skill_dir, "assets", "scripting-stub.d.ts")
            if os.path.isfile(stub):
                shutil.copyfile(stub, os.path.join(tmp, "scripting-stub.d.ts"))
            tsconfig = {
                "compilerOptions": {
                    "target": "ES2020",
                    "module": "ESNext",
                    "moduleResolution": "bundler",
                    "jsx": "preserve",
                    "strict": False,
                    "noEmit": True,
                    "skipLibCheck": True,
                    "esModuleInterop": True,
                    "types": [],
                    "lib": ["ES2020", "DOM"],
                },
                "include": ["**/*.ts", "**/*.tsx"],
            }
            mode = "宽松 stub"

        json.dump(tsconfig, open(os.path.join(tmp, "tsconfig.json"), "w", encoding="utf-8"), indent=2)

        proc = subprocess.run(
            ["npx", "-y", "-p", "typescript@5", "tsc", "-p", "tsconfig.json", "--noEmit"],
            cwd=tmp,
            capture_output=True,
            text=True,
            timeout=900,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        errors = [l for l in out.splitlines() if re.search(r"error TS\d+", l)]
        hard = [l for l in errors if not any(code in l for code in SOFT_CODES)]
        soft = [l for l in errors if any(code in l for code in SOFT_CODES)]
        note = f"tsc 无语法/类型错误（{mode}）" if not errors else f"tsc 发现 {len(errors)} 条问题（{mode}）"
        return hard, soft, note
    except FileNotFoundError:
        return [], [], "npx 不可用，跳过 tsc"
    except subprocess.TimeoutExpired:
        return [], [], "tsc 超时，已跳过"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--no-tsc", action="store_true")
    ap.add_argument("--skill-dir", default=default_skill_dir())
    args = ap.parse_args()

    project = os.path.abspath(args.project)
    if not os.path.isdir(project):
        print(f"项目目录不存在: {project}", file=sys.stderr)
        return 2

    print(f"== 项目: {project}")
    problems, notes = check_structure(project)
    for level, msg in notes:
        print(f"  [{level}] {msg}")
    for level, msg in problems:
        print(f"  [{level}] {msg}")

    hard: list[str] = []
    if not args.no_tsc:
        hard, soft, note = run_tsc(project, args.skill_dir)
        if hard:
            print("  [FAIL] TypeScript 错误:")
            for l in hard:
                print(f"         {l}")
        else:
            print(f"  [OK] {note}")
        if soft:
            print("  [WARN] 未收录的 API 符号（可能 stub 未覆盖，请查官方 llms.txt 确认）:")
            for l in soft:
                print(f"         {l}")

    print()
    if problems or hard:
        print("== 检查未通过")
        return 1
    print("== 检查通过（注意：这不等于真机验证通过）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
