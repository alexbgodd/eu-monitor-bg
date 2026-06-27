import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'programs.json')

SOURCES = [
    {
        "name": "ОПИК - Иновации и конкурентоспособност",
        "url": "https://www.opic.bg/proceduri-za-kandidatstvane/otvoreni-proceduri",
        "category": "бизнес",
        "parser": "opic"
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

def save_programs(programs):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(programs, f, ensure_ascii=False, indent=2)

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

def make_entry(uid, title, source, deadline):
    return {
        "id": uid,
        "title": title,
        "source": source["name"],
        "category": source["category"],
        "url": uid if uid.startswith('http') else '',
        "deadline": deadline,
        "found_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

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
    """ЦРЧР — Еразъм+ покани и програми."""
    programs = []
    if not soup:
        return programs
    base = source.get('base_url', 'https://hrdc.bg')
    seen = set()
    keywords = ['покан', 'програм', 'еразъм', 'кандидатстван', 'грант', 'финансир', 'младеж', 'мобилност']
    for a in soup.select('a'):
        text = a.get_text(strip=True)
        href = a.get('href', '')
        if not href or href.startswith('#') or href.startswith('mailto'):
            continue
        full_url = (base + href) if href.startswith('/') else href
        if (text and 10 < len(text) < 200 and text not in seen and
                any(w in text.lower() for w in keywords)):
            seen.add(text)
            programs.append(make_entry(full_url, text, source, ''))
    return programs

def parse_ngobg(soup, source):
    """НПО портал — списък с отворени програми за финансиране."""
    programs = []
    if not soup:
        return programs
    base = source.get('base_url', 'https://www.ngobg.info')
    seen = set()
    for a in soup.select('a'):
        text = a.get_text(strip=True)
        href = a.get('href', '')
        if not href or href.startswith('#') or href.startswith('mailto'):
            continue
        full_url = (base + href) if href.startswith('/') else href
        if (text and 10 < len(text) < 200 and text not in seen and
                '/financing/' in href or '/bg/financing' in href):
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
    keywords = ['програм', 'конкурс', 'грант', 'финансир', 'стипенд', 'покан']
    for a in soup.select('a'):
        text = a.get_text(strip=True)
        href = a.get('href', '')
        if not href or href.startswith('#') or href.startswith('mailto'):
            continue
        full_url = (base + href) if href.startswith('/') else href
        if (text and 8 < len(text) < 200 and text not in seen and
                any(w in text.lower() for w in keywords)):
            seen.add(text)
            programs.append(make_entry(full_url, text, source, ''))
    return programs

PARSERS = {
    "opic": parse_opic,
    "esf": parse_esf,
    "eufunds": parse_eufunds,
    "mzh": parse_mzh,
    "mc": parse_mc,
    "dfz": parse_dfz,
    "hrdc": parse_hrdc,
    "ngobg": parse_ngobg,
    "ncf": parse_ncf,
}

def scrape_all():
    existing = load_existing()
    existing_ids = {p['id'] for p in existing}
    new_programs = []

    for source in SOURCES:
        print(f"\n>>> {source['name']}")
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

    if new_programs:
        save_programs(new_programs + existing)
        print(f"\n✓ Записани {len(new_programs)} нови програми в data/programs.json")
    else:
        print(f"\n— Няма нови програми.")

    return new_programs

if __name__ == "__main__":
    scrape_all()
