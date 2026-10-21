#!/usr/bin/env python3
"""
一次性凭据接收器（iSH 侧）。

设备上的「凭据桥」脚本把凭据 POST 到这里；本进程收到一条合法请求后，
把内容写入 --out 指定的文件（0600 权限），**不把明文打印到 stdout**，然后退出。

用法:
  python3 cred_receiver.py --token <一次性token> [--host 127.0.0.1] [--port 8765] [--out /tmp/.minis-cred] [--timeout 60]
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STATE = {"done": False, "payload": None, "auth_ok": False}


class Handler(BaseHTTPRequestHandler):
    token = ""
    out = ""

    def log_message(self, fmt, *args):  # 静音默认日志
        pass

    def do_GET(self):
        # 健康检查：只回一个不含凭据的状态
        body = b'{"status":"waiting"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        token = self.headers.get("X-Cred-Token") or ""
        if not token or token != Handler.token:
            self.send_response(403)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        try:
            payload = json.loads(raw.decode("utf-8", "replace"))
        except Exception:
            payload = {"ok": False, "error": "bad json"}
        # 落盘：只写文件，不打印明文
        fd = os.open(Handler.out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        os.chmod(Handler.out, stat.S_IRUSR | stat.S_IWUSR)
        STATE["done"] = True
        STATE["payload"] = payload
        STATE["auth_ok"] = True
        body = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", required=True)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--out", default="/tmp/.minis-cred")
    ap.add_argument("--timeout", type=int, default=60)
    args = ap.parse_args()

    Handler.token = args.token
    Handler.out = os.path.abspath(args.out)

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    httpd.timeout = 1
    print(f"RECEIVER_READY {args.host}:{args.port} -> {Handler.out}", flush=True)
    waited = 0
    while not STATE["done"] and waited < args.timeout:
        httpd.handle_request()
        waited += 1
    httpd.server_close()
    if not STATE["done"]:
        print("RECEIVER_TIMEOUT", flush=True)
        return 1
    # 只回状态，不回明文
    payload = STATE["payload"] or {}
    if payload.get("ok"):
        print("RECEIVED_OK", flush=True)
        return 0
    print("RECEIVED_ERR " + str(payload.get("error") or payload.get("hint") or "unknown"), flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
