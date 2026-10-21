---
name: scripting-app-dev
version: 1.0.0
description: 写/改 Scripting App(iOS) 脚本时的规范手册：项目结构(script.json/index.tsx/各入口)、生命周期、TSX 页面与 toolbar 写法、原生 API 查表纪律、🐝密码管理器凭据读取(项目码优先+敏感打码)、历史版本备份查阅、TypeScript 静态检查与 .scripting 打包交付。当用户提到 Scripting、脚本、index.tsx、script.json、TSX、小工具、Widget、Intent、App Group、🐝密码管理器 时使用。
runtime: python
entry: scripts/check_project.py
metadata:
  display_name: "Scripting 脚本开发辅助"
  author: "Minis"
  repository: "https://github.com/vvvvvveng/Minis"
  last_updated: "2026-10-21"
  intent_patterns: "写脚本, 改脚本, Scripting, index.tsx, script.json, TSX, Widget, Intent, 脚本打包, 脚本历史版本, 密码管理器凭据, 需要 token, 需要 api key"
  required_tools: "run_shell_command, file_tool"
  openclaw:
    emoji: "📜"
    requires:
      bins: ["node", "npx", "python3", "rg", "unzip"]
---

# Scripting App 脚本开发规范（Minis 自用手册）

本 skill 面向 **我（Minis / iSH 环境）**，不是面向 Scripting App 内部的 agent。
目标：以后写 Scripting 脚本时不用再从零摸索——结构、API、用户的私有约定、校验与交付流程都已固化。

---

## 0.1 快速开始（照抄即可）

```bash
SKILL=/var/minis/skills/scripting-app-dev

# 1) 生成项目骨架（finite / page / resident / widget）
python3 $SKILL/scripts/new_project.py "🐝我的脚本" --type page --dir /var/minis/shared/scripting

# 2) 写码时随时查 API（离线官方文档）
rg -n 'present\(' $SKILL/references/api/Views_Modal_presentaions_index_md.md
rg -il 'notification' $SKILL/references/api/ | head

# 3) 静态检查（结构 + tsc）
bash $SKILL/scripts/check_project.sh "/var/minis/shared/scripting/🐝我的脚本"

# 4) 打包成可导入的 .scripting
python3 $SKILL/scripts/build_scripting.py "/var/minis/shared/scripting/🐝我的脚本"

# 5) 需要读凭据时把模块拷进项目
cp $SKILL/assets/credentials.ts "/var/minis/shared/scripting/🐝我的脚本/"
```

---

## 0. 一句话定位

Scripting = iOS 上的 TypeScript/TSX 脚本 App。
一个脚本 = 一个目录：`<脚本名>/script.json` + `<脚本名>/index.tsx`（可选其它入口文件），
打包后是 `.scripting`（本质是 zip），可导入 App 或存进 ScriptBackups 做历史版本。

---

## 1. 职责边界（先想清楚，别吹牛）

| 谁 | 负责 |
|---|---|
| 我（Minis / iSH） | 写代码、查官方 API、tsc 静态检查、打包 `.scripting`、读历史备份 |
| Scripting App（真机） | 运行脚本、渲染 UI、申请权限、Widget/Intent 等宿主行为 |

**硬规则**

- iPhone 上**没有 `scripting-ts` 运行时**，我跑不了 Scripting 代码。只能声称"通过 tsc 静态检查"，**禁止声称"已运行/已验证"**。
- Widget / Intent / 富通知 / Live Activity / Safari 的系统宿主行为**只能用户在设备上验证**，交付时必须写出最短验证步骤。
- 需要真机同步调试 → 让用户在 Mac 上装 Node 20+ 跑 `npx scripting-cli start`（见 `references/api-cheatsheet.md`）。

---

## 2. 项目结构与入口映射

