#!/usr/bin/env bash
# 薄封装：真正逻辑在 check_project.py（与 Scripting App 内的 python entry 共用同一份）
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/check_project.py" "$@"
