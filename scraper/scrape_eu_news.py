"""
EU-Bulgaria News Aggregator — RSS синдикация
Чете публични RSS feeds от официални EU и BG медийни източници.
RSS е стандарт за синдикация — проектиран да се чете автоматично.
Записва само: заглавие, дата, кратко резюме (max 300 символа), URL, източник.
Стартирай: cd scraper && python scrape_eu_news.py
"""

import requests
import xml.etree.ElementTree as ET
import json
import os
import re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

OUTPUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'eu-news.json')
MAX_ITEMS = 200  # горна граница (филтърът по дата е основното ограничение)
MAX_DESC  = 300  # символи от описанието
DAYS_BACK = 2    # само днес и вчера

EU_KEYWORDS = [
    'европейск', 'european', 'еврофонд', 'eu ', ' eu', 'cohesion',
    'structural fund', 'европейско финансиране', 'еврофинансиране',
    'оперативна програма', 'европейска комисия', 'european commission',
    'еврокомисия', 'european parliament', 'европейски парламент',
    'recovery', 'nextgeneration', 'multiannual', 'исун', 'еафрдр',
    'еврофондов', 'евросредства', 'european union', 'европейски съюз',
]

NEWS_TOPIC_KEYWORDS = {
    "бизнес":      ["бизнес", "икономик", "предприемач", "инвестиц", "стартъп", "конкурентоспособ", "компани", "фирм"],
    "земеделие":   ["земедел", "фермер", "селскостопан", "аграр", "животновъд", "реколт", "рибарств"],
    "култура":     ["култур", "изкуств", "театър", "музей", "кино", "филм", "изложб", "концерт"],
    "социални":    ["социал", "здравеопазван", "здрав", "пенси", "осигур", "заетост", "труд", "болниц", "нзок"],
    "образование": ["образован", "училищ", "университет", "студент", "учениц", "детск", "матур"],
    "туризъм":     ["туризъм", "хотел", "курорт", "летовищ", "морск", "планинск"],
    "екология":    ["околна среда", "климат", "въглеродн", "зелен", "природ", "отпадъц", "води", "язовир"],
    "ит":          ["дигитал", "технолог", "софтуер", "изкуствен интелект", "стартъп технолог", "кибер"],
    "общини":      ["общин", "кмет", "инфраструктур", "региони", "област"],
}


def get_topic(title: str, desc: str, source: str) -> str:
    """EU за България / тематична категория (като при програмите) / общи БГ новини."""
    if source in ('European Commission', 'Google News EN'):
        return 'eu'
    combined = (title + ' ' + desc).lower()
    if any(kw in combined for kw in EU_KEYWORDS):
        return 'eu'
    for topic, keywords in NEWS_TOPIC_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            return topic
    return 'общи'

# -----------------------------------------------------------------------
# RSS ИЗТОЧНИЦИ — само публични, официални или лицензирани за синдикация
# -----------------------------------------------------------------------
FEEDS = [
    # --- Google News (публична услуга, без scraping) ---
    {
        "name": "Google News BG",
        "url": "https://news.google.com/rss/search?q=EU+финансиране+България+when:3d&hl=bg&gl=BG&ceid=BG:bg",
        "lang": "bg", "filter": None,
    },
    {
        "name": "Google News EN",
        "url": "https://news.google.com/rss/search?q=EU+Bulgaria+funding+grants+when:3d&hl=en&gl=BG&ceid=BG:en",
        "lang": "en", "filter": None,
    },
    # --- EU официални ---
    {
        "name": "European Commission",
        "url": "https://ec.europa.eu/commission/presscorner/api/rss",
        "lang": "en",
        "filter": ["bulgar", "cohesion", "structural fund", "recovery", "regional"],
    },
    # --- Български медии ---
    {
        "name": "Dnevnik.bg",
        "url": "https://www.dnevnik.bg/rss/",
        "lang": "bg",
        "filter": ["еврофонд", "еврокомисия", "европейска комисия", "европейски средства",
                   "европейски пари", "оперативна програма", "структурен фонд",
                   "кохезионен", "европейско финансиране", "еврофинансиране"],
    },
    {
        "name": "Capital.bg",
        "url": "https://www.capital.bg/rss/",
        "lang": "bg",
        "filter": ["еврофонд", "еврокомисия", "европейска комисия", "европейски средства",
                   "европейски пари", "оперативна програма", "структурен фонд",
                   "кохезионен", "европейско финансиране", "еврофинансиране"],
    },
    {
        "name": "Investor.bg",
        "url": "https://www.investor.bg/rss/news",
        "lang": "bg",
        "filter": ["еврофонд", "еврокомисия", "европейска комисия", "европейски средства",
                   "европейски пари", "оперативна програма", "структурен фонд",
                   "кохезионен", "европейско финансиране", "еврофинансиране"],
    },
    # --- Общи БГ новини (без филтър — попълват тематичните категории) ---
    {
        "name": "Focus News",
        "url": "https://www.focus-news.net/rss.php?cat=6",
        "lang": "bg", "filter": None,
    },
    {
        "name": "BG ON AIR",
        "url": "https://www.bgonair.bg/rss/c/2-bulgaria",
        "lang": "bg", "filter": None,
    },
    {
        "name": "Bloomberg TV BG",
        "url": "https://www.bloombergtv.bg/rss/c/9-bulgaria",
        "lang": "bg", "filter": None,
    },
]

