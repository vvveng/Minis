#!/usr/bin/env bash
# 凭据取用封装：从「🐝密码管理器」取账号/密码/Token，供命令行内直接使用。
#
# 用法:
#   cred.sh get  <service> <key> [projectCode]            # 取值到临时文件；stdout 只打印文件路径
#   cred.sh run  <service> <key> [projectCode] -- <cmd...> # 以 $CRED=<明文> 注入执行命令
#   cred.sh list [service]                                 # 列出服务/账号（不含任何明文）
#
# 约定（与上游 skill「数据读取辅助」一致）:
#   * 定位优先级：projectCode（5 位项目码，全库唯一） > service(+key)
#   * 敏感字段（密码/Token/API Key）默认打码；只有明确要用来调用时才带 confirm=true
#   * 明文只落在 --out 临时文件（0600）与命令环境变量里，不进对话、不进日志
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

bridge_name_enc="$(urlenc "$BRIDGE_SCRIPT")"

run_bridge() { # $1=query string
  local q="$1"
  local token
  token="$(python3 -c 'import secrets;print(secrets.token_hex(16))')"

  rm -f "$OUT_FILE"
  : > "$LOG"

  python3 "$RECEIVER" --token "$token" --host 127.0.0.1 --port "$PORT" \
      --out "$OUT_FILE" --timeout "$TIMEOUT" > "$LOG" 2>&1 &
  local recv_pid=$!

  # 等接收器就绪
  local i=0
  while [ $i -lt 40 ]; do
    grep -q RECEIVER_READY "$LOG" && break
    sleep 0.1
    i=$((i+1))
  done
  if ! grep -q RECEIVER_READY "$LOG"; then
    echo "接收器未就绪（端口 $PORT 被占用？）" >&2
    kill "$recv_pid" 2>/dev/null
    return 3
  fi

  # 唤起设备上的「凭据桥」
  apple-open "scripting://run/${bridge_name_enc}?${q}&callback=http%3A%2F%2F127.0.0.1%3A${PORT}%2Fcred&token=${token}" >/dev/null 2>&1

  wait "$recv_pid"
  local rc=$?
  return $rc
}

payload_field() { # $1=json field
  python3 - "$1" <<'PY'
import json, sys
try:
    d = json.load(open("/tmp/.minis-cred", encoding="utf-8"))
except Exception:
    print(""); raise SystemExit(0)
v = d.get(sys.argv[1], "")
if isinstance(v, (dict, list)):
    v = json.dumps(v, ensure_ascii=False)
print(v if v is not None else "")
PY
}

cmd_get() {
  local service="$1" key="$2" code="${3:-}"
  local q="service=$(urlenc "$service")&key=$(urlenc "$key")&confirm=true"
  [ -n "$code" ] && q="$q&projectCode=$(urlenc "$code")"
  run_bridge "$q"
  local rc=$?
  if [ $rc -ne 0 ]; then
    echo "取凭据失败(rc=$rc)：$(tail -n 1 "$LOG")" >&2
    echo "提示：若设备上还没有「$BRIDGE_SCRIPT」脚本，请在 Scripting App 的桌面同步里打开它一次。" >&2
    return $rc
  fi
  if [ "$(payload_field ok)" != "True" ]; then
    echo "取凭据失败：$(payload_field error) $(payload_field hint)" >&2
    return 2
  fi
  echo "$OUT_FILE"
}

cmd_run() {
  local service="$1" key="$2" code="${3:-}"
  shift 3
  [ "${1:-}" = "--" ] && shift
  local path
  path="$(cmd_get "$service" "$key" "$code")" || return $?
  local value
  value="$(python3 -c 'import json;print(json.load(open("'"$path"'",encoding="utf-8")).get("value",""))')"
  CRED="$value" CRED_SERVICE="$(payload_field service)" CRED_KEY="$key" \
    bash -c "$*"
  local rc=$?
  # 用完即焚
  rm -f "$OUT_FILE"
  return $rc
}

cmd_list() {
  local service="${1:-}"
  local q
  if [ -n "$service" ]; then
    q="service=$(urlenc "$service")"
  else
    q="noop=1"
  fi
  run_bridge "$q"
  local rc=$?
  if [ $rc -ne 0 ]; then
    echo "取凭据失败(rc=$rc)：$(tail -n 1 "$LOG")" >&2
    return $rc
  fi
  python3 - <<'PY'
import json
d = json.load(open("/tmp/.minis-cred", encoding="utf-8"))
if d.get("ok"):
    print("服务:", d.get("service"), "| 账号数:", d.get("accountCount"))
    for a in d.get("accounts", []):
        print(f"  - 项目码 {a.get('code')} | id {a.get('id')}")
        for f in a.get("fields", []):
            print(f"      {f.get('key')}: {f.get('value')}")
else:
    print("失败:", d.get("error"), d.get("availableServices") or "")
PY
}

case "${1:-}" in
  get)  shift; cmd_get "${1:-}" "${2:-}" "${3:-}" ;;
  run)  shift; cmd_run "${1:-}" "${2:-}" "${3:-}" "$@" ;;
  list) shift; cmd_list "${1:-}" ;;
  *)    echo "用法: cred.sh get <service> <key> [projectCode] | cred.sh run <service> <key> [projectCode] -- <cmd> | cred.sh list [service]" >&2; exit 2 ;;
esac
