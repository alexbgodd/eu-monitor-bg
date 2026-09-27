from http.server import BaseHTTPRequestHandler
import hmac
import hashlib
import html
import os
import urllib.request
import urllib.parse
import json

# Отписване.
#
# GET  /unsubscribe?email=..&token=..  → страница с бутон „Потвърди отписването“.
#      НЕ трие. Корпоративни и антивирусни скенери отварят линковете в писмата
#      сами (GET); ако GET трие, те отписват хора без те да са кликнали.
# POST /unsubscribe?email=..&token=..  → трие. Това прави бутонът на страницата,
#      както и бутонът „Отписване“ на Gmail/Yahoo (RFC 8058, List-Unsubscribe-Post).
#
# Изтриването не зависи от главни/малки букви: намира реалния запис в базата
# (Foo@Abv.bg) и трие точно него. Преди `.lower()` + `email=eq.` не намираше
# такива записи, а страницата казваше „успешно“.


def make_token(email: str, secret: str) -> str:
    return hmac.new(secret.encode(), email.lower().encode(), hashlib.sha256).hexdigest()


SITE_URL = "https://tools.gdprcheck.bg"

_STYLE = """<style>
  body{font-family:'Segoe UI',Arial,sans-serif;background:#f8fafc;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
  .box{background:white;border-radius:12px;padding:48px 40px;max-width:440px;text-align:center;box-shadow:0 4px 24px rgba(0,0,0,0.08)}
  .icon{font-size:48px;margin-bottom:16px}
  h1{font-size:22px;color:#1e293b;margin:0 0 12px}
  p{color:#64748b;line-height:1.6;margin:0 0 24px}
  a.btn,button{display:inline-block;padding:10px 24px;background:#2563eb;color:white;border:0;border-radius:8px;text-decoration:none;font-weight:600;font-size:15px;cursor:pointer;font-family:inherit}
  button.danger{background:#dc2626}
</style>"""


def _page(title, icon, heading, body_html, extra_html=""):
    return (
        '<!DOCTYPE html>\n<html lang="bg"><head>\n<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        '<meta name="robots" content="noindex">\n'
        f'<title>{title} — ОП + Фондове БГ</title>\n{_STYLE}</head><body>\n'
        f'<div class="box">\n  <div class="icon">{icon}</div>\n'
        f'  <h1>{heading}</h1>\n  <p>{body_html}</p>\n{extra_html}'
        f'  <p style="margin:24px 0 0"><a href="{SITE_URL}" style="color:#2563eb">← Обратно към сайта</a></p>\n'
        '</div>\n</body></html>'
    )


def confirm_page(email, token):
    action = "/unsubscribe?" + urllib.parse.urlencode({"email": email, "token": token})
    form = (f'  <form method="post" action="{html.escape(action)}">\n'
            '    <button type="submit" class="danger">Потвърди отписването</button>\n'
            '  </form>\n')
    return _page("Отписване", "✉️", "Отписване от известията",
                 f"Ще спрем писмата до <b>{html.escape(email)}</b>.", form)


def success_page(email, found):
    if found:
        body = (f"Имейл адресът <b>{html.escape(email)}</b> беше премахнат.<br>"
                "Повече няма да получаваш известия от нас.")
    else:
        body = (f"Адресът <b>{html.escape(email)}</b> вече не е в списъка ни.<br>"
                "Няма да получаваш известия от нас.")
    return _page("Отписан", "✅", "Успешно отписан", body)


def error_page(message_html):
    return _page("Грешка", "❌", "Невалиден линк", message_html)


def _supabase(method, path, supabase_url, secret):
    req = urllib.request.Request(
        f"{supabase_url}/rest/v1/{path}",
        method=method,
        headers={
            'apikey': secret,
            'Authorization': f'Bearer {secret}',
            'Accept': 'application/json',
            'Prefer': 'return=minimal',
        },
    )
    with urllib.request.urlopen(req, timeout=8) as r:
        body = r.read()
    return json.loads(body) if body else None


def delete_subscriber(email_lower, supabase_url, secret):
    """
    Трие всички записи, чийто имейл съвпада с email_lower без значение от
    главните букви. Връща колко записа са изтрити.

    Стъпка 1 търси кандидати с ilike (без значение от главните букви).
    ilike третира `_` и `%` като шаблони, затова може да върне и чужди
    адреси (a_b@x намира и axb@x). Стъпка 2 ги отсява с ТОЧНО сравнение
    в Python, а стъпка 3 трие по точната стойност от базата с eq.
    """
    q = urllib.parse.quote(email_lower, safe='')
    rows = _supabase('GET', f"registrations?select=email&email=ilike.{q}",
                     supabase_url, secret) or []
    exact = sorted({r.get('email') for r in rows
                    if isinstance(r.get('email'), str)
                    and r['email'].strip().lower() == email_lower})
    for stored in exact:
        _supabase('DELETE',
                  f"registrations?email=eq.{urllib.parse.quote(stored, safe='')}",
                  supabase_url, secret)
    return len(exact)


class handler(BaseHTTPRequestHandler):
    def _params(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        email = params.get('email', [''])[0].strip().lower()
        token = params.get('token', [''])[0].strip()
        return email, token

    def _check(self, email, token):
        """Връща None ако линкът е валиден, иначе (status, html)."""
        secret = os.getenv('SUPABASE_SECRET_KEY', '')
        if not email or not token or not secret:
            return 400, error_page(
                'Линкът е непълен. Моля пиши на <a href="mailto:info@gdprcheck.bg">'
                'info@gdprcheck.bg</a> за отписване.')
        if not hmac.compare_digest(make_token(email, secret), token):
            return 403, error_page('Токенът е невалиден или линкът е изтекъл.')
        return None

    def do_GET(self):
        email, token = self._params()
        bad = self._check(email, token)
        if bad:
            self._html(*bad)
            return
        self._html(200, confirm_page(email, token))

    def do_POST(self):
        # Тялото не ни трябва (Gmail праща "List-Unsubscribe=One-Click"),
        # но го прочитаме, за да не остане висящо в сокета.
        try:
            n = int(self.headers.get('Content-Length', 0) or 0)
            if 0 < n <= 10000:
                self.rfile.read(n)
        except Exception:
            pass

        email, token = self._params()
        bad = self._check(email, token)
        if bad:
            self._html(*bad)
            return

        try:
            found = delete_subscriber(email,
                                      os.getenv('SUPABASE_URL', ''),
                                      os.getenv('SUPABASE_SECRET_KEY', ''))
            self._html(200, success_page(email, found > 0))
        except Exception:
            self._html(500, error_page(
                'Техническа грешка. Пиши на <a href="mailto:info@gdprcheck.bg">'
                'info@gdprcheck.bg</a> и ще те отпишем ръчно.'))

    def _html(self, status, body):
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body.encode('utf-8'))

    def log_message(self, format, *args):
        pass  # без логване (в URL-а има имейл)
