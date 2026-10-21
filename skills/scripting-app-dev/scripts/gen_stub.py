#!/usr/bin/env python3
"""
生成 assets/scripting-stub.d.ts：
把官方 llms.txt 索引里的 API 名称 + 视图组件路径名，导出成宽松的 any 声明，
让本地 tsc 能在没有 App 同步 .d.ts 的情况下做语法/类型检查。
"""
import json
import os
import re

LLMS = "/var/minis/skills/scripting-app-dev/references/llms.txt"
OUT = "/var/minis/skills/scripting-app-dev/assets/scripting-stub.d.ts"

# 官方文档里以「全局对象」形式出现的 API（不需要 import）
GLOBALS = ["FileManager"]

IDENT = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")

# 明显不是 API 符号的标题
SKIP_TITLES = {
    "example", "common", "chaining view modifiers", "animation and transition",
    "app events", "device formats", "background urlsession", "data",
}


# 文档标题不是标识符、但确实是 API 的常见名字（视图组件 / 运行时模块）
EXTRA = {
    # 布局与容器
    "VStack", "HStack", "ZStack", "Grid", "GridRow", "GridItem", "ScrollView",
    "LazyVStack", "LazyHStack", "List", "Section", "Group", "Spacer", "Divider",
    "NavigationStack", "NavigationSplitView", "NavigationLink", "TabView",
    "TabItem", "Form", "DisclosureGroup", "LabeledContent", "Menu", "Gauge",
    # 控件
    "Text", "Button", "Toggle", "TextField", "SecureField", "Slider", "Stepper",
    "Picker", "DatePicker", "ColorPicker", "ProgressView", "Image", "Link",
    "ActivityIndicator", "Video", "WebView", "EditButton", "ShareLink",
    # 运行时模块
    "Script", "Navigation", "Widget", "Storage", "FileManager", "Device",
    "Notification", "Intent", "AppIntent", "BackgroundKeeper", "CloudSharedData",
    "Pasteboard", "Keychain", "WebScraper", "LanguageModelSession", "AlarmManager",
    "Calendar", "Reminder", "Location", "Photos", "Speech", "SpeechRecognition",
    "DocumentPicker", "Crypto", "JWT", "AppStore", "HapticFeedback", "Weather",
    "QuickLook", "PDF", "ShareSheet", "Safari", "Send_Mail", "Send_Message",
    "TextInput", "DateFormatter", "Data", "UUID", "URL", "Color", "Font",
}


def main() -> None:
    text = open(LLMS, encoding="utf-8").read()
    entries = re.findall(r"^\- \[([^\]]+)\]\((/[^)]+)\):", text, re.M)

    names = set()
    for title, path in entries:
        if path.startswith("/guide/Changelog"):
            continue
        t = title.strip()
        if t.lower() in SKIP_TITLES:
            continue
        if IDENT.match(t):
            names.add(t)
        # 从路径末段再取一次组件名（例：.../Layout/VStack/index.md → VStack）
        seg = [s for s in path.split("/") if s not in ("", "guide", "index.md", ".md")]
        if seg:
            last = seg[-1]
            last = last[:-3] if last.endswith(".md") else last
            if IDENT.match(last):
                names.add(last)
    names |= EXTRA

    lines = [
        "/**",
        " * 本地 tsc 检查用的宽松类型兜底（由 scripts/gen_stub.py 生成，勿手改）。",
        " * 真正的精确签名以 App 同步下来的 .d.ts 或官方文档为准。",
        " */",
        "",
        "declare namespace JSX {",
        "  interface Element {}",
        "  interface ElementChildrenAttribute { children: {} }",
        "  interface IntrinsicElements { [name: string]: any }",
        "}",
        "",
        "declare module \"scripting\" {",
    ]
    for n in sorted(names):
        lines.append(f"  export const {n}: any")
    lines += [
        "  const _default: any",
        "  export default _default",
        "}",
        "",
    ]
    for g in GLOBALS:
        lines.append(f"declare const {g}: any")
    lines.append("")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write("\n".join(lines))
    print(f"stub written: {OUT} ({len(names)} exports)")


if __name__ == "__main__":
    main()
