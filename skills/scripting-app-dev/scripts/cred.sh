#!/usr/bin/env bash
# 凭据取用封装：从「🐝密码管理器」取账号/密码/Token，供命令行内直接使用。
#
# 用法:
#   cred.sh get  <service> <key> [projectCode]            # 取值到临时文件；stdout 只打印文件路径
#   cred.sh run  <service> <key> [projectCode] -- <cmd...> # 以 $CRED=<明文> 注入执行命令
#   cred.sh list [service]                                 # 列出服务/账号（不含任何明文）
#
# 传输：设备上的「凭据桥」脚本把结果回传，三条通道并行，谁先到用谁：
#   1) HTTP   → http://127.0.0.1:8765/cred（一次性 token 鉴权）
#   2) 剪贴板 → apple-clipboard（读完立刻清空）
#   3) 文件   → 设备上 <脚本目录>/__result.json（走 scripting-cli 同步通道）
#
# 铁律：明文只落在 0600 临时文件与 $CRED 环境变量里，绝不 echo 到 stdout。
set -uo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RECEIVER="$SKILL_DIR/scripts/cred_receiver.py"
BRIDGE_SCRIPT="凭据桥"
PORT="${CRED_PORT:-8765}"
OUT_FILE="${CRED_OUT:-/tmp/.minis-cred}"
TIMEOUT="${CRED_TIMEOUT:-45}"
LOG="/tmp/cred-bridge.log"

urlenc() {
  python3 - "$1" <<'PY'
import sys, urllib.parse
print(urllib.parse.quote(sys.argv[1], safe=""))
PY
}

# ⚠️ 中文脚本名必须原样放进 URL，百分号编码后 Scripting App 认不出（会静默不运行）
bridge_name="$BRIDGE_SCRIPT"

nonce() { python3 -c 'import secrets;print(secrets.token_hex(8))'; }

# 读剪贴板里的 JSON（若带 nonce 匹配）
clip_payload() {
  local want="$1"
  apple-clipboard get -q 2>/dev/null | python3 - "$want" <<'PY'
import json, sys
want = sys.argv[1]
raw = sys.stdin.read().strip()
if not raw or raw[0] not in "{[":
    raise SystemExit(0)
try:
    d = json.loads(raw)
except Exception:
    raise SystemExit(0)
if isinstance(d, dict) and want and d.get("nonce") != want:
    raise SystemExit(0)
print(json.dumps(d, ensure_ascii=False))
PY
}

wait_for_payload() { # $1=nonce → 结果写到 stdout（JSON），无则退出码 1
  local want="$1" i=0 out=""
  while [ $i -lt $((TIMEOUT * 2)) ]; do
    if [ -s "$OUT_FILE" ]; then
      out="$(cat "$OUT_FILE")"
      if [ -n "$out" ]; then
        printf '%s' "$out"
        return 0
      fi
    fi
    out="$(clip_payload "$want")"
    if [ -n "$out" ]; then
      apple-clipboard clear >/dev/null 2>&1
      printf '%s' "$out"
      return 0
    fi
    sleep 0.5
    i=$((i + 1))
  done
  return 1
}

