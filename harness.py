import http.server
import socketserver
import json
import urllib.parse
import socket
import subprocess
import time
import threading
import urllib.request
import os

PORT = 8080
LLAMA_PORT = 8081
LLAMA_BIN = "/usr/local/bin/llama-server"
MODELS_DIR = "/home/fox/models"

DATA_STORE = {
    "active_model": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
    "functions": [
        {"category": "coding", "description": "Flutter, Dart, Python, and C++ code generation", "assigned_model": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf", "status": "Ready in VRAM"},
        {"category": "search", "description": "Fast local file parsing, indexing, and text extraction", "assigned_model": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf", "status": "Ready in VRAM"}
    ],
    "models": [
        {"filename": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf", "repo": "meta-llama/Llama-3.1-8B-Instruct-GGUF", "size_gb": 4.9, "vram_fit": "100% GPU VRAM (0 GB Spillover)"},
        {"filename": "SmolLM2-1.7B-Instruct.gguf", "repo": "HuggingFaceTB/SmolLM2-1.7B-Instruct", "size_gb": 1.0, "vram_fit": "100% GPU VRAM"},
        {"filename": "Qwen3-8B-Q4_K_M.gguf", "repo": "Qwen/Qwen3-8B-GGUF", "size_gb": 4.9, "vram_fit": "100% GPU VRAM"}
    ]
}

swap_lock = threading.Lock()

def wait_for_slots_idle(timeout=30):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{LLAMA_PORT}/slots")
            with urllib.request.urlopen(req, timeout=1) as resp:
                if resp.status == 200:
                    slots = json.loads(resp.read().decode("utf-8"))
                    busy = any(slot.get("state", 0) != 0 for slot in slots)
                    if not busy:
                        print("[Switchboard] Active generation batch completed. Station is clear.")
                        return True
        except Exception:
            return True
        time.sleep(1)
    print("[Switchboard] Swap timeout reached; proceeding with forced transition.")
    return True

class HarnessHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/functions":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(DATA_STORE["functions"]).encode("utf-8"))
            return
        if parsed.path == "/api/models":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(DATA_STORE["models"]).encode("utf-8"))
            return

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/select":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode("utf-8"))
                target_model = payload.get("model")
                
                with swap_lock:
                    print(f"[Switchboard] Requested switch to {target_model}. Checking active batch status...")
                    wait_for_slots_idle()

                    DATA_STORE["active_model"] = target_model
                    print(f"[Switchboard] Terminating stale llama-server...")
                    subprocess.run(["pkill", "-f", "llama-server"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(1)

                    model_path = os.path.join(MODELS_DIR, target_model)
                    cmd = [LLAMA_BIN, "-m", model_path, "--n-gpu-layers", "99", "--port", str(LLAMA_PORT), "--host", "127.0.0.1"]
                    print(f"[Switchboard] Launching: " + " ".join(cmd))
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                response = {"status": "success", "active_model": target_model, "message": f"Spawned {target_model} on port {LLAMA_PORT}"}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    with ReusableTCPServer(("127.0.0.1", PORT), HarnessHandler) as httpd:
        print(f"[Harness Active] Switchboard listening at http://127.0.0.1:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Harness stopped.")