HEADERS = {
    "User-Agent": "EUMonitorBG/1.0 RSS Reader (https://tools.gdprcheck.bg; news aggregator)",
    "Accept": "application/rss+xml, application/xml, text/xml",
}


def clean(text: str) -> str:
    """Премахва HTML тагове и излишни whitespace."""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def parse_date(text: str) -> str:
    """Връща ISO дата или празен стринг."""
    if not text:
        return ""
    try:
        dt = parsedate_to_datetime(text)
        return dt.strftime('%Y-%m-%d')
    except Exception:
        pass
    for fmt in ('%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(text[:19], fmt).strftime('%Y-%m-%d')
        except Exception:
            pass
    return text[:10]  # last resort


def passes_filter(title: str, desc: str, keywords) -> bool:
    if keywords is None:
        return True
    combined = (title + ' ' + desc).lower()
    return any(kw.lower() in combined for kw in keywords)


def _parse_bs4_entries(entries, feed: dict) -> list:
    items = []
    for entry in entries:
        def gtag(tag):
            el = entry.find(tag)
            return el.get_text(strip=True) if el else ''
        title = clean(gtag('title'))
        desc  = clean(gtag('description') or gtag('summary') or gtag('content'))
        link  = gtag('link') or gtag('guid')
        date  = parse_date(gtag('pubDate') or gtag('published') or gtag('updated'))
        if not title or not link:
            continue
        if not passes_filter(title, desc, feed.get("filter")):
            continue
        items.append({
            "title":  title,
            "desc":   desc[:MAX_DESC],
            "url":    link.strip(),
            "date":   date,
            "source": feed["name"],
            "lang":   feed["lang"],
            "topic":  get_topic(title, desc, feed["name"]),
        })
    return items


def fetch_feed(feed: dict) -> list:
    items = []
    verify = feed.get("verify", True)
    lenient = feed.get("lenient", False)

    try:
        kwargs = {"headers": HEADERS, "timeout": 12, "verify": verify}
        if not verify:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        resp = requests.get(feed["url"], **kwargs)
        resp.raise_for_status()
    except Exception as e:
        print(f"  ⚠ {feed['name']}: {e}")
        return items

    # Парсиране — lenient режим за malformed XML
    try:
        if lenient:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.content, 'html.parser')
            entries = soup.find_all('item') or soup.find_all('entry')
            return _parse_bs4_entries(entries, feed)
        else:
            root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        # Fallback към lenient
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.content, 'html.parser')
            entries = soup.find_all('item') or soup.find_all('entry')
            print(f"  ⚠ {feed['name']}: malformed XML — fallback към lenient парсер")
            return _parse_bs4_entries(entries, feed)
        except Exception as e2:
            print(f"  ⚠ {feed['name']}: {e2}")
            return items

    # Поддържа стандартен RSS 2.0 и Atom
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    rss_items  = root.findall('.//item')
    atom_items = root.findall('.//atom:entry', ns)
    entries = rss_items if rss_items else atom_items

    for entry in entries:
        def get(tag, default=''):
            el = entry.find(tag)
            if el is None:
                el = entry.find(f'atom:{tag}', ns)
            return (el.text or '') if el is not None else default

        title = clean(get('title'))
        desc  = clean(get('description') or get('summary') or get('content'))
        link  = get('link') or get('guid')
        date  = parse_date(get('pubDate') or get('published') or get('updated'))

        # Atom link може да е атрибут
        if not link:
            link_el = entry.find('atom:link', ns)
            if link_el is not None:
                link = link_el.get('href', '')

        if not title or not link:
            continue

        if not passes_filter(title, desc, feed["filter"]):
            continue

        items.append({
            "title":   title,
            "desc":    desc[:MAX_DESC],
            "url":     link.strip(),
            "date":    date,
            "source":  feed["name"],
            "lang":    feed["lang"],
            "topic":   get_topic(title, desc, feed["name"]),
        })

    print(f"  ✓ {feed['name']}: {len(items)} статии")
    return items


def run():
    print(">>> EU-Bulgaria News — RSS синдикация")
    all_items = []
    seen_urls = set()

    for feed in FEEDS:
        items = fetch_feed(feed)
        for item in items:
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                all_items.append(item)

    # Филтър: само последните DAYS_BACK дни
    # Статии без разпозната дата се пропускат (не се третират като "най-нови").
    cutoff = (datetime.now() - timedelta(days=DAYS_BACK)).strftime('%Y-%m-%d')
    before = len(all_items)

    def is_recent(item):
        d = item.get("date") or ""
        if len(d) != 10 or d[4] != '-' or d[7] != '-':
            return False  # неразпозната/непълна дата — изключваме, не приемаме по подразбиране
        return d >= cutoff

    all_items = [i for i in all_items if is_recent(i)]
    print(f"  Филтър {DAYS_BACK} дни: {before} → {len(all_items)} статии")

    # Сортираме по дата (най-нови първи)
    all_items.sort(key=lambda x: x["date"] or "0000", reverse=True)
    all_items = all_items[:MAX_ITEMS]

    meta = {
        "updated": datetime.now().strftime('%Y-%m-%d %H:%M'),
        "count": len(all_items),
        "items": all_items,
    }

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n  Записани {len(all_items)} статии → data/eu-news.json")
    print(f"  Обновено: {meta['updated']}")


if __name__ == "__main__":
    run()
