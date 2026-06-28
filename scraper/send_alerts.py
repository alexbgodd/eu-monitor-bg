import smtplib
import json
import os
import sys
import hmac
import hashlib
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("EMAIL_USER")
SMTP_PASS = os.getenv("EMAIL_PASS")
SITE_NAME = "EU Monitor BG"
SITE_URL  = "https://tools.gdprcheck.bg"


def make_unsub_token(email: str) -> str:
    secret = os.getenv('SUPABASE_SECRET_KEY', 'fallback-secret')
    return hmac.new(secret.encode(), email.lower().encode(), hashlib.sha256).hexdigest()


def unsub_url(email: str) -> str:
    token = make_unsub_token(email)
    return f"{SITE_URL}/unsubscribe?email={urllib.parse.quote(email)}&token={token}"

def send_email(to_email, to_name, programs):
    if not SMTP_USER or not SMTP_PASS:
        print("ГРЕШКА: Няма EMAIL_USER / EMAIL_PASS в .env файла!")
        return False

    subject = f"[{SITE_NAME}] {len(programs)} нов{'а програма' if len(programs)==1 else 'и програми'} за теб"

    # HTML съдържание
    programs_html = ""
    for p in programs:
        url_line = f'<a href="{p["url"]}">{p["url"]}</a>' if p.get("url") else "Няма линк"
        deadline_line = f'<b>Краен срок:</b> {p["deadline"]}<br>' if p.get("deadline") else ""
        programs_html += f"""
        <div style="border-left:4px solid #2563eb;padding:12px 16px;margin:16px 0;background:#f8faff;">
            <b style="font-size:16px;">{p['title']}</b><br>
            <span style="color:#555;">Източник: {p['source']}</span><br>
            {deadline_line}
            {url_line}
        </div>
        """

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto;color:#222;">
        <div style="background:#2563eb;padding:20px;border-radius:8px 8px 0 0;">
            <a href="{SITE_URL}/programs" style="text-decoration:none;">
                <h2 style="color:white;margin:0;">🇪🇺 {SITE_NAME}</h2>
                <p style="color:#bfdbfe;margin:4px 0 0;">Мониторинг на EU финансиране</p>
            </a>
        </div>
        <div style="padding:24px;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 8px 8px;">
            <p>Здравей, <b>{to_name}</b>!</p>
            <p>Намерихме <b>{len(programs)} нов{'а програма' if len(programs)==1 else 'и програми'}</b>,
               която може да те интересува:</p>
            {programs_html}
            <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
            <p style="color:#888;font-size:13px;">
                Получаваш този имейл, защото се регистрира на
                <a href="{SITE_URL}" style="color:#6b7280;">{SITE_URL}</a><br><br>
                <a href="{unsub_url(to_email)}"
                   style="color:#ef4444;text-decoration:underline;font-size:12px;">
                   Отпиши се от alerts
                </a>
            </p>
        </div>
    </body></html>
    """

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"{SITE_NAME} <{SMTP_USER}>"
    msg['To'] = to_email
    msg.attach(MIMEText(html, 'html', 'utf-8'))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        print(f"  ✓ Изпратен на {to_email}")
        return True
    except Exception as e:
        print(f"  ✗ Грешка при {to_email}: {e}")
        return False

def run_alerts():
    # Импортираме тук за да избегнем circular import
    sys.path.insert(0, os.path.dirname(__file__))
    from scraper import scrape_all
    from matcher import get_matches

    print("=== EU Monitor — Изпращане на alerts ===\n")
    print("Стъпка 1: Scraping...")
    new_programs = scrape_all()

    if not new_programs:
        print("\nНяма нови програми — alerts не се изпращат.")
        return

    print(f"\nСтъпка 2: Matching ({len(new_programs)} нови програми)...")
    matches = get_matches(new_programs)

    if not matches:
        print("Няма съвпадения с регистрирани потребители.")
        return

    print(f"\nСтъпка 3: Изпращане на имейли...")
    sent = 0
    # Групираме програмите по потребител
    user_programs = {}
    for data in matches.values():
        for user in data['users']:
            email = user['email']
            if email not in user_programs:
                user_programs[email] = {"user": user, "programs": []}
            user_programs[email]["programs"].append(data['program'])

    for email, data in user_programs.items():
        if send_email(email, data['user'].get('name', 'потребител'), data['programs']):
            sent += 1

    print(f"\n✓ Готово! Изпратени: {sent} имейла.")

def test_email():
    """Тестов имейл с примерна програма"""
    test_programs = [{
        "title": "Тестова програма — EU Monitor работи!",
        "source": "EU Monitor BG",
        "url": "https://tools.gdprcheck.bg",
        "deadline": ""
    }]
    print("Изпращане на тестов имейл...")
    send_email(SMTP_USER, "Alex", test_programs)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_email()
    else:
        run_alerts()
