#!/usr/bin/env python3
"""Loopback-only companion service for the Chrome extension."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "127.0.0.1"
PORT = 17832
ROOT = Path(__file__).resolve().parent
FETCHER = ROOT / "fetch_video.py"
OUTPUT = Path(r"D:\Codex\outputs\web-video-downloads")
JOBS = OUTPUT / "jobs"
ALLOWED_BROWSERS = {"chrome", "edge", "firefox", "brave", "chromium"}


def write_job(job_id: str, data: dict) -> None:
    JOBS.mkdir(parents=True, exist_ok=True)
    (JOBS / f"{job_id}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def worker(job_id: str, payload: dict) -> None:
    cmd = [sys.executable, str(FETCHER), payload["url"], "-o", str(OUTPUT)]
    if payload.get("frames"):
        cmd.append("--frames")
    browser = payload.get("cookiesFromBrowser")
    if browser in ALLOWED_BROWSERS:
        cmd += ["--cookies-from-browser", browser]
    user = payload.get("instagramUser")
    if isinstance(user, str) and user.strip():
        cmd += ["--instagram-user", user.strip()]
    write_job(job_id, {"status": "running", "command": [part for part in cmd if part != user]})
    proc = subprocess.run(cmd, text=True, capture_output=True, encoding="utf-8", errors="replace")
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result = {"status": "failed", "kind": "invalid_worker_output", "stdout": proc.stdout[-3000:], "stderr": proc.stderr[-3000:]}
    result["returncode"] = proc.returncode
    write_job(job_id, result)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def extension_origin(self) -> str | None:
        origin = self.headers.get("Origin", "")
        return origin if origin.startswith("chrome-extension://") else None

    def send_response_headers(self, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        origin = self.extension_origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def send_json(self, data: dict, status: int = 200) -> None:
        self.send_response_headers(status)
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self) -> None:
        self.send_response_headers(204)

    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_json({"ok": True, "service": "web-video-downloader", "output": str(OUTPUT)})
            return
        if self.path.startswith("/jobs/"):
            job_id = self.path.rsplit("/", 1)[-1]
            path = JOBS / f"{job_id}.json"
            if re.fullmatch(r"[0-9a-f]{12}", job_id) and path.exists():
                self.send_response_headers()
                self.wfile.write(path.read_bytes())
            else:
                self.send_json({"error": "job not found"}, 404)
            return
        self.send_json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        if not self.extension_origin():
            self.send_json({"accepted": False, "error": "仅接受 Chrome 扩展请求"}, 403)
            return
        if self.path != "/download":
            self.send_json({"error": "not found"}, 404)
            return
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 32768)
            payload = json.loads(self.rfile.read(length))
            url = payload.get("url")
            if not isinstance(url, str) or not url.startswith(("https://", "http://")):
                raise ValueError("需要有效的 http/https URL")
            job_id = uuid.uuid4().hex[:12]
            threading.Thread(target=worker, args=(job_id, payload), daemon=True).start()
            self.send_json({"accepted": True, "jobId": job_id}, 202)
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_json({"accepted": False, "error": str(exc)}, 400)


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    print(f"网页视频下载服务：http://{HOST}:{PORT}")
    print(f"输出目录：{OUTPUT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
