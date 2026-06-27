from http.server import BaseHTTPRequestHandler
import json
import os

USERS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'users.json')

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body.decode('utf-8'))
            name      = data.get('name', '').strip()
            email     = data.get('email', '').strip().lower()
            org_type  = data.get('org_type', '').strip()
            interests = data.get('interests', [])

            if not name or not email or not interests:
                self._respond(400, {"error": "Попълни всички полета."})
                return

            users = load_users()
            if any(u['email'] == email for u in users):
                self._respond(409, {"error": "Този имейл вече е регистриран."})
                return

            users.append({
                "name": name,
                "email": email,
                "org_type": org_type,
                "interests": interests
            })
            save_users(users)

            self._respond(200, {"message": f"Успешно! Ще получаваш alerts на {email}."})

        except Exception as e:
            self._respond(500, {"error": str(e)})

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _respond(self, status, data):
        self.send_response(status)
        self._cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
