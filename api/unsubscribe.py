from http.server import BaseHTTPRequestHandler
import hmac
import hashlib
import os
import urllib.request
import urllib.parse
import json


def make_token(email: str, secret: str) -> str:
    return hmac.new(secret.encode(), email.lower().encode(), hashlib.sha256).hexdigest()


SITE_URL = "https://tools.gdprcheck.bg"

SUCCESS_HTML = """<!DOCTYPE html>
<html lang="bg"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Отписан — ОП + Фондове БГ</title>
<style>
  body{{font-family:'Segoe UI',Arial,sans-serif;background:#f8fafc;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
  .box{{background:white;border-radius:12px;padding:48px 40px;max-width:440px;text-align:center;box-shadow:0 4px 24px rgba(0,0,0,0.08)}}
  .icon{{font-size:48px;margin-bottom:16px}}
  h1{{font-size:22px;color:#1e293b;margin:0 0 12px}}
  p{{color:#64748b;line-height:1.6;margin:0 0 24px}}
  a{{display:inline-block;padding:10px 24px;background:#2563eb;color:white;border-radius:8px;text-decoration:none;font-weight:600;font-size:15px}}
</style></head><body>
<div class="box">
  <div class="icon">✅</div>
  <h1>Успешно отписан</h1>
  <p>Имейл адресът <b>{email}</b> беше премахнат.<br>Повече няма да получаваш alerts от нас.</p>
  <a href="{site_url}">← Обратно към сайта</a>
</div>
</body></html>"""

ERROR_HTML = """<!DOCTYPE html>
<html lang="bg"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Грешка — ОП + Фондове БГ</title>
<style>
  body{{font-family:'Segoe UI',Arial,sans-serif;background:#f8fafc;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
  .box{{background:white;border-radius:12px;padding:48px 40px;max-width:440px;text-align:center;box-shadow:0 4px 24px rgba(0,0,0,0.08)}}
  .icon{{font-size:48px;margin-bottom:16px}}
  h1{{font-size:22px;color:#1e293b;margin:0 0 12px}}
  p{{color:#64748b;line-height:1.6;margin:0 0 24px}}
  a{{display:inline-block;padding:10px 24px;background:#2563eb;color:white;border-radius:8px;text-decoration:none;font-weight:600;font-size:15px}}
</style></head><body>
<div class="box">
  <div class="icon">❌</div>
  <h1>Невалиден линк</h1>
  <p>{message}</p>
  <a href="{site_url}">← Обратно към сайта</a>
</div>
</body></html>"""


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        email = params.get('email', [''])[0].lower().strip()
        token = params.get('token', [''])[0].strip()

        secret = os.getenv('SUPABASE_SECRET_KEY', '')
        supabase_url = os.getenv('SUPABASE_URL', '')

        if not email or not token:
            self._html(400, ERROR_HTML.format(
                message='Линкът е непълен. Моля пиши на <a href="mailto:alexbgodd@gmail.com">alexbgodd@gmail.com</a> за отписване.',
                site_url=SITE_URL
            ))
            return

        expected = make_token(email, secret)
        if not hmac.compare_digest(expected, token):
            self._html(403, ERROR_HTML.format(
                message='Токенът е невалиден или линкът е изтекъл.',
                site_url=SITE_URL
            ))
            return

        # Изтриване от Supabase
        try:
            encoded_email = urllib.parse.quote(email)
            req = urllib.request.Request(
                f"{supabase_url}/rest/v1/registrations?email=eq.{encoded_email}",
                method='DELETE',
                headers={
                    'apikey': secret,
                    'Authorization': f'Bearer {secret}',
                    'Prefer': 'return=minimal'
                }
            )
            urllib.request.urlopen(req)
            self._html(200, SUCCESS_HTML.format(email=email, site_url=SITE_URL))
        except Exception as e:
            self._html(500, ERROR_HTML.format(
                message=f'Техническа грешка. Пиши на <a href="mailto:alexbgodd@gmail.com">alexbgodd@gmail.com</a>.',
                site_url=SITE_URL
            ))

    def _html(self, status, body):
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body.encode('utf-8'))

    def log_message(self, format, *args):
        pass  # тихо логване