```
<脚本名>/
├── script.json      必需：name / icon / color / version
├── index.tsx        必需：主入口（App 内运行）
├── widget.tsx       桌面小组件
├── live_activity.tsx 锁屏/灵动岛
├── notification.tsx 富通知展开 UI
├── intent.tsx       快捷指令 / 分享面板
├── app_intents.tsx  App Intent（小组件/实时活动/控制中心）
├── browser.tsx      Safari 浏览器脚本
└── 其它：keyboard.tsx / spotlight.tsx / translation_ui_provider.tsx /
         home_screen_default_ui.tsx / control_widget_button.tsx /
         control_widget_toggle.tsx / assistant_tool.tsx / alarm_live_activity.tsx
```

规则：

- 只创建用户**需要**的入口文件，不要全塞。
- `script.json` 必须含 `name`、`icon`、`color`、`version`；`name` 默认与目录同名。
- `intentInputTypes` 只在有 `intent.tsx` 时加；`runInApp` 只在需要 App 内呈现时加。
- 业务逻辑放普通 `.ts`/`.tsx` 模块，入口文件只做"取参数 → 调逻辑 → 渲染/返回 → 收尾"。

---

## 3. 生命周期决策（选错了会挂起或白屏）

| 场景 | 写法 |
|---|---|
| 一次性任务（抓取并保存、排队通知） | 结束时 `Script.exit()` |
| 一次性页面 | `await Navigation.present(<Page/>)` → 关闭后 `Script.exit()` |
| 常驻/需保留状态、需被通知/小组件/URL 再次唤醒 | `Script.onResume(...)`；**不要**紧接着无条件 `Script.exit()`，需要时用 `Script.minimize()` |
| `intent.tsx` 返回 | 每条路径都要 `Script.exit(value)` 返回结果 |

> 有限任务必须 `Script.exit()`，否则事件循环不结束、脚本挂住。

---

## 4. API 使用纪律（最容易出错的地方）

**禁止凭记忆写 Scripting API。** Scripting 的 JS/TS 封装和 SwiftUI 原生 API 名字/签名常常不一样。

查表顺序：

1. 本地离线文档：`references/api/*.md`（138 篇官方页，已抓取）+ 总索引 `references/llms.txt`
2. 精确检索示例：
   ```bash
   rg -n '^\s*### `FileManager\.' /var/minis/skills/scripting-app-dev/references/api/FileManager.md
   rg -il 'navigation' /var/minis/skills/scripting-app-dev/references/api/
   rg -n 'Script\.(exit|run|onResume)' /var/minis/skills/scripting-app-dev/references/api/Script.md
   ```
3. 官方在线索引（本地缺项时）：`https://scriptingapp.github.io/llms.txt`，正文路径形如 `/guide/Utilities/FileManager.md`

确认这些再落笔：模块/全局、函数名与参数、返回值、是否 async、权限与授权弹窗、iOS 版本可用性、宿主限制。

**导入约定**：`import { Script, Navigation, ... } from "scripting"`；官方标注为全局的 API 不要 import，也不要瞎猜。

**已验证的高频 API**（详见 `references/api-cheatsheet.md`）

- `Script`：`name` / `directory` / `env` / `widgetParameter` / `queryParameters` / `metadata` / `exit(result?)` / `run(options)` / `createRunURLScheme(...)` / `hasFullAccess()`
- `FileManager`：`documentsDirectory` / `iCloudDocumentsDirectory` / `appGroupDocumentsDirectory` / `scriptsDirectory` / `temporaryDirectory` / `exists(Sync)` / `readAsString(Sync)` / `writeAsString(Sync)` / `createDirectory(Sync)` / `readDirectory(Sync)` / `copyFile(Sync)` / `remove(Sync)` / `zip(Sync)` / `unzip(Sync)` / `stat(Sync)`
- `Storage`：键值持久化；`Device`、`Notification`、`Calendar`、`Reminder`、`Location`、`Speech`、`Photos`、`DocumentPicker`、`WebScraper`、`JWT`、`Crypto`、`CloudSharedData`、`BackgroundKeeper`、`AlarmManager`
- 视图：`Text` `Button` `List` `Form` `Image` `Toggle` `TextField` `Slider` `Picker` `DatePicker` `ProgressView` `VStack` `HStack` `Grid` `ScrollView` `NavigationStack` `TabView` `Navigation` `Widget`

