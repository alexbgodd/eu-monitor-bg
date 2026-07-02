from http.server import BaseHTTPRequestHandler
import json
import os
import re
import smtplib
import hmac
import hashlib
import urllib.parse
from email.mime.text import MIMEText

SMTP_HOST = os.getenv("SMTP_HOST", "smtp-relay.brevo.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_LOGIN = os.getenv("SMTP_LOGIN")
SMTP_KEY = os.getenv("SMTP_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM", "info@gdprcheck.bg")
NOTIFY_TO = os.getenv("NOTIFY_TO", "info@gdprcheck.bg")
SITE_API_KEY = os.getenv("SITE_API_KEY", "")
SITE_URL = "https://tools.gdprcheck.bg"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def unsub_url(email: str) -> str:
    secret = os.getenv('SUPABASE_SECRET_KEY', 'fallback-secret')
    token = hmac.new(secret.encode(), email.lower().encode(), hashlib.sha256).hexdigest()
    return f"{SITE_URL}/unsubscribe?email={urllib.parse.quote(email)}&token={token}"


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        # Защита от директни/чужди извиквания на endpoint-a
        if not SITE_API_KEY or self.headers.get('X-Site-Key') != SITE_API_KEY:
            self._respond(403, {"ok": False, "error": "forbidden"})
            return

        try:
            data = json.loads(body.decode('utf-8'))
            name      = data.get('name', '').strip()
            email     = data.get('email', '').strip()
            org_type  = data.get('org_type', '').strip() or '—'
            interests = data.get('interests', '')
            if isinstance(interests, list):
                interests = ', '.join(interests)

            if not email or not EMAIL_RE.match(email):
                self._respond(400, {"ok": False, "error": "invalid email"})
                return

            self._send_notification(name, email, org_type, interests)
            self._send_welcome(name, email)
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

    def _send_welcome(self, name, email):
        if not SMTP_LOGIN or not SMTP_KEY or not email:
            return

        body = (
            f"Здравей, {name or 'приятел'}!\n\n"
            f"Регистрацията ти в ОП + Фондове БГ е успешна.\n"
            f"От сега нататък ще получаваш имейл известия на този адрес, когато се появи "
            f"нова обществена поръчка или EU програма, съответстваща на избраните от теб интереси.\n\n"
            f"Разгледай всички активни програми: {SITE_URL}/programs\n\n"
            f"Ако искаш да се отпишеш по всяко време: {unsub_url(email)}\n"
        )
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = "Добре дошъл в ОП + Фондове БГ — регистрацията е успешна"
        msg['From'] = f"EU Monitor BG <{EMAIL_FROM}>"
        msg['To'] = email

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=8) as server:
            server.starttls()
            server.login(SMTP_LOGIN, SMTP_KEY)
            server.sendmail(EMAIL_FROM, email, msg.as_string())

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
