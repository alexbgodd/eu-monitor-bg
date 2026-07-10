import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, date, timedelta
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'programs.json')

SOURCES = [
    {
        "name": "Министерство на иновациите и растежа",
        "url": "https://www.mig.government.bg/otvoreni-proceduri/",
        "category": "бизнес",
        "parser": "mig",
        "base_url": "https://www.mig.government.bg"
    },
    {
        "name": "ПНИИДИТ — Иновации и дигитализация",
        "url": "https://www.mig.government.bg/programa-nauchni-izsledvaniya-inovaczii-i-digitalizacziya-za-inteligentna-transformacziya/",
        "category": "бизнес",
        "parser": "mig",
        "base_url": "https://www.mig.government.bg"
    },
    {
        "name": "ИСУН 2020 — Отворени процедури",
        "url": "https://eumis2020.government.bg/bg/s/Procedure/Active",
        "category": "общи",
        "parser": "isun",
        "base_url": "https://eumis2020.government.bg"
    },
    {
        "name": "finansirane.org — Отворени процедури",
        "url": "https://finansirane.org/fin/open",
        "category": "общи",
        "parser": "finansirane",
        "base_url": "https://finansirane.org"
    },
    {
        "name": "ИПУП — Отворени покани",
        "url": "https://www.ippm-bg.org/otvoreni-pokani-za-finansirane1.html",
        "category": "общи",
        "parser": "ippm",
        "base_url": "https://www.ippm-bg.org"
    },
    {
        "name": "ЕСФ България",
        "url": "https://esf.bg/proceduri/",
        "category": "социални",
        "parser": "esf"
    },
    {
        "name": "Еврофондове.бг",
        "url": "https://www.eufunds.bg/bg/page/976",
        "category": "общи",
        "parser": "eufunds"
    },
    {
        "name": "Министерство на земеделието",
        "url": "https://www.mzh.government.bg/bg/politiki-i-programi/programi-za-finansirane/",
        "category": "земеделие",
        "parser": "mzh",
        "base_url": "https://www.mzh.government.bg"
    },
    {
        "name": "Министерство на културата",
        "url": "https://mc.government.bg/pages.php?cat=22",
        "category": "култура",
        "parser": "mc",
        "base_url": "https://mc.government.bg"
    },
    {
        "name": "Държавен фонд Земеделие",
        "url": "https://www.dfz.bg/bg/open-support-procedures",
        "category": "земеделие",
        "parser": "dfz",
        "base_url": "https://www.dfz.bg"
    },
    {
        "name": "ЦРЧР — Еразъм+ и младеж",
        "url": "https://hrdc.bg/",
        "category": "образование",
        "parser": "hrdc",
        "base_url": "https://hrdc.bg"
    },
    {
        "name": "НПО портал — Финансиране",
        "url": "https://www.ngobg.info/bg/financing.html",
        "category": "социални",
        "parser": "ngobg",
        "base_url": "https://www.ngobg.info"
    },
    {
        "name": "Национален фонд Култура",
        "url": "https://ncf.bg/bg/programs",
        "category": "култура",
        "parser": "ncf",
        "base_url": "https://ncf.bg"
    },
    {
        "name": "Фонд Научни изследвания",
        "url": "https://www.fni.bg/?q=node/562",
        "category": "бизнес",
        "parser": "fni",
        "base_url": "https://www.fni.bg",
        "keywords": ["конкурс", "програм", "покан", "финансир", "грант", "изследван"]
    },
    {
        "name": "МОН — Национални програми",
        "url": "https://www.mon.bg/dokumentatsiya/programi-i-proekti/",
        "category": "образование",
        "parser": "mon",
        "base_url": "https://www.mon.bg"
    },
    {
        "name": "МОСВ — Програми и проекти",
        "url": "https://www.moew.government.bg/bg/ministerstvo/programi-i-proekti/",
        "category": "екология",
        "parser": "moew",
        "base_url": "https://www.moew.government.bg"
    }
]

