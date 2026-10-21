# 用户上游 Scripting skills 要点（映射到我的环境）

来源仓库：https://github.com/vvvvvveng/Scripting-skills
- `数据读取辅助/`（runtime: scripting，entry: scripts/main.ts）→ 离线副本 `references/upstream-data-read-main.ts`
- `脚本历史版本辅助/`（runtime: python，entry: scripts/backup_tool.py）

上游 skill 是给 **Scripting App 内置 agent** 用的（工具叫 `run_shell_command` / `file_tool`）。
我这边工具名不同，映射如下：

| 上游用法 | 我这里的做法 |
|---|---|
| `run_shell_command` | `shell_execute`（同样支持多行、超时、后台 `> /dev/null 2>&1 &`） |
| `file_tool`（读写） | `file_read` / `file_write` / `file_edit` |
| `scripting-ts run <skill>/scripts/main.ts --queryparameters '{...}'` | iPhone 上**没有** scripting-ts；改为把 `assets/credentials.ts` 模块**嵌入用户脚本**内直接调用 |
| 记忆写入 `memory/memories/*.md` | `memory_write`（当日日志）/ GLOBAL.md 仅用户手改，我不擅自写全局记忆 |
| 同步基线（比对 skill 文件 mtime） | 不适用（我的 skill 不会自动更新），但**上游仓库可能更新** → 需要时重新 `git clone` 比对 |

---

## 1. 数据读取辅助（凭据）

- 完整规范见 `SKILL.md` §5；可复用实现见 `assets/credentials.ts`；原始实现见 `references/upstream-data-read-main.ts`。
- 上游对 App 内 agent 的调用方式（用户在 App 里点「一键安装」后可用）：
  ```
  scripting-ts run <skill_dir>/scripts/main.ts --queryparameters '{"projectCode":"12345","key":"token","confirm":true}'
  ```
- 上游返回契约：`success` / `found` / `requiresConfirm` / `value` / `service` / `code` / `accounts` / `codes` / `flatMap` / `availableServices` / `serviceConflict` / `note` / `hint`。
- 我写用户脚本时**优先嵌入模块**（无需用户先装 skill），但要保持同样的返回语义与打码策略。

---

## 2. 脚本历史版本辅助（备份查阅）

上游用 `scripts/backup_tool.py` 扫描沙盒里的 ScriptBackups；我在 iPhone 上**读不到真机沙盒**，
所以只能：

1. 用户把 `.scripting` 备份文件传到本机（下载/分享/上传到 GitHub 后 clone）后，用标准 unzip 读取：
   ```bash
   unzip -l "xxx.scripting"
   unzip -p "xxx.scripting" "xxx/script.json"
   unzip -p "xxx.scripting" "xxx/index.tsx" | rg -n '关键词' -C 3
   ```
2. 或从 GitHub 仓库拉：
   - `vvvvveng/Scripting-releases`（当前**最新版**，文件名不带版本号）
   - `vvvvveng/Scripting-test`（脚本管理工具自动创建的公开发布仓库）
   - **历史版本仍以真机 ScriptBackups 的 `.scripting` 为准**；本地没有就问用户要不要从 GitHub 拿，**用户同意前不下载**。
3. 只读 `.scripting`，**不要**从 `全部_*.zip` 打包备份里取脚本。

备份目录规则（写文档/脚本时用）：`脚本名_版本号.scripting`；路径由 `TMPDIR` 推导为
`<沙盒>/Documents/ScriptBackups/`；`script.json` 内 `version` 字段可核对版本号。
