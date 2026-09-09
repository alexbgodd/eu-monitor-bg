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

SMTP_HOST = os.getenv("SMTP_HOST", "smtp-relay.brevo.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_LOGIN = os.getenv("SMTP_LOGIN")
SMTP_KEY = os.getenv("SMTP_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM", "info@gdprcheck.bg")
SITE_NAME = "EU Monitor BG"
SITE_URL  = "https://tools.gdprcheck.bg"


def make_unsub_token(email: str) -> str:
    secret = os.getenv('SUPABASE_SECRET_KEY', 'fallback-secret')
    return hmac.new(secret.encode(), email.lower().encode(), hashlib.sha256).hexdigest()


def unsub_url(email: str) -> str:
    token = make_unsub_token(email)
    return f"{SITE_URL}/unsubscribe?email={urllib.parse.quote(email)}&token={token}"


# ── Форматиране на новите полета от ЦАИС ──────────────────────────────────

NUTS_LABELS = {
    "BG": "Цялата страна",
    "BG31": "Северозападен", "BG32": "Северен централен", "BG33": "Североизточен",
    "BG34": "Югоизточен", "BG41": "Югозападен", "BG42": "Южен централен",
    "BG311": "Видин", "BG312": "Монтана", "BG313": "Враца", "BG314": "Плевен",
    "BG315": "Ловеч", "BG321": "Велико Търново", "BG322": "Габрово",
    "BG323": "Русе", "BG324": "Разград", "BG325": "Силистра",
    "BG331": "Варна", "BG332": "Добрич", "BG333": "Шумен", "BG334": "Търговище",
    "BG341": "Бургас", "BG342": "Сливен", "BG343": "Ямбол", "BG344": "Стара Загора",
    "BG411": "София (столица)", "BG412": "София област", "BG413": "Благоевград",
    "BG414": "Перник", "BG415": "Кюстендил", "BG421": "Пловдив",
    "BG422": "Хасково", "BG423": "Пазарджик", "BG424": "Смолян", "BG425": "Кърджали",
}


def esc(s):
    """Екранира текст от външни регистри, преди да влезе в HTML на имейла."""
    return (str("" if s is None else s)
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def fmt_value(v):
    if not isinstance(v, (int, float)) or v <= 0:
        return ""
    if v >= 999500:
        return f"{v / 1e6:.1f}".replace(".", ",").rstrip("0").rstrip(",") + " млн. €"
    if v >= 999.5:
        return f"{round(v / 1000):,}".replace(",", " ") + " хил. €"
    return f"{round(v):,}".replace(",", " ") + " €"


def region_label(nuts):
    return NUTS_LABELS.get(str(nuts or ""), str(nuts or ""))


def days_left(deadline):
    if not deadline:
        return None
    from datetime import date
    try:
        d = date.fromisoformat(str(deadline)[:10])
    except (ValueError, TypeError):
        return None
    return (d - date.today()).days


def deadline_phrase(p):
    """'до 12.09.2026 (още 3 дни)' — срокът е причината имейлът да се отвори."""
    dl = p.get("deadline")
    if not dl:
        return ""
    d = days_left(dl)
    if d is None:
        return str(dl)
    if d < 0:
        return f"{dl} — изтекъл"
    if d == 0:
        return f"{dl} — ИЗТИЧА ДНЕС"
    if d == 1:
        return f"{dl} — остава 1 ден"
    return f"{dl} — остават {d} дни"

def send_email(to_email, to_name, programs):
    if not SMTP_LOGIN or not SMTP_KEY:
        print("ГРЕШКА: Няма SMTP_LOGIN / SMTP_KEY в .env файла!")
        return False

    # Темата казва колко изтичат скоро — това е информацията, която решава
    # дали имейлът ще бъде отворен днес или „после“.
    # ВНИМАНИЕ: `days_left(...) or 99` е грешно — 0 дни (изтича днес) е falsy
    # и точно най-спешните изпадаха от бройката.
    def _is_urgent(p):
        dl = days_left(p.get("deadline"))
        return dl is not None and 0 <= dl <= 7
    urgent = sum(1 for p in programs if _is_urgent(p))
    base = f"{len(programs)} нов{'а програма' if len(programs) == 1 else 'и програми'}"
    subject = (f"[{SITE_NAME}] {base} · {urgent} изтичат до 7 дни"
               if urgent else f"[{SITE_NAME}] {base} за теб")

    CATEGORY_LABELS = {
        "общи": "🌐 Общи", "бизнес": "💼 Бизнес", "земеделие": "🌾 Земеделие",
        "култура": "🎭 Култура", "социални": "👥 Социални",
        "здравеопазване": "🏥 Здравеопазване", "образование": "📚 Образование",
        "туризъм": "🏨 Туризъм", "екология": "🌿 Екология", "ит": "💻 ИТ",
        "търгове": "🏛️ Поръчки", "инфраструктура": "🏗️ Инфраструктура", "общини": "🏘️ Общини",
    }

    # Групираме по категория (най-многобройните секции първи, редът вътре се пази)
    grouped = {}
    for p in programs:
        grouped.setdefault(p.get("category", "общи"), []).append(p)
    ordered = sorted(grouped.items(), key=lambda kv: -len(kv[1]))

    # HTML съдържание — секция за всяка категория
    programs_html = ""
    for category, items in ordered:
        label = CATEGORY_LABELS.get(category, category)
        programs_html += f"""
        <h3 style="font-size:15px;color:#1d4ed8;margin:24px 0 4px;border-bottom:2px solid #e5e7eb;padding-bottom:6px;">
            {label} <span style="color:#94a3b8;font-weight:normal;">({len(items)})</span>
        </h3>
        """
        for p in items:
            # Линкът сочи към нашата детайлна страница (/notice), не директно навън —
            # там има copy бутон, Google търсене и работещ път към източника.
            if p.get("id"):
                notice_url = f"{SITE_URL}/notice?id={urllib.parse.quote(str(p['id']))}"
            else:
                notice_url = p.get("url", "")
            url_line = f'<a href="{notice_url}">{notice_url}</a>' if notice_url else "Няма линк"

            # Срок — оцветен по спешност, защото това е причината да се отвори имейлът
            dl_phrase = deadline_phrase(p)
            d = days_left(p.get("deadline"))
            dl_color = "#b91c1c" if (d is not None and d <= 3) else \
                       "#b45309" if (d is not None and d <= 10) else "#9a3412"
            deadline_line = (f'<b style="color:{dl_color};">⏳ Краен срок: {esc(dl_phrase)}</b><br>'
                             if dl_phrase else "")

            # Стойност, регион, обособени позиции, ЕС програма — в един ред
            facts = []
            if fmt_value(p.get("value")):
                facts.append(f'<b>{esc(fmt_value(p["value"]))}</b>')
            if p.get("nuts"):
                facts.append(esc(region_label(p["nuts"])))
            if isinstance(p.get("lots"), int) and p["lots"] > 1:
                facts.append(f'{p["lots"]} обособени позиции')
            if p.get("eu_funded"):
                facts.append("ЕС финансиране")
            facts_line = (f'<span style="color:#334155;">{" · ".join(facts)}</span><br>'
                          if facts else "")

            border = dl_color if (d is not None and d <= 3) else "#2563eb"
            programs_html += f"""
        <div style="border-left:4px solid {border};padding:12px 16px;margin:12px 0;background:#f8faff;">
            <b style="font-size:16px;">{esc(p['title'])}</b><br>
            {deadline_line}
            {facts_line}
            <span style="color:#555;">Източник: {esc(p['source'])}</span><br>
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
               {'която може' if len(programs) == 1 else 'които може'} да те интересува{'' if len(programs) == 1 else 'т'}:</p>
            {f'<p style="color:#b91c1c;"><b>{urgent}</b> от тях изтичат до 7 дни.</p>' if urgent else ''}
            {programs_html}
            <div style="background:#f8faff;border:1px solid #dbeafe;border-radius:8px;padding:14px 16px;margin:24px 0;font-size:14px;color:#1e40af;">
                Ако това ти е полезно, препрати имейла на колега — регистрацията е безплатна:
                <a href="{SITE_URL}" style="color:#1d4ed8;">{SITE_URL}</a>
            </div>
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

    # Текстова версия: имейл само с HTML получава по-висок спам-рейтинг.
    # При проблема с доставяемостта към abv.bg това е първото, което помага.
    text_lines = [f"Здравей, {to_name}!", "",
                  f"{len(programs)} нови възможности за теб:", ""]
    for category, items in ordered:
        text_lines.append(f"--- {CATEGORY_LABELS.get(category, category)} ---")
        for p in items:
            text_lines.append(f"* {p.get('title', '')}")
            if deadline_phrase(p):
                text_lines.append(f"  Краен срок: {deadline_phrase(p)}")
            facts = [x for x in (fmt_value(p.get("value")),
                                 region_label(p["nuts"]) if p.get("nuts") else "",
                                 f"{p['lots']} обособени позиции"
                                 if isinstance(p.get("lots"), int) and p["lots"] > 1 else "",
                                 "ЕС финансиране" if p.get("eu_funded") else "") if x]
            if facts:
                text_lines.append("  " + " · ".join(facts))
            text_lines.append(f"  Източник: {p.get('source', '')}")
            if p.get("id"):
                text_lines.append(
                    f"  {SITE_URL}/notice?id={urllib.parse.quote(str(p['id']))}")
            elif p.get("url"):
                text_lines.append(f"  {p['url']}")
            text_lines.append("")
    text_lines += ["", f"Получаваш този имейл, защото се регистрира на {SITE_URL}",
                   f"Отписване: {unsub_url(to_email)}"]
    text_body = "\n".join(text_lines)

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"{SITE_NAME} <{EMAIL_FROM}>"
    msg['To'] = to_email
    # Gmail и Yahoo изискват one-click отписване от масовите податели; без тези
    # хедъри доставяемостта пада и услугата спира тихо да работи.
    msg['List-Unsubscribe'] = f"<{unsub_url(to_email)}>"
    msg['List-Unsubscribe-Post'] = "List-Unsubscribe=One-Click"
    # Редът има значение: последната прикачена част е предпочитаната.
    msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
    msg.attach(MIMEText(html, 'html', 'utf-8'))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_LOGIN, SMTP_KEY)
            server.sendmail(EMAIL_FROM, to_email, msg.as_string())
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
    send_email("alexbgodd@gmail.com", "Alex", test_programs)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_email()
    elif len(sys.argv) > 1:
        # Защита: "python send_alerts.py email@x.bg" НЕ праща до конкретен имейл —
        # за това е blast_existing.py. Без този guard аргументът се игнорираше
        # и скриптът пращаше до ВСИЧКИ абонати (инцидент 31.07.2026).
        print("Непознат аргумент.")
        print("  Тест имейл:            python send_alerts.py test")
        print("  До конкретен абонат:   python blast_existing.py email@x.bg")
        print("  До всички (с дедупл.): python blast_existing.py")
    else:
        run_alerts()
