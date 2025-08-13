#!/usr/bin/env python3
import http.server
import socketserver
import json
from urllib.parse import urlparse, parse_qs
import sys

class DebugHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        print("\n=== N8N DEBUG REQUEST ===")
        print(f"Method: {self.command}")
        print(f"Path: {self.path}")
        print(f"Headers:")
        for header, value in self.headers.items():
            print(f"  {header}: {value}")
        
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            print(f"Body length: {content_length}")
            print(f"Body (raw): {body}")
            print(f"Body (decoded): {body.decode('utf-8', errors='replace')}")
        else:
            print("Body: EMPTY")
        print("========================\n")
        
        # Send response
        response = {"status": "received", "body_length": content_length}
        response_json = json.dumps(response).encode('utf-8')
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_json)))
        self.end_headers()
        self.wfile.write(response_json)

if __name__ == "__main__":
    PORT = 8020
    with socketserver.TCPServer(("", PORT), DebugHTTPRequestHandler) as httpd:
        print(f"Debug server running on port {PORT}")
        print("Waiting for n8n requests...")
        httpd.serve_forever()