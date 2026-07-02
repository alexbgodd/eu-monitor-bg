from http.server import BaseHTTPRequestHandler
import json
import os
import smtplib
from email.mime.text import MIMEText

SMTP_HOST = os.getenv("SMTP_HOST", "smtp-relay.brevo.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_LOGIN = os.getenv("SMTP_LOGIN")
SMTP_KEY = os.getenv("SMTP_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM", "info@gdprcheck.bg")
NOTIFY_TO = os.getenv("NOTIFY_TO", "info@gdprcheck.bg")


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body.decode('utf-8'))
            name      = data.get('name', '').strip()
            email     = data.get('email', '').strip()
            org_type  = data.get('org_type', '').strip() or '—'
            interests = data.get('interests', '')
            if isinstance(interests, list):
                interests = ', '.join(interests)

            self._send_notification(name, email, org_type, interests)
            self._respond(200, {"ok": True})
        except Exception as e:
            # Никога не чупим регистрацията заради неуспешен имейл — само логваме
            self._respond(200, {"ok": False, "error": str(e)})

    def _send_notification(self, name, email, org_type, interests):
        if not SMTP_LOGIN or not SMTP_KEY:
            return

        body = (
            f"Нова регистрация в ОП + Фондове БГ:\n\n"
            f"Име: {name}\n"
            f"Имейл: {email}\n"
            f"Организация: {org_type}\n"
            f"Интереси: {interests}\n"
        )
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = f"Нова регистрация: {email}"
        msg['From'] = f"EU Monitor BG <{EMAIL_FROM}>"
        msg['To'] = NOTIFY_TO

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=8) as server:
            server.starttls()
            server.login(SMTP_LOGIN, SMTP_KEY)
            server.sendmail(EMAIL_FROM, NOTIFY_TO, msg.as_string())

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

    def log_message(self, format, *args):
        pass
