# -*- coding: utf-8 -*-
"""edge-tts 朗读桥接：Windows 双击「双击启动桥接.bat」运行（或直接运行本脚本）。
启动后艾宾浩斯单词本网页自动改用 edge-tts 神经网络语音。
仅监听 127.0.0.1，不对外网开放。关闭本窗口即停止服务。
依赖：Python 3.8+；edge-tts 缺失时首次运行自动安装。"""
import asyncio
import json
import re
import subprocess
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    import edge_tts
except ImportError:
    print("首次运行：正在自动安装 edge-tts，请稍候…")
    if subprocess.call([sys.executable, "-m", "pip", "install", "edge-tts"]) != 0:
        print("默认源失败，改用清华镜像重试…")
        subprocess.call([sys.executable, "-m", "pip", "install", "edge-tts",
                         "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"])
    try:
        import edge_tts
    except ImportError:
        print("edge-tts 安装失败：请检查网络后重试，或手动执行 pip install edge-tts")
        input("按回车退出…")
        sys.exit(1)

PORT = 5299
CACHE = {}
CACHE_ORDER = []
VOICES = None
RATE_RE = re.compile(r"^[+-]\d{1,3}%$")


def synth(text, voice, rate):
    async def run():
        com = edge_tts.Communicate(text, voice, rate=rate)
        chunks = [c["data"] async for c in com.stream() if c["type"] == "audio"]
        return b"".join(chunks)
    try:
        return asyncio.run(run())
    except Exception:
        # 服务端偶发 503/403，重试一次通常即恢复
        return asyncio.run(run())


def voices():
    global VOICES
    if VOICES is None:
        raw = asyncio.run(edge_tts.list_voices())
        VOICES = [
            {"name": v["ShortName"], "locale": v["Locale"], "gender": v["Gender"]}
            for v in raw
            if v["Locale"].startswith(("en-", "zh-"))
        ]
    return VOICES


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == "/ping":
            return self._json({"ok": True, "engine": "edge-tts", "version": edge_tts.__version__})
        if u.path == "/voices":
            try:
                return self._json(voices())
            except Exception as e:
                return self._json({"error": str(e)}, 502)
        if u.path == "/tts":
            text = (q.get("text") or [""])[0].strip()
            voice = (q.get("voice") or ["en-US-AriaNeural"])[0].strip()
            rate = (q.get("rate") or ["+0%"])[0].strip()
            if not text:
                return self._json({"error": "empty text"}, 400)
            if len(text) > 600:
                return self._json({"error": "text too long"}, 400)
            if not RATE_RE.match(rate):
                return self._json({"error": "bad rate"}, 400)
            if not re.match(r"^[a-zA-Z]{2,3}-[a-zA-Z]{2,4}-[A-Za-z0-9]+$", voice):
                return self._json({"error": "bad voice"}, 400)
            key = (text, voice, rate)
            data = CACHE.get(key)
            if data is None:
                try:
                    data = synth(text, voice, rate)
                except Exception as e:
                    return self._json({"error": str(e)}, 502)
                if not data:
                    return self._json({"error": "no audio"}, 502)
                CACHE[key] = data
                CACHE_ORDER.append(key)
                while len(CACHE_ORDER) > 300:
                    CACHE.pop(CACHE_ORDER.pop(0), None)
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self._json({"error": "not found"}, 404)

    def log_message(self, fmt, *args):
        print("[tts] " + (fmt % args))


if __name__ == "__main__":
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        print("端口 %d 已被占用：桥接可能已经在运行，无需重复启动。" % PORT)
        input("按回车退出…")
        sys.exit(0)
    print("edge-tts 朗读服务已启动: http://127.0.0.1:%d" % PORT)
    print("回到网页点朗读即可自动使用 edge-tts；关闭本窗口即停止。")
    server.serve_forever()