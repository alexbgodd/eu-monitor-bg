"""
Генерира статични SEO страници по институция/източник от data/programs.json.

За разлика от web/programs.html (SPA, JS зарежда данните в браузъра),
тези страници имат реалното съдържание директно в HTML-а — Google (и
всеки друг crawler) вижда заглавията на програмите без да изпълнява JS.

URL адресите са постоянни (напр. /institucii/tsais-eop) и НЕ се трият,
дори когато отделните програми/поръчки изтекат — само списъкът вътре
се обновява при следващо пускане на скрипта. Целта е стабилни, дълготрайни
страници, вместо хиляди бързоизтичащи URL адреса за всяка отделна поръчка.

Пуска се ръчно (или по-късно като стъпка в daily pipeline-а, след като
му се доверим): `python generate_seo_pages.py`
"""
import json
import os

BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
DATA_FILE = os.path.join(BASE_DIR, 'data', 'programs.json')
OUT_DIR = os.path.join(BASE_DIR, 'web', 'institucii')

# Slug + SEO мета за всеки известен източник (виж SOURCES в scraper.py).
# Пазим списъка тук ръчно вместо auto-slug от кирилица — по-предвидимо
# и по-стабилно за URL адресите с времето.
SOURCE_META = {
    "Министерство на иновациите и растежа": {
        "slug": "mig",
        "h1": "Финансиране от Министерство на иновациите и растежа",
        "desc": "Активни процедури и програми за финансиране от Министерството на иновациите и растежа на България.",
    },
    "ПНИИДИТ — Иновации и дигитализация": {
        "slug": "pniidit",
        "h1": "ПНИИДИТ — Иновации и дигитализация",
        "desc": "Отворени процедури по Програма за научни изследвания, иновации и дигитализация за интелигентна трансформация.",
    },
    "ИСУН 2020 — Отворени процедури": {
        "slug": "isun-2020",
        "h1": "ИСУН 2020 — Отворени EU процедури",
        "desc": "Пълен списък отворени процедури по Информационната система за управление и наблюдение на средствата от ЕС в България.",
    },
    "finansirane.org — Отворени процедури": {
        "slug": "finansirane-org",
        "h1": "finansirane.org — Отворени процедури",
        "desc": "Агрегирани отворени процедури за финансиране от finansirane.org.",
    },
    "ИПУП — Отворени покани": {
        "slug": "ippm",
        "h1": "ИПУП — Отворени покани за финансиране",
        "desc": "Отворени покани от Института за управление на програми и проекти.",
    },
    "ЕСФ България": {
        "slug": "esf-bg",
        "h1": "Европейски социален фонд — България",
        "desc": "Отворени процедури по Европейски социален фонд в България.",
    },
    "Еврофондове.бг": {
        "slug": "evrofondove-bg",
        "h1": "Еврофондове.бг — Отворени процедури",
        "desc": "Агрегирани отворени процедури за EU финансиране от Еврофондове.бг.",
    },
    "Министерство на земеделието": {
        "slug": "mzh",
        "h1": "Финансиране от Министерство на земеделието",
        "desc": "Активни мерки, подмерки и схеми за финансиране от Министерството на земеделието.",
    },
    "Министерство на културата": {
        "slug": "mc",
        "h1": "Финансиране от Министерство на културата",
        "desc": "Активни програми, конкурси и грантове от Министерството на културата.",
    },
    "Държавен фонд Земеделие": {
        "slug": "dfz",
        "h1": "Държавен фонд Земеделие — Отворени процедури",
        "desc": "Активни схеми, мерки и интервенции за подпомагане от Държавен фонд Земеделие.",
    },
    "ЦРЧР — Еразъм+ и младеж": {
        "slug": "hrdc-erasmus",
        "h1": "ЦРЧР — Еразъм+ и младежки програми",
        "desc": "Отворени покани по Еразъм+ и младежки мобилности от Центъра за развитие на човешките ресурси.",
    },
    "НПО портал — Финансиране": {
        "slug": "ngobg-finansirane",
        "h1": "НПО портал — Възможности за финансиране",
        "desc": "Отворени програми за финансиране на НПО и социални организации, агрегирани от НПО портал.",
    },
    "Национален фонд Култура": {
        "slug": "ncf",
        "h1": "Национален фонд Култура — Отворени конкурси",
        "desc": "Активни конкурси, грантове и стипендии от Национален фонд Култура.",
    },
    "ЦАИС ЕОП — Обявления": {
        "slug": "tsais-eop",
        "h1": "ЦАИС ЕОП — Обществени поръчки",
        "desc": "Активни обявления за обществени поръчки от Централизираната автоматизирана информационна система „Електронни обществени поръчки“ (ЦАИС ЕОП).",
    },
}

CATEGORY_LABELS = {
    "общи": "🌐 Общи", "бизнес": "💼 Бизнес", "земеделие": "🌾 Земеделие",
    "култура": "🎭 Култура", "социални": "👥 Социални", "образование": "📚 Образование",
    "туризъм": "🏨 Туризъм", "екология": "🌿 Екология", "ит": "💻 ИТ",
    "търгове": "🏛️ Поръчки", "инфраструктура": "🏗️ Инфраструктура", "общини": "🏘️ Общини",
}