**TSX 关键点**：`toolbar` 是**视图属性**（`ToolBarProps` 对象），不是 SwiftUI 的 `.toolbar { }` 修饰器，也**不要**挂在 `NavigationStack` 上，要挂在 `List`/`VStack`/`ScrollView` 等可见页面上。
`ToolBarProps` 可用槽位：`topBarLeading` `topBarTrailing` `principal` `primaryAction` `confirmationAction` `cancellationAction` `destructiveAction` `navigation` `bottomBar` `keyboard`（值可为单个节点或数组）。

---

## 5. 🐝密码管理器凭据读取（用户私有约定，必读）

用户有专门的「🐝密码管理器」脚本，脚本需要账号/Token 时**从它读，不要反问用户要**。

**存储路径**（App Group UUID 每台设备不同，**永远动态拼接，禁止硬编码绝对路径**）：

```typescript
const credentialsPath =
  FileManager.appGroupDocumentsDirectory + "/🐝密码管理器/credentials.json"
```

**数据结构**：`data.services[服务名]` → 账号数组 → `fields[]`（`key` / `title` / `value` / `secure`）。
字段 key 约定：`account`(账号/用户名) `password`(密码,secure) `userId`(用户ID) `token`(Token/API Key,secure) `custom`(备注)。
服务名大小写不敏感（存的是 `Github` 也能用 `github` 命中）。
**项目码 `code`**：5 位数字（10000–99999）、全库唯一、生成后永不变，**优先用它定位账号**。

**定位优先级**：`projectCode` > `service`(+`key`)。
两者都传且指向不同账号 → 以项目码为准，并回 `serviceConflict: true` + `note`（不报错、不取错项）。
没有项目码时，先按服务读（不传 key），返回结果里带各账号的 `code`，再精确调用。

**安全规则（硬性）**

- secure 字段（密码/Token/API Key）默认返回打码值 `*** (加密隐藏)` + `requiresConfirm: true`；
  只有用户**明确要求使用**（如"用我的 GitHub token 调 API"）才带 `confirm: true` 读明文。
- 拿到明文后**不要**打印进对话、**不要**写进任何文件或记忆，只在命令行内直接使用（如 `curl -H "Authorization: Bearer $TOKEN"`）。
- 批量读（不指定 key）时 secure 字段只给 key/title，`flatMap` 只含非 secure 字段。

现成实现（可直接嵌进用户脚本或改用）：`assets/credentials.ts`（模块化版）、`references/api/` 外的原始实现见 `references/upstream-skills.md`。
用户端可执行版本：`scripting-ts run <skill_dir>/scripts/main.ts --queryparameters '{"projectCode":"12345","key":"token","confirm":true}'`。

### 5.1 在本机（iSH/Minis）怎么取到凭据 ⚠️ 关键

**iOS 沙盒隔离：iSH 读不到 Scripting 的 App Group 容器**（`/var/mobile` 在 iSH 里根本不存在），
所以我**不能直接打开** `credentials.json`。必须走一条"设备 → 本机"的桥。

已就绪的桥（`assets/凭据桥/` + `scripts/cred_receiver.py` + `scripts/cred.sh`）：

| 角色 | 位置 | 作用 |
|---|---|---|
| 设备侧脚本 | `assets/凭据桥/index.tsx`（已部署到 CLI 工作区 `scripts/凭据桥/`） | 在设备上读凭据 → POST 到 `http://127.0.0.1:8765/cred`（带一次性 token） |
| 本机接收器 | `scripts/cred_receiver.py` | 收一条请求，把结果写进 0600 临时文件，**明文不打印到 stdout**，然后退出 |
| 取用封装 | `scripts/cred.sh` | `get` 取值到文件（stdout 只给路径）/ `run` 以 `$CRED` 注入执行命令 / `list` 列服务与项目码 |

