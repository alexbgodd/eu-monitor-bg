from http.server import BaseHTTPRequestHandler
from datetime import datetime, timezone
import json
import os
import re
import smtplib
import hmac
import hashlib
import urllib.parse
import urllib.request
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

# Приветствие се праща само за запис, създаден преди малко. Ключът X-Site-Key
# е в публичния script.js, така че сам по себе си не пази от нищо: без тази
# проверка всеки можеше да праща писма от info@ до произволен адрес с
# произволен текст в името.
MAX_AGE_MINUTES = 15


def unsub_url(email: str) -> str:
    secret = os.getenv('SUPABASE_SECRET_KEY', 'fallback-secret')
    token = hmac.new(secret.encode(), email.lower().encode(), hashlib.sha256).hexdigest()
    return f"{SITE_URL}/unsubscribe?email={urllib.parse.quote(email)}&token={token}"


def clean_name(name):
    """
    Името идва от формата и отива в писмо от нашия домейн. Махаме всичко,
    което може да го превърне в реклама или фишинг: линкове, имейли,
    контролни символи, прекалена дължина.
    """
    s = " ".join(str(name or "").split())          # и нови редове, и табове
    s = "".join(ch for ch in s if ch.isprintable())
    low = s.lower()
    if (not s or len(s) > 60 or "://" in low or "www." in low or "@" in low
            or re.search(r"\b[a-z0-9-]+\.(bg|com|net|org|eu|info|io|ru|xyz|top|link)\b", low)
            or re.search(r"[<>]", s)):
        return ""
    return s


def find_registration(email):
    """
    Връща записа от Supabase за точно този адрес или None.
    Не зависи от имената на колоните (select=*), защото CLAUDE.md веднъж
    вече сбърка схемата.
    """
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SECRET_KEY", "")
    if not url or not key:
        return None
    q = urllib.parse.quote(email, safe="")
    req = urllib.request.Request(
        f"{url}/rest/v1/registrations?select=*&email=eq.{q}&limit=1",
        headers={"apikey": key, "Authorization": f"Bearer {key}",
                 "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        rows = json.loads(r.read().decode("utf-8") or "[]")
    return rows[0] if rows else None


def is_recent(row, now=None):
    """
    True ако записът е създаден преди по-малко от MAX_AGE_MINUTES.
    Ако няма created_at или не се чете, пускаме (само проверката за време —
    проверката, че адресът изобщо е в базата, остава).
    """
    raw = str(row.get("created_at") or "").strip()
    if not raw:
        return True
    try:
        created = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return True
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    age_min = (now - created).total_seconds() / 60
    return -5 <= age_min <= MAX_AGE_MINUTES


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0) or 0)
        body = self.rfile.read(min(content_length, 20000))

        # Защита от директни/чужди извиквания на endpoint-a
        if not SITE_API_KEY or self.headers.get('X-Site-Key') != SITE_API_KEY:
            self._respond(403, {"ok": False, "error": "forbidden"})
            return

        try:
            data = json.loads(body.decode('utf-8'))
            email = str(data.get('email', '')).strip()

            if not email or len(email) > 254 or not EMAIL_RE.match(email):
                self._respond(400, {"ok": False, "error": "invalid email"})
                return

            # Писмо само за адрес, който наистина току-що е записан в базата.
            # Данните за писмото се вземат от базата, не от заявката.
            row = find_registration(email)
            if not row or not is_recent(row):
                self._respond(200, {"ok": False})
                return

            name = clean_name(row.get('name'))
            org_type = str(row.get('org_type') or '').strip() or '—'
            interests = row.get('interests') or ''
            if isinstance(interests, list):
                interests = ', '.join(interests)

            self._send_notification(name, email, org_type, interests)
            self._send_welcome(name, email)
            self._respond(200, {"ok": True})
        except Exception:
            # Никога не чупим регистрацията заради неуспешен имейл.
            # Без текста на грешката: той може да издаде вътрешни подробности.
            self._respond(200, {"ok": False})

    def _send_notification(self, name, email, org_type, interests):
        if not SMTP_LOGIN or not SMTP_KEY:
            return

        body = (
            f"Нова регистрация в ОП + Фондове БГ:\n\n"
            f"Име: {name or '(празно или отхвърлено)'}\n"
            f"Имейл: {email}\n"
            f"Организация: {org_type}\n"
            f"Интереси: {interests}\n"
        )
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = "Нова регистрация в ОП + Фондове БГ"
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
            f"Ако не си се регистрирал ти или искаш да се отпишеш: {unsub_url(email)}\n"
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
        self.send_header('Access-Control-Allow-Origin', SITE_URL)
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Site-Key')

    def log_message(self, format, *args):
        pass
