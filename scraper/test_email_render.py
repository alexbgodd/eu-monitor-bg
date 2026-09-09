"""
Офлайн тест на имейл шаблона и на избора какво влиза в имейла.

НЕ изпраща нищо и не пипа мрежата — само проверява форматирането и подбора.
Записва и HTML предварителен преглед в scraper/testdata/preview_email.html,
който можеш да отвориш в браузър, за да видиш как ще изглежда писмото.

    python scraper/test_email_render.py
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from send_alerts import (                          # noqa: E402
    fmt_value, region_label, days_left, deadline_phrase, esc,
)
from blast_existing import select_for_email        # noqa: E402

_failures = []


def check(label, got, expected):
    ok = got == expected
    print(f"  {'✓' if ok else '✗'} {label}: {got!r}"
          + ("" if ok else f"  (очаквано: {expected!r})"))
    if not ok:
        _failures.append(label)


def d(offset):
    return (date.today() + timedelta(days=offset)).isoformat()


def sample():
    """Смес, каквато реално се получава: спешни поръчки, скъпи, и фондове без срок."""
    out = []
    for i, off in enumerate([0, 1, 2, 3, 5, 7, 9, 12, 15, 20, 25, 30, 35, 40, 45, 50]):
        out.append({
            "id": f"ocds-e82gsb-{600000 + i}", "type": "tender",
            "title": f"Поръчка {i}", "source": "ЦАИС ЕОП — Обявления",
            "category": "инфраструктура", "deadline": d(off),
            "value": 50000 * (i + 1), "nuts": "BG411",
            "found_at": d(-3), "lots": 3 if i == 2 else None,
            "eu_funded": i == 1,
        })
    for i in range(14):
        out.append({
            "id": f"BG16RFPR-{i}", "type": "fund",
            "title": f"Фонд {i}", "source": "ИСУН 2020 — Отворени процедури",
            "category": "бизнес", "deadline": "", "found_at": d(-i),
        })
    return out


def main():
    print("\n[1] Форматиране на стойност")
    check("999",       fmt_value(999),       "999 €")
    check("50 000",    fmt_value(50000),     "50 хил. €")
    check("999 999",   fmt_value(999999),    "1 млн. €")
    check("5 800 000", fmt_value(5800000),   "5,8 млн. €")
    check("нула",      fmt_value(0),         "")
    check("None",      fmt_value(None),      "")
    check("текст",     fmt_value("х"),       "")

    print("\n[2] Регион и срок")
    check("BG411",        region_label("BG411"), "София (столица)")
    check("непознат код", region_label("BG999"), "BG999")
    check("празно",       region_label(None),    "")
    check("днес",     deadline_phrase({"deadline": d(0)}), f"{d(0)} — ИЗТИЧА ДНЕС")
    check("утре",     deadline_phrase({"deadline": d(1)}), f"{d(1)} — остава 1 ден")
    check("след 5",   deadline_phrase({"deadline": d(5)}), f"{d(5)} — остават 5 дни")
    check("изтекъл",  deadline_phrase({"deadline": d(-2)}), f"{d(-2)} — изтекъл")
    check("без срок", deadline_phrase({"deadline": ""}), "")
    check("счупена дата", days_left("не е дата"), None)

    print("\n[3] Екраниране")
    check("HTML в заглавие", esc('<b>&"x"'), "&lt;b&gt;&amp;&quot;x&quot;")
    check("None", esc(None), "")

    print("\n[4] Подбор: спешните първи, но фондовете не се изместват")
    chosen = select_for_email(sample())
    check("точно 20", len(chosen), 20)
    n_funds = sum(1 for p in chosen if p["type"] == "fund")
    n_tend = sum(1 for p in chosen if p["type"] == "tender")
    check("фондове в имейла", n_funds, 8)
    check("поръчки в имейла", n_tend, 12)
    check("общо = лимита", n_funds + n_tend, 20)
    check("първата изтича най-скоро", chosen[0]["deadline"], d(0))
    check("фондовете са накрая", chosen[-1]["type"], "fund")

    print("\n[5] Гранични случаи на подбора")
    only_funds = [p for p in sample() if p["type"] == "fund"]
    check("само фондове → пълни се докрай", len(select_for_email(only_funds)), 14)
    only_tenders = [p for p in sample() if p["type"] == "tender"]
    check("само поръчки → до лимита", len(select_for_email(only_tenders)), 16)
    check("празен вход", select_for_email([]), [])
    check("под лимита", len(select_for_email(sample()[:3])), 3)

    print("\n[6] Сглобяване на писмото (без изпращане)")
    import send_alerts
    captured = {}

    class FakeSMTP:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self): pass
        def login(self, *a): pass
        def sendmail(self, frm, to, raw): captured["raw"] = raw

    send_alerts.SMTP_LOGIN = send_alerts.SMTP_KEY = "test"
    real = send_alerts.smtplib.SMTP
    send_alerts.smtplib.SMTP = FakeSMTP
    try:
        ok = send_alerts.send_email("test@example.com", "Алекс", chosen)
    finally:
        send_alerts.smtplib.SMTP = real

    raw = captured.get("raw", "")
    import email as email_mod
    check("изпращането върна успех", ok, True)
    check("има текстова част", "text/plain" in raw, True)
    check("има HTML част", "text/html" in raw, True)
    check("има List-Unsubscribe", "List-Unsubscribe:" in raw, True)
    check("има one-click", "One-Click" in raw, True)
    import email.header
    subj = str(email.header.make_header(
        email.header.decode_header(email_mod.message_from_string(raw)["Subject"])))
    check("темата брои спешните", "изтичат до 7 дни" in subj, True)
    check("темата брои правилно (вкл. изтичащите днес)", subj.split("·")[1].strip(),
          "6 изтичат до 7 дни")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "testdata", "preview_email.html")
    msg = email_mod.message_from_string(raw)
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            with open(out, "w", encoding="utf-8") as f:
                f.write(part.get_payload(decode=True).decode("utf-8"))
            print(f"\n  Предварителен преглед записан: {out}")
            break

    print()
    if _failures:
        print(f"ПАДНАЛИ ПРОВЕРКИ ({len(_failures)}): " + ", ".join(_failures))
        return 1
    print("Всички проверки минаха.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