def load_programs():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def card_html(p):
    is_tender = p.get('type') == 'tender'
    deadline_html = ''
    if p.get('deadline'):
        deadline_html = f'<span class="i-tag i-deadline">⏰ Краен срок: {p["deadline"]}</span>'
    else:
        deadline_html = '<span class="i-tag i-deadline-none">Краен срок: уточнява се</span>'
    cat = CATEGORY_LABELS.get(p.get('category', ''), p.get('category', ''))
    link = f'<a href="{p["url"]}" target="_blank" rel="noopener">Виж детайли →</a>' if p.get('url') else ''
    return f"""
        <article class="i-card">
            <h2>{p['title']}</h2>
            <div class="i-meta">
                <span class="i-tag">{cat}</span>
                {deadline_html}
            </div>
            {link}
        </article>"""


def render_page(source_name, meta, programs):
    cards = "\n".join(card_html(p) for p in programs) or \
        '<p class="i-empty">В момента няма активни записи от този източник — провери отново скоро.</p>'
    count = len(programs)
    return f"""<!DOCTYPE html>
<html lang="bg">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{meta['h1']} — ОП + Фондове БГ</title>
<meta name="description" content="{meta['desc']}">
<link rel="canonical" href="https://tools.gdprcheck.bg/institucii/{meta['slug']}">
<link rel="stylesheet" href="/water.min.css">
<link rel="stylesheet" href="/style.css">
<style>
.i-wrap {{ max-width: 760px; margin: 0 auto; padding: 32px 20px 60px; }}
.i-back {{ display:inline-flex; align-items:center; gap:6px; color:#2563eb; text-decoration:none; font-size:14px; margin-bottom:20px; }}
.i-desc {{ color:#64748b; font-size:15px; margin-bottom:8px; }}
.i-count {{ color:#94a3b8; font-size:13px; margin-bottom:24px; }}
.i-card {{ background:white; border-radius:10px; padding:16px 20px; margin-bottom:14px; box-shadow:0 2px 10px rgba(0,0,0,0.06); border-left:4px solid #2563eb; }}
.i-card h2 {{ font-size:16px; margin:0 0 8px; color:#1e293b; }}
.i-meta {{ display:flex; gap:10px; flex-wrap:wrap; margin-bottom:8px; }}
.i-tag {{ font-size:12px; padding:3px 10px; border-radius:20px; background:#eff6ff; color:#1d4ed8; font-weight:600; }}
.i-deadline {{ background:#fff7ed; color:#9a3412; }}
.i-deadline-none {{ background:#f1f5f9; color:#64748b; }}
.i-card a {{ font-size:13px; color:#2563eb; text-decoration:none; }}
.i-card a:hover {{ text-decoration:underline; }}
.i-empty {{ color:#64748b; }}
</style>
</head>
<body>
<header>
    <div class="container">
        <a href="/" class="logo-box">
            <div class="logo">ОП + Фондове БГ</div>
            <p class="tagline">Обществени поръчки и EU финансиране на едно място</p>
        </a>
    </div>
</header>

<div class="i-wrap">
    <a href="/programs" class="i-back">← Всички програми и поръчки</a>
    <h1>{meta['h1']}</h1>
    <p class="i-desc">{meta['desc']}</p>
    <p class="i-count">{count} активни в момента</p>
    {cards}
</div>

<footer>
    <div class="container">
        <p>© 2026 ОП + Фондове БГ &nbsp;|&nbsp; Безплатна услуга &nbsp;|&nbsp; <a href="/privacy">Поверителност</a> &nbsp;|&nbsp; <a href="mailto:alexbgodd@gmail.com">Контакт</a></p>
    </div>
</footer>
</body>
</html>
"""


def generate():
    programs = load_programs()
    if not programs:
        print("Няма данни в data/programs.json — прекратявам.")
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    by_source = {}
    for p in programs:
        by_source.setdefault(p['source'], []).append(p)

    written = 0
    skipped_unknown = set()
    for source_name, meta in SOURCE_META.items():
        progs = by_source.get(source_name, [])
        html = render_page(source_name, meta, progs)
        out_path = os.path.join(OUT_DIR, f"{meta['slug']}.html")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html)
        written += 1
        print(f"  ✓ {meta['slug']}.html  ({len(progs)} записа)")

    for source_name in by_source:
        if source_name not in SOURCE_META:
            skipped_unknown.add(source_name)
    if skipped_unknown:
        print(f"\n  ! Източници без slug мапинг (пропуснати): {', '.join(skipped_unknown)}")

    print(f"\n✓ Готово. Генерирани {written} institution страници в web/institucii/")

    generate_sitemap()


SITE_URL = "https://tools.gdprcheck.bg"


def generate_sitemap():
    """Генерира web/sitemap.xml — статични + institution страници."""
    import datetime
    today = datetime.date.today().isoformat()

    urls = [
        (f"{SITE_URL}/", "daily", "1.0"),
        (f"{SITE_URL}/programs", "daily", "0.9"),
        (f"{SITE_URL}/privacy", "yearly", "0.3"),
    ]
    for meta in SOURCE_META.values():
        urls.append((f"{SITE_URL}/institucii/{meta['slug']}", "daily", "0.7"))

    entries = "\n".join(
        f"""  <url>
    <loc>{loc}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{freq}</changefreq>
    <priority>{prio}</priority>
  </url>"""
        for loc, freq, prio in urls
    )

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{entries}
</urlset>
"""
    out_path = os.path.join(BASE_DIR, 'web', 'sitemap.xml')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(xml)
    print(f"✓ sitemap.xml генериран ({len(urls)} URL адреса).")


if __name__ == "__main__":
    generate()