```bash
SKILL=/var/minis/skills/scripting-app-dev
bash $SKILL/scripts/cred.sh list                 # 列出服务与项目码（无明文）
bash $SKILL/scripts/cred.sh get github token     # → 打印临时文件路径
bash $SKILL/scripts/cred.sh run github token -- 'curl -s -H "Authorization: Bearer $CRED" https://api.github.com/user'
```

**铁律**：`cred.sh get` 只能拿路径，`cred.sh run` 才能用值；**永远不要把明文 echo/print 到命令输出**，
否则会进对话上下文和日志。用完 `rm -f /tmp/.minis-cred`。

**触发前提**：设备上要有「凭据桥」这个脚本。
`scripting://run/<脚本名>` 可唤起（**中文名不要百分号编码**，编码后 App 认不出；`apple-open` 偶发 opened:false，重试即可）。
若设备上还没有该脚本，让用户在 Scripting App 的**桌面同步**里点开它一次，之后 CLI 会热推更新。

**更安全的替代**：不需要明文时，把"要做的动作"写成 Scripting 脚本，让脚本在设备上自己读凭据并完成
（调 API / 写文件 / 发通知）——凭据完全不出设备，这是首选。

**已核实的实现细节**（来自 `🐝密码管理器` 源码 2026-09-07 版）：
- 凭据路径确为 `FileManager.appGroupDocumentsDirectory + "/🐝密码管理器/credentials.json"`（另有 legacy 路径 `.../scripting-agent/workspace/default/credentials.json`，App 会自动迁移）。
- 账号结构：`services[服务名][] → { id, fields[], code? }`；`fields[]` 的 `secure` 标记密码/Token/OTP。
- 该发布版**还没有 `code`（项目码）字段**；若设备上的版本更新则有。桥接脚本把 `code` 当可选，缺失时自动退回按 service 定位。



---

## 6. 历史版本 / 备份查阅

- 备份目录（真机沙盒，UUID 随设备变化，**不要硬编码**）：
  `/private/var/mobile/Containers/Data/Application/<UUID>/Documents/ScriptBackups/`
  实际可用路径由 `TMPDIR`（= `<沙盒>/tmp/`）推导：去掉 `/tmp` 拼 `Documents/ScriptBackups`。
- 命名：`脚本名_版本号.scripting`（如 `🐝浏览器_1.0.1.scripting`）；`script.json` 里有 `version` 字段可核对。
- **只读 `.scripting`，绝不从 `全部_*.zip` 打包备份里取脚本**（打包 zip 只用于整体备份/恢复）。
- `.scripting` 就是 zip → 本地直接 `unzip -l` / `unzip -p` 读 `index.tsx`、`script.json`，无需工具脚本：
  ```bash
  unzip -l "/path/xxx.scripting"
  unzip -p "/path/xxx.scripting" "xxx/script.json"
  unzip -p "/path/xxx.scripting" "xxx/index.tsx" | rg -n '关键词' -C 3
  ```
- 本地找不到再问用户是否从 GitHub 拉（默认仓库 `vvvvveng/Scripting-releases`，只有**当前最新版**，不含历史版本）；**用户同意前不下载**。

---

## 7. 交付流程（照这个顺序走）

1. **读现状**：改已有脚本前先读 `script.json` + `index.tsx` + 相关入口文件；不要凭猜重写。
2. **落盘**：项目放在 `/var/minis/shared/scripting/<脚本名>/`（跨会话保留），临时试验放 `/var/minis/workspace/`。
3. **静态检查**：`bash scripts/check_project.sh <项目目录>`（结构校验 + tsc 类型检查，用 `assets/scripting-stub.d.ts` 兜底未安装的 `scripting` 类型）。
4. **打包**：`python3 scripts/build_scripting.py <项目目录>` → 生成 `<脚本名>.scripting`，可直接让用户在 Scripting App 导入。
5. **给用户交付**：说明改了哪些文件、用了哪些官方 API、静态检查结果、**还需要用户在设备上做什么**（手动验证步骤）。