def load_existing():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def expire_old(programs):
    """
    Изчиства стари записи:
    - Активни покани (type=tender) с краен срок: премахва когато срокът изтече
    - Активни покани без краен срок: премахва след 30 дни от намирането
    - EU фондове (type=fund): премахва след 180 дни
    Записите без дата се запазват.
    """
    today = date.today()
    kept, removed = [], 0
    for p in programs:
        # За тендери с изричен краен срок — изтича когато срокът мине
        if p.get('type') == 'tender' and p.get('deadline'):
            try:
                dl = date.fromisoformat(p['deadline'][:10])
                if dl < today:
                    removed += 1
                    continue
                else:
                    kept.append(p)
                    continue
            except (ValueError, TypeError):
                pass  # ако форматът е грешен, падаме към обичайната логика

        # Иначе — по дата на намиране
        found_str = p.get('found_at', '')[:10]
        if not found_str:
            kept.append(p)
            continue
        try:
            found_date = date.fromisoformat(found_str)
        except ValueError:
            kept.append(p)
            continue
        age = (today - found_date).days
        # Тендери без срок — изтичат след 30 дни
        # EU фондове — изтичат след 90 дни
        max_age = 30 if p.get('type') == 'tender' else 90
        if age <= max_age:
            kept.append(p)
        else:
            removed += 1
    if removed:
        print(f"  [Изтекли] Премахнати {removed} стари записа.")
    return kept

def save_programs(programs):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(programs, f, ensure_ascii=False, indent=2)

def fetch_isun():
    """Специален fetch за ИСУН — използва Session с пълни browser headers."""
    try:
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'bg-BG,bg;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        # Първо зареждаме началната страница за cookies
        session.get('https://eumis2020.government.bg/bg/s/Default/Index',
                   headers=headers, timeout=20, verify=False)
        # После зареждаме процедурите
        r = session.get('https://eumis2020.government.bg/bg/s/Procedure/Active',
                       headers=headers, timeout=20, verify=False)
        r.encoding = 'utf-8'
        return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        print(f"  Грешка ИСУН: {e}")
        return None

def fetch_page(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0'
    }
    try:
        r = requests.get(url, headers=headers, timeout=15, verify=False)
        r.encoding = 'utf-8'
        return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        print(f"  Грешка: {e}")
        return None

