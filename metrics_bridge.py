import http.server
import socketserver
import json
from store import MultiModelStore

PORT = 5002
store = MultiModelStore()

class MultiModelHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ["/api/models", "/api/metrics", "/api/hardware"]:
            table_map = {
                "/api/models": "model_registry",
                "/api/metrics": "performance_metrics",
                "/api/hardware": "hardware_logs"
            }
            table = table_map[self.path]
            data = store.get_all(table)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    with socketserver.TCPServer(("127.0.0.1", PORT), MultiModelHandler) as httpd:
        print(f"[Multi-Model Bridge Active] Listening on http://127.0.0.1:{PORT}")
        httpd.serve_forever()
