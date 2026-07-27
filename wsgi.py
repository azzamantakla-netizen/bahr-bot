import threading
import os
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Web server is active, bot is running!")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

if __name__ == "__main__":
    # تشغيل خادم ويب في الخلفية لإرضاء Render
    threading.Thread(target=run_web_server, daemon=True).start()

    # تشغيل ملف البوت الأصلي الخاص بك كاملاً
    print("Launching original bot.py...")
    subprocess.run(["python", "bot.py"])

