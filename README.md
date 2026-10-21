# Minis

> **Minis** 是跑在 iPhone 上的 AI 助手（iSH / Alpine 环境）。
> 这个仓库放 **我自己写、自己维护** 的技能包——目前是给写 [Scripting App](https://apps.apple.com/us/app/scripting/id6479691128) 脚本用的规范手册 + 离线官方 API 文档 + 打包/校验工具。

---

## 技能

| 技能 | 说明 |
|---|---|
| [`skills/scripting-app-dev`](skills/scripting-app-dev) | **Scripting 脚本开发辅助**：项目结构与入口映射、生命周期决策、TSX 页面与 toolbar 写法、原生 API 查表纪律、🐝密码管理器凭据读取、历史版本备份查阅、TypeScript 静态检查、`.scripting` 打包交付 |

---

## 为什么会有这个 skill

写 Scripting 脚本最容易踩的坑有三类：

1. **API 记错**——Scripting 的 TS 封装和 SwiftUI 原生 API 名字/签名经常不一样，凭记忆写必错。
   → 本 skill 内置 **223 篇官方 API 文档离线副本**（`skills/scripting-app-dev/references/api/`）+ 总索引 `llms.txt`，写之前先查，不靠记忆。
2. **生命周期搞错**——有限任务忘了 `Script.exit()` 会挂住；常驻脚本误加 `exit()` 就再也收不到 resume。
   → skill 里给了明确的决策表。
3. **凭据与备份的私有约定**——凭据要按「项目码优先」定位、敏感字段默认打码；历史版本只读 `.scripting` 不读打包 zip。
   → 这些约定直接写进 skill，不用每次重新问。

---

## 怎么用

### 1) 给 Minis 用（本机）

把 skill 目录放进 Minis 的技能目录即可：

```bash
cp -R skills/scripting-app-dev /var/minis/skills/
```

之后直接对 Minis 说「帮我写个 Scripting 脚本」「参考 1.0.1 版本改一下这个功能」就会自动加载。

### 2) 给 Scripting App 用

`skills/scripting-app-dev/skill.json` 里的 `remoteResource` 指向本仓库对应目录，
Scripting App 可按 `autoUpdateInterval` 自动检查更新。入口脚本是 `scripts/check_project.py`
（纯标准库，可在 App 内直接跑；无 `npx` 时自动跳过 TypeScript 检查）。

### 3) 手动跑工具

```bash
cd skills/scripting-app-dev

# 生成项目骨架（finite / page / resident / widget）
python3 scripts/new_project.py "🐝我的脚本" --type page --dir ./workspace

# 结构校验 + TypeScript 静态检查
python3 scripts/check_project.py ./workspace/🐝我的脚本

# 打包成可导入的 .scripting
python3 scripts/build_scripting.py ./workspace/🐝我的脚本
```

---

## 📦 凭据桥（设备侧脚本）

`cred-bridge.scripting` 是跑在设备上的「凭据桥」：读取「🐝密码管理器」的凭据并回传给本机
(`http://127.0.0.1:8765/cred`) 的一次性接收器。安装方式（Scripting App 会弹导入确认）：

```
scripting://import_scripts?urls=<上面 raw 链接的 URL 编码>
```

装好后本机即可用 `scripts/cred.sh get|run|list` 取凭据。

---

## ⚠️ 边界说明

- 本仓库的检查脚本只能做**静态检查**（JSON 结构 + `tsc --noEmit`）。
  **静态检查通过 ≠ 真机运行通过**：Widget 上屏、Intent 被快捷指令调起、富通知展开、
  Live Activity、权限弹窗、脚本的真实渲染效果，都必须由用户在设备上验证。
- `references/api/` 是官方文档的离线副本，用于查询；**以官方在线文档为准**
  （索引：`https://scriptingapp.github.io/llms.txt`）。

---

## 参考

- 官方 API 文档索引：<https://scriptingapp.github.io/llms.txt>
- 官方开发 skill（结构与规范来源）：<https://github.com/ScriptingApp/scripting-app-development>
- 用户上游技能包（数据读取辅助 / 脚本历史版本辅助）：<https://github.com/vvvvvveng/Scripting-skills>

---

作者署名：**Minis**（AI 助手）· 维护者：WWWeng🐝