bridge_call() { # $1=query(已编码) → 输出 JSON
  local q="$1"
  local n token
  n="$(nonce)"
  token="$(python3 -c 'import secrets;print(secrets.token_hex(16))')"

  rm -f "$OUT_FILE"
  : > "$LOG"

  python3 "$RECEIVER" --token "$token" --host 0.0.0.0 --port "$PORT" \
      --out "$OUT_FILE" --timeout "$TIMEOUT" > "$LOG" 2>&1 &
  local recv_pid=$!

  local i=0
  while [ $i -lt 40 ]; do
    grep -q RECEIVER_READY "$LOG" && break
    sleep 0.1
    i=$((i + 1))
  done

  apple-clipboard set --text "CB-WAIT:$n" >/dev/null 2>&1

  # 候选回传地址：环回 + 局域网 IP（脚本按顺序尝试）
  local lan_ip
  lan_ip="$(ip -4 -o addr show 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | grep -v '^127\.' | head -1)"
  local cbs="http%3A%2F%2F127.0.0.1%3A${PORT}%2Fcred"
  [ -n "$lan_ip" ] && cbs="$cbs%2Chttp%3A%2F%2F${lan_ip}%3A${PORT}%2Fcred"
  local url="scripting://run/${bridge_name}?${q}&nonce=${n}&clipboard=1&confirm=true&callback=${cbs}&token=${token}"
  apple-open "$url" >/dev/null 2>&1

  local payload
  payload="$(wait_for_payload "$n")"
  local rc=$?
  kill "$recv_pid" 2>/dev/null
  apple-clipboard clear >/dev/null 2>&1

  if [ $rc -ne 0 ] || [ -z "$payload" ]; then
    echo "取凭据失败：设备端未回传（receiver: $(tail -n 1 "$LOG" 2>/dev/null)）" >&2
    echo "排查：① 手机是否解锁/在前台；② Scripting App 是否已连上 scripting-cli（当前端口见 /root/sc-cli/port）；③ 设备上是否有「$BRIDGE_SCRIPT」脚本。" >&2
    return 1
  fi
  printf '%s' "$payload"
}

save_payload() { # $1=json → 写 0600 文件并打印路径
  printf '%s' "$1" > "$OUT_FILE"
  chmod 600 "$OUT_FILE"
  echo "$OUT_FILE"
}

cmd_get() {
  local service="$1" key="$2" code="${3:-}"
  local q="service=$(urlenc "$service")&key=$(urlenc "$key")"
  [ -n "$code" ] && q="$q&projectCode=$(urlenc "$code")"
  local payload rc
  payload="$(bridge_call "$q")"; rc=$?
  [ $rc -ne 0 ] && return $rc
  if [ "$(printf '%s' "$payload" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("ok"))' 2>/dev/null)" != "True" ]; then
    echo "取凭据失败：$(printf '%s' "$payload" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("error"),d.get("hint") or "")' 2>/dev/null)" >&2
    return 2
  fi
  save_payload "$payload"
}

cmd_run() {
  local service="$1" key="$2" code="${3:-}"
  shift 3
  [ "${1:-}" = "--" ] && shift
  local path value
  path="$(cmd_get "$service" "$key" "$code")" || return $?
  value="$(python3 -c 'import json;print(json.load(open("'"$path"'",encoding="utf-8")).get("value",""))')"
  CRED="$value" bash -c "$*"
  local rc=$?
  rm -f "$OUT_FILE"
  return $rc
}

cmd_list() {
  local service="${1:-}"
  local q
  if [ -n "$service" ]; then q="service=$(urlenc "$service")"; else q="noop=1"; fi
  local payload rc
  payload="$(bridge_call "$q")"; rc=$?
  [ $rc -ne 0 ] && return $rc
  printf '%s' "$payload" | python3 -c '
import json, sys
d = json.load(sys.stdin)
if d.get("ok"):
    print("服务:", d.get("service"), "| 账号数:", d.get("accountCount"))
    for a in d.get("accounts", []):
        print(f"  - 项目码 {a.get(\"code\")} | id {a.get(\"id\")}")
        for f in a.get("fields", []):
            print(f"      {f.get(\"key\")}: {f.get(\"value\")}")
else:
    print("失败:", d.get("error"), d.get("availableServices") or "")
'
}

case "${1:-}" in
  get)  shift; cmd_get "${1:-}" "${2:-}" "${3:-}" ;;
  run)  shift; cmd_run "${1:-}" "${2:-}" "${3:-}" "$@" ;;
  list) shift; cmd_list "${1:-}" ;;
  *)    echo "用法: cred.sh get <service> <key> [projectCode] | cred.sh run <service> <key> [projectCode] -- <cmd> | cred.sh list [service]" >&2; exit 2 ;;
esac