**证据等级（写话时不要升级措辞）**

| 我能提供的证据 | 只能证明 |
|---|---|
| JSON/schema 检查 | 描述文件可解析、字段齐全 |
| tsc 类型检查 | 没有已知语法/类型错误 |
| 代码走查 | 逻辑在纸面上自洽 |
| — | **不能**证明真机运行、权限弹窗、Widget 上屏、Intent 被调起 |

用户端真机验证：`scripting-ts project "<name>"` 或 App 内直接运行。

---

## 8. 用户脚本的额外约定

- **元数据**：`script.json` 里维护 `version`、`author`（name/email/homepage）、`contributors`；改动功能后按项目惯例升版本号，并在 `description` 里同步中文说明。
- **UI 风格**：iOS 26 风格，同时**兼容 iOS 18**（新 API 先查 `references/api/` 里的版本标注）。
- **命名**：用户脚本常带 emoji（🐝浏览器、🐝密码管理器）；文件名匹配按"包含关系"，别只做全等。
- **边界**：不擅自改脚本名/图标/配色/已有入口结构；不主动翻 ScriptBackups 做无关对比；改 README/更新日志前先问。

---

## 9. 常见坑（写完自查）

1. 忘了 `Script.exit()` → 脚本挂住不返回。
2. `toolbar` 写成 SwiftUI 的 `.toolbar {}` 或挂在 `NavigationStack` 上 → 工具栏不出现。
3. 硬编码 App Group / iCloud 绝对路径 → 换设备就废。
4. 凭据 secure 字段直接明文回显 → 泄露风险（见 §5）。
5. `FileManager` 同步方法阻塞主线程 → 优先用 `await` 版本。
6. 从 SwiftUI 记忆猜 API 名 → 必查 `references/api/`。
7. `Grid`/`ScrollView` 里放无约束高度纵向布局 → 布局崩。
8. 声称"已测试通过" → 只能说"tsc 通过"，宿主行为交给用户验。

---

## 10. 文件清单

```
scripting-app-dev/
├── SKILL.md                      本文件
├── references/
│   ├── llms.txt                  官方 API 总索引（rg 检索用）
│   ├── api/                      官方 API 文档离线副本（223 篇，含来源映射 _index.json）
│   ├── api-cheatsheet.md         高频 API 速查（已核对签名）
│   ├── upstream-skills.md        用户上游两个 Scripting skill 的要点 + 工具映射
│   ├── upstream-data-read-main.ts   上游「数据读取辅助」原始实现
│   └── upstream-backup_tool.py      上游「脚本历史版本辅助」原始工具
├── assets/
│   ├── script.json               脚本元数据模板
│   ├── index-finite.tsx          一次性脚本模板
│   ├── index-page.tsx            一次性页面模板
│   ├── index-resident.tsx        常驻/可恢复模板
│   ├── widget.tsx                小组件模板
│   ├── credentials.ts            🐝密码管理器凭据读取模块
│   ├── 凭据桥/                    设备侧桥接脚本（index.tsx + script.json）
│   ├── scripting-stub.d.ts       本地 tsc 检查用的类型兜底（gen_stub.py 生成）
│   └── tsconfig.check.json       检查用 tsconfig
└── scripts/
    ├── check_project.sh          项目结构校验 + tsc 检查（薄封装）
    ├── check_project.py          校验逻辑（优先用 CLI 同步下来的真实 dts，退回 stub）
    ├── cred.sh                   凭据取用封装（get / run / list）
    ├── cred_receiver.py          本机一次性凭据接收器
    ├── build_scripting.py        打包成 .scripting
    ├── new_project.py            脚手架生成
    └── gen_stub.py               重新生成 scripting-stub.d.ts
```

上游来源：官方 `https://github.com/ScriptingApp/scripting-app-development`（API 索引 `https://scriptingapp.github.io/llms.txt`）、
用户仓库 `https://github.com/vvvvvveng/Scripting-skills`（数据读取辅助 / 脚本历史版本辅助）。