def make_entry(uid, title, source, deadline, entry_type="fund"):
    return {
        "id": uid,
        "title": title,
        "source": source["name"],
        "category": source["category"],
        "url": uid if uid.startswith('http') else '',
        "deadline": deadline,
        "type": entry_type,
        "found_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }


# ── ЦАИС ЕОП open-data S3 ──────────────────────────────────────────────────

EOP_BASE = "https://storage.eop.bg"
EOP_UA   = "eu-monitor-bg/1.0 (+https://github.com)"

def _eop_list_bucket(day_iso):
    """Връща S3 ключовете за даден ден или None."""
    url = f"{EOP_BASE}/open-data-{day_iso}/"
    req = urllib.request.Request(url, headers={"User-Agent": EOP_UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            root = ET.fromstring(r.read())
        ns = "{http://s3.amazonaws.com/doc/2006-03-01/}"
        return [el.text for el in root.iter(f"{ns}Key")]
    except Exception:
        return None

def _eop_fetch_json(day_iso, key):
    """Изтегля JSON файл от S3 bucket."""
    url = f"{EOP_BASE}/open-data-{day_iso}/{urllib.parse.quote(key)}"
    req = urllib.request.Request(url, headers={"User-Agent": EOP_UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except Exception:
        return None

def fetch_eop_tenders(days_back=7):
    """
    Чете OCDS обявления (активни покани) от storage.eop.bg за последните days_back дни.
    Файлът се казва 'обявления' и е в OCDS 1.1 формат (пакет с releases).
    Връща списък [(day_iso, release), ...] само за активни тендери.
    """
    results = []
    today = date.today()
    for offset in range(1, days_back + 1):
        day = today - timedelta(days=offset)
        day_iso = day.isoformat()
        keys = _eop_list_bucket(day_iso)
        if not keys:
            continue
        # OCDS обявления файл
        ocds_key = next((k for k in keys if "обявлени" in k.lower()), None)
        if not ocds_key:
            continue
        data = _eop_fetch_json(day_iso, ocds_key)
        if not data:
            continue
        # OCDS package: {"releases": [...], ...}
        releases = data.get("releases", []) if isinstance(data, dict) else data
        for rel in releases:
            tag = rel.get("tag", [])
            tender = rel.get("tender", {})
            status = tender.get("status", "")
            # Вземаме само активни покани (не резултати от класиране, не отменени)
            if "tender" in tag or status == "active":
                results.append((day_iso, rel))
    return results

def parse_eop(records, existing_ids):
    """
    Преобразува OCDS releases от ЦАИС ЕОП в обекти за programs.json.
    OCDS полета: ocid, tender.title, tender.tenderPeriod.endDate,
                 buyer.name, tender.mainProcurementCategory
    """
    programs = []
    seen = set()

    for day_iso, rel in records:
        ocid = rel.get("ocid", "")
        tender = rel.get("tender", {})
        buyer = rel.get("buyer", {})

        title = tender.get("title") or tender.get("description") or ""
        authority = buyer.get("name") or ""
        uid = ocid or tender.get("id") or rel.get("id") or ""

        # Краен срок от tenderPeriod.endDate
        deadline = ""
        end_date = tender.get("tenderPeriod", {}).get("endDate", "")
        if end_date:
            deadline = end_date[:10]  # YYYY-MM-DD

        if not title or not uid:
            continue
        if uid in seen or uid in existing_ids:
            continue
        seen.add(uid)

        cpv = str(tender.get("mainProcurementCategory", ""))
        category = _eop_category(title, cpv)

        # URL: tender.id е обикновено номерът на поръчката (напр. "00-00-2026-0001234")
        tender_id = tender.get("id", "")
        if tender_id:
            full_url = f"https://app.eop.bg/bg-BG/notice/0/{urllib.parse.quote(tender_id)}"
        else:
            full_url = "https://app.eop.bg/today"

        programs.append({
            "id": uid,
            "title": title[:200],
            "source": "ЦАИС ЕОП — Обявления",
            "category": category,
            "url": full_url,
            "deadline": deadline,
            "type": "tender",
            "authority": authority[:100],
            "found_at": day_iso,
            "code": tender_id or uid,
        })
    return programs

def _eop_category(title, cpv=""):
    t = (title + " " + cpv).lower()
    if any(w in t for w in ["иновац", "дигитал", "ит ", "софтуер", "информацион", "технолог"]):
        return "бизнес"
    if any(w in t for w in ["образован", "обучен", "училищ", "детск"]):
        return "образование"
    if any(w in t for w in ["социал", "здрав", "болниц", "медицин"]):
        return "социални"
    if any(w in t for w in ["земедел", "горск", "рибарств", "храни"]):
        return "земеделие"
    if any(w in t for w in ["строител", "пътищ", "инфраструктур", "ремонт", "реконструкц"]):
        return "инфраструктура"
    if any(w in t for w in ["природ", "околна среда", "отпадъц", "вод"]):
        return "екология"
    if any(w in t for w in ["култур", "изкуств", "театър", "музей"]):
        return "култура"
    if any(w in t for w in ["общин", "кметств", "район"]):
        return "общини"
    return "търгове"

def parse_isun(soup, source):
    """ИСУН 2020 — пълен списък отворени EU процедури в България."""
    programs = []
    if not soup:
        return programs
    seen = set()

    def get_category(text):
        t = text.lower()
        if any(w in t for w in ['иновац', 'дигитал', 'конкурентоспособ', 'предприят', 'цифров']):
            return 'бизнес'
        if any(w in t for w in ['образован', 'обучен', 'училищ', 'висше', 'професионал', 'еразъм']):
            return 'образование'
        if any(w in t for w in ['социал', 'заетост', 'труд', 'здрав', 'деца', 'семейст', 'човешки ресурс']):
            return 'социални'
        if any(w in t for w in ['земедел', 'рибарств', 'аквакулт', 'морско дел', 'храни']):
            return 'земеделие'
        if any(w in t for w in ['околна среда', 'природ', 'биологично', 'натура', 'води', 'климат']):
            return 'екология'
        if any(w in t for w in ['регион', 'градск', 'общин', 'инфраструктур']):
            return 'общини'
        return 'общи'

    import re
    # Процедурите са линкове с код BG... в текста
    for a in soup.select('a'):
        text = a.get_text(strip=True)
        href = a.get('href', '')
        if not re.match(r'^BG\d+', text):
            continue
        if text in seen:
            continue
        seen.add(text)
        parts = text.split(' - ', 1)
        code = parts[0].strip()
        title = parts[1].strip() if len(parts) > 1 else text
        full_url = (base + href) if href.startswith('/') else href
        entry = make_entry(code, title, source, '')
        entry['url'] = full_url
        entry['category'] = get_category(title)
        entry['code'] = code
        programs.append(entry)
    return programs

def parse_mig(soup, source):
    """Министерство на иновациите и растежа."""
    programs = []
    if not soup:
        return programs
    base = source.get('base_url', 'https://www.mig.government.bg')
    seen = set()
    keywords = ['процедур', 'програм', 'покан', 'финансир', 'грант', 'иновац', 'дигитал', 'конкурентоспособ']
    skip = ['начало', 'контакти', 'за нас', 'новини', 'english']
    for a in soup.select('a'):
        text = a.get_text(strip=True)
        href = a.get('href', '')
        if not href or href.startswith('#') or href.startswith('mailto'):
            continue
        if text.lower() in skip or len(text) < 12:
            continue
        full_url = (base + href) if href.startswith('/') else href
        if (text and len(text) < 250 and text not in seen and
                any(w in text.lower() for w in keywords)):
            seen.add(text)
            programs.append(make_entry(full_url, text, source, ''))
    return programs

def parse_opic(soup, source):
    """ОПИК листва процедури в div-ове с клас или в таблица."""
    programs = []
    if not soup:
        return programs
    # Опитваме различни селектори
    selectors = [
        'table tr',
        '.view-content .views-row',
        'article',
        '.field-content a',
        'h3 a', 'h2 a'
    ]
    for sel in selectors:
        items = soup.select(sel)
        if not items:
            continue
        if sel == 'table tr':
            for row in items[1:]:
                cells = row.select('td')
                if len(cells) >= 2:
                    a = cells[0].find('a')
                    name = cells[0].get_text(strip=True)
                    href = a['href'] if a else ''
                    url = ('https://www.opic.bg' + href) if href.startswith('/') else href
                    deadline = cells[-1].get_text(strip=True)
                    if name and len(name) > 5:
                        programs.append(make_entry(url or name, name, source, deadline))
        else:
            for item in items:
                a = item if item.name == 'a' else item.find('a')
                if a:
                    text = a.get_text(strip=True)
                    href = a.get('href', '')
                    full_url = ('https://www.opic.bg' + href) if href.startswith('/') else href
                    if text and len(text) > 10:
                        programs.append(make_entry(full_url or text, text, source, ''))
        if programs:
            break
    return programs

def parse_esf(soup, source):
    programs = []
    if not soup:
        return programs
    for sel in ['article h2 a', 'article h3 a', '.entry-title a',
                '.post-title a', 'h2 a', 'h3 a', '.title a']:
        items = soup.select(sel)
        if items:
            for a in items:
                text = a.get_text(strip=True)
                href = a.get('href', '')
                if text and len(text) > 8:
                    programs.append(make_entry(href, text, source, ''))
            if programs:
                break
    return programs

def parse_eufunds(soup, source):
    programs = []
    if not soup:
        return programs
    seen = set()
    keywords = ['процедур', 'програм', 'схем', 'покан', 'финансир', 'грант']
    for a in soup.select('a'):
        text = a.get_text(strip=True)
        href = a.get('href', '')
        if (text and len(text) > 12 and text not in seen and
                any(w in text.lower() for w in keywords)):
            seen.add(text)
            full_url = href if href.startswith('http') else 'https://www.eufunds.bg' + href
            programs.append(make_entry(full_url, text, source, ''))
    return programs

def parse_mzh(soup, source):
    """Министерство на земеделието — страница с програми за финансиране."""
    programs = []
    if not soup:
        return programs
    base = source.get('base_url', 'https://www.mzh.government.bg')
    seen = set()
    # Търсим линкове в main content, изключваме навигация
    for sel in ['.main-content a', '#content a', 'article a', '.entry a', 'main a', 'td a', 'li a']:
        items = soup.select(sel)
        if not items:
            continue
        for a in items:
            text = a.get_text(strip=True)
            href = a.get('href', '')
            if not href or href.startswith('#') or href.startswith('mailto'):
                continue
            full_url = (base + href) if href.startswith('/') else href
            # Само линкове към конкретни програми/мерки
            if (text and 15 < len(text) < 200 and text not in seen and
                    any(w in text.lower() for w in ['мярк', 'програм', 'финансир', 'схем', 'подмярк', 'интервенц'])):
                seen.add(text)
                programs.append(make_entry(full_url, text, source, ''))
        if programs:
            break
    return programs

def parse_mc(soup, source):
    """Министерство на културата."""
    programs = []
    if not soup:
        return programs
    base = source.get('base_url', 'https://mc.government.bg')
    seen = set()
    for a in soup.select('a'):
        text = a.get_text(strip=True)
        href = a.get('href', '')
        if not href or href.startswith('#'):
            continue
        full_url = (base + '/' + href) if not href.startswith('http') else href
        if (text and 10 < len(text) < 200 and text not in seen and
                any(w in text.lower() for w in ['програм', 'финансир', 'конкурс', 'грант', 'стипенд', 'субсид'])):
            seen.add(text)
            programs.append(make_entry(full_url, text, source, ''))
    return programs

def parse_dfz(soup, source):
    """Държавен фонд Земеделие — отворени процедури."""
    programs = []
    if not soup:
        return programs
    base = source.get('base_url', 'https://www.dfz.bg')
    seen = set()
    keywords = ['схем', 'мярк', 'процедур', 'подпомаг', 'интервенц', 'програм', 'финансир']
    for a in soup.select('a'):
        text = a.get_text(strip=True)
        href = a.get('href', '')
        if not href or href.startswith('#') or href.startswith('mailto'):
            continue
        full_url = (base + href) if href.startswith('/') else href
        if (text and 10 < len(text) < 250 and text not in seen and
                any(w in text.lower() for w in keywords)):
            seen.add(text)
            programs.append(make_entry(full_url, text, source, ''))
    return programs

def parse_hrdc(soup, source):
    """ЦРЧР — само реални покани за кандидатстване по Еразъм+."""
    programs = []
    if not soup:
        return programs
    base = source.get('base_url', 'https://hrdc.bg')
    seen = set()
    # Само реални покани — изисква поне едно от тези
    must_have = ['покан', 'кандидатстван', 'насоки за', 'мобилност', 'изграждане на капацитет']
    # Новини, съобщения и архив — изключваме
    skip = ['отбелязв', 'напредък', 'шатра', 'отчита', 'резултат',
            'популяризир', 'конференц', '2014', '2020 >', 'информационна',
            'съобщен', 'новина', 'събитие']
    for a in soup.select('a'):
        text = a.get_text(strip=True)
        href = a.get('href', '')
        if not href or href.startswith('#') or href.startswith('mailto'):
            continue
        if not text or len(text) < 15 or len(text) > 200:
            continue
        if text in seen:
            continue
        tl = text.lower()
        if any(w in tl for w in skip):
            continue
        if not any(w in tl for w in must_have):
            continue
        seen.add(text)
        full_url = (base + href) if href.startswith('/') else href
        programs.append(make_entry(full_url, text, source, ''))
    return programs

def parse_ngobg(soup, source):
    """НПО портал — списък с отворени програми за финансиране."""
    programs = []
    if not soup:
        return programs
    base = source.get('base_url', 'https://www.ngobg.info')
    seen = set()
    skip_words = ['добави финансиране', 'виж архив', 'финансиране', 'архив', 'назад', 'напред']
    keywords = ['програм', 'финансир', 'грант', 'фонд', 'конкурс', 'покан', 'процедур', 'отворен']
    for a in soup.select('a'):
        text = a.get_text(strip=True)
        href = a.get('href', '')
        if not href or href.startswith('#') or href.startswith('mailto'):
            continue
        if text.lower() in skip_words or len(text) < 15:
            continue
        full_url = (base + href) if href.startswith('/') else href
        if (text and len(text) < 200 and text not in seen and
                any(w in text.lower() for w in keywords)):
            seen.add(text)
            programs.append(make_entry(full_url, text, source, ''))
    return programs

def parse_ncf(soup, source):
    """Национален фонд Култура."""
    programs = []
    if not soup:
        return programs
    base = source.get('base_url', 'https://ncf.bg')
    seen = set()
    skip_words = ['архив програми', 'кандидатствай по програма', 'архив', 'начало', 'контакти']
    keywords = ['програм', 'конкурс', 'грант', 'финансир', 'стипенд', 'покан']
    for a in soup.select('a'):
        text = a.get_text(strip=True)
        href = a.get('href', '')
        if not href or href.startswith('#') or href.startswith('mailto'):
            continue
        if text.lower() in skip_words or len(text) < 12:
            continue
        full_url = (base + href) if href.startswith('/') else href
        if (text and len(text) < 200 and text not in seen and
                any(w in text.lower() for w in keywords)):
            seen.add(text)
            programs.append(make_entry(full_url, text, source, ''))
    return programs

def parse_finansirane(soup, source):
    """finansirane.org — агрегатор на отворени EU процедури."""
    programs = []
    if not soup:
        return programs
    base = source.get('base_url', 'https://finansirane.org')
    seen = set()
    keywords = ['процедур', 'програм', 'покан', 'грант', 'финансир', 'конкурс']
    for a in soup.select('a'):
        text = a.get_text(strip=True)
        href = a.get('href', '')
        if not href or href.startswith('#') or href.startswith('mailto'):
            continue
        if len(text) < 15 or text in seen:
            continue
        full_url = (base + href) if href.startswith('/') else href
        if any(w in text.lower() for w in keywords):
            seen.add(text)
            programs.append(make_entry(full_url, text, source, ''))
    return programs

def parse_ippm(soup, source):
    """ИПУП — Институт за управление на програми и проекти."""
    programs = []
    if not soup:
        return programs
    base = source.get('base_url', 'https://www.ippm-bg.org')
    seen = set()
    keywords = ['процедур', 'програм', 'покан', 'грант', 'финансир', 'конкурс', 'отворен']
    noise = ['програмии проекти', 'програми и проекти', 'начало', 'контакти',
             'за нас', 'новини', 'english', 'bg', 'търсене']
    for a in soup.select('a'):
        text = a.get_text(strip=True)
        href = a.get('href', '')
        if not href or href.startswith('#') or href.startswith('mailto'):
            continue
        if len(text) < 20 or text in seen:
            continue
        if text.lower() in noise or text.lower().startswith('програмии'):
            continue
        full_url = (base + '/' + href) if not href.startswith('http') else href
        if (any(w in text.lower() for w in keywords) and
                not full_url.endswith('proekti.html')):
            seen.add(text)
            programs.append(make_entry(full_url, text, source, ''))
    return programs

def parse_fni(soup, source):
    """Фонд Научни изследвания — само отворени конкурси, без навигация и новини."""
    programs = []
    if not soup:
        return programs
    base = source.get('base_url', 'https://www.fni.bg')
    seen = set()
    # Изключваме навигационни и приключили елементи
    exclude = ['приключил', 'предстоящ', 'наръчник', 'представи', 'архив', 'новини', 'контакти']
    for a in soup.select('a'):
        text = a.get_text(strip=True)
        href = a.get('href', '')
        if not href or href.startswith('#') or href.startswith('mailto'):
            continue
        if not text or len(text) < 20 or len(text) > 250:
            continue
        if text in seen:
            continue
        tl = text.lower()
        if any(w in tl for w in exclude):
            continue
        if not any(w in tl for w in ['конкурс', 'програм', 'покан', 'финансир', 'грант']):
            continue
        seen.add(text)
        full_url = href if href.startswith('http') else base + href
        programs.append(make_entry(full_url, text, source, ''))
    return programs


def parse_mon(soup, source):
    """МОН — Национални програми за образование."""
    programs = []
    if not soup:
        return programs
    base = source.get('base_url', 'https://www.mon.bg')
    seen = set()
    skip = ['архив', 'изпълнителна агенция', 'програми и проекти',
            '2019', '2020 –', '2020-', '2021 –', '2021-', '2022 –', '2022-',
            '2023 –', '2023-', '2014-2020', 'приключил']
    keywords = ['програм', 'покан', 'финансир', 'грант', 'конкурс', 'ремонт', 'изграждан', 'обновяван', 'санир', 'управлен']
    for a in soup.select('a'):
        text = a.get_text(strip=True)
        href = a.get('href', '')
        if not href or href.startswith('#') or href.startswith('mailto'):
            continue
        if not text or len(text) < 15 or len(text) > 200:
            continue
        if text in seen:
            continue
        tl = text.lower()
        if any(w in tl for w in skip):
            continue
        if not any(w in tl for w in keywords):
            continue
        seen.add(text)
        full_url = (base + href) if href.startswith('/') else href
        programs.append(make_entry(full_url, text, source, ''))
    return programs

def parse_moew(soup, source):
    """МОСВ — Програми и проекти за околна среда."""
    programs = []
    if not soup:
        return programs
    base = source.get('base_url', 'https://www.moew.government.bg')
    seen = set()
    skip = ['приключил', 'архив', '2010', 'нормативни документи', 'обща информация']
    keywords = ['програм', 'финансир', 'покан', 'грант', 'конкурс', 'процедур', 'проект', 'фонд', 'life']
    for a in soup.select('a'):
        text = a.get_text(strip=True)
        href = a.get('href', '')
        if not href or href.startswith('#') or href.startswith('mailto'):
            continue
        if not text or len(text) < 15 or len(text) > 200:
            continue
        if text in seen:
            continue
        tl = text.lower()
        if any(w in tl for w in skip):
            continue
        if not any(w in tl for w in keywords):
            continue
        seen.add(text)
        full_url = (base + href) if href.startswith('/') else href
        programs.append(make_entry(full_url, text, source, ''))
    return programs

def parse_generic_links(soup, source):
    """Generic parser — сканира всички линкове по ключови думи от source config."""
    programs = []
    if not soup:
        return programs
    base = source.get('base_url', '')
    keywords = source.get('keywords', ['програм', 'финансир', 'покан', 'грант', 'конкурс'])
    seen = set()
    for a in soup.select('a'):
        text = a.get_text(strip=True)
        href = a.get('href', '')
        if not href or href.startswith('#') or href.startswith('mailto'):
            continue
        if not text or len(text) < 10 or len(text) > 250:
            continue
        if text in seen:
            continue
        if not any(w in text.lower() for w in keywords):
            continue
        seen.add(text)
        if href.startswith('http'):
            full_url = href
        elif href.startswith('/'):
            full_url = base + href
        else:
            full_url = base + '/' + href
        programs.append(make_entry(full_url, text, source, ''))
    return programs


PARSERS = {
    "isun": parse_isun,
    "mig": parse_mig,
    "opic": parse_opic,
    "esf": parse_esf,
    "eufunds": parse_eufunds,
    "mzh": parse_mzh,
    "mc": parse_mc,
    "dfz": parse_dfz,
    "hrdc": parse_hrdc,
    "ngobg": parse_ngobg,
    "ncf": parse_ncf,
    "finansirane": parse_finansirane,
    "ippm": parse_ippm,
    "generic_links": parse_generic_links,
    "fni": parse_fni,
    "mon": parse_mon,
    "moew": parse_moew,
}

def scrape_all():
    existing = load_existing()
    # Изчистваме старите сключени договори (заменени с активни обявления)
    old_contracts_src = "ЦАИС ЕОП — Обществени поръчки"
    old_count = sum(1 for p in existing if p.get("source") == old_contracts_src)
    if old_count:
        existing = [p for p in existing if p.get("source") != old_contracts_src]
        print(f"  [Cleanup] Премахнати {old_count} стари договора (заменено с активни обявления).")
    existing_ids = {p['id'] for p in existing}
    new_programs = []

    for source in SOURCES:
        print(f"\n>>> {source['name']}")
        if source['parser'] == 'isun':
            soup = fetch_isun()
        else:
            soup = fetch_page(source['url'])
        parser = PARSERS.get(source['parser'])
        if parser and soup:
            found = parser(soup, source)
            count = 0
            for p in found:
                if p['id'] not in existing_ids:
                    new_programs.append(p)
                    existing_ids.add(p['id'])
                    count += 1
                    print(f"    НОВО: {p['title'][:80]}")
            if count == 0:
                print(f"    Няма нови.")
        else:
            print(f"    Неуспешно зареждане.")

    # ЦАИС ЕОП (storage.eop.bg S3 open-data — OCDS обявления)
    print(f"\n>>> ЦАИС ЕОП — Активни обявления (последните 7 дни)")
    try:
        eop_records = fetch_eop_tenders(days_back=7)
        if eop_records:
            eop_programs = parse_eop(eop_records, existing_ids)
            count = 0
            for p in eop_programs:
                if p['id'] not in existing_ids:
                    new_programs.append(p)
                    existing_ids.add(p['id'])
                    count += 1
                    print(f"    НОВО: {p['title'][:80]}")
            print(f"    {'Няма нови.' if count == 0 else f'{count} нови обявления.'}")
        else:
            print(f"    Няма данни от storage.eop.bg (проверете връзката).")
    except Exception as e:
        print(f"    Грешка ЦАИС ЕОП: {e}")

    # Изчисти изтеклите записи
    all_programs = new_programs + existing
    all_programs = expire_old(all_programs)

    if new_programs:
        save_programs(all_programs)
        print(f"\n✓ Записани {len(new_programs)} нови. Общо активни: {len(all_programs)}")
    else:
        save_programs(all_programs)
        print(f"\n— Няма нови програми. Активни: {len(all_programs)}")

    return new_programs

if __name__ == "__main__":
    scrape_all()
