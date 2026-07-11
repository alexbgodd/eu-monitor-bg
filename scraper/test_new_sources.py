"""
Тест на нови потенциални източници — пуска се локално преди добавяне в scraper.py
cd scraper && python test_new_sources.py
"""
import requests
from bs4 import BeautifulSoup
import urllib3
import ssl
urllib3.disable_warnings()

# Fix за стари BG правителствени сайтове с weak DH ключ
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

class WeakSSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context(ciphers="DEFAULT:@SECLEVEL=1")
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = ctx
        super().init_poolmanager(*args, **kwargs)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0'
}

CANDIDATES = [
    {
        "name": "EEA Grants — България",
        "url": "https://eeagrants.org/countries/bulgaria",
        "keywords": ["grant", "call", "fund", "open", "programme", "финансир", "покан", "грант"]
    },
    {
        "name": "Активни граждани — Покани",
        "url": "https://activecitizensfund.bg/pokani/",
        "keywords": ["покан", "програм", "финансир", "грант", "конкурс", "кандидатстван"]
    },
    {
        "name": "America for Bulgaria — Грантове",
        "url": "https://www.americaforbulgaria.org/bg/grants",
        "keywords": ["грант", "покан", "финансир", "кандидатстван", "програм", "конкурс"]
    },
    {
        "name": "LIFE програма МОСВ",
        "url": "https://www.moew.government.bg/bg/ministerstvo/programi-i-proekti/programa-life/",
        "keywords": ["покан", "програм", "финансир", "грант", "конкурс", "процедур"]
    },
]

def test_source(src):
    print(f"\n{'='*60}")
    print(f"Тест: {src['name']}")
    print(f"URL:  {src['url']}")
    try:
        session = requests.Session()
        if src.get('weak_ssl'):
            session.mount('https://', WeakSSLAdapter())
            r = session.get(src['url'], headers=HEADERS, timeout=15)
        else:
            r = session.get(src['url'], headers=HEADERS, timeout=15, verify=False)
        print(f"Статус: {r.status_code}")
        if r.status_code != 200:
            print("  ✗ Неуспешно")
            return
        soup = BeautifulSoup(r.text, 'html.parser')
        # Намери всички линкове с keywords
        found = []
        seen = set()
        for a in soup.select('a'):
            text = a.get_text(strip=True)
            href = a.get('href', '')
            if not text or len(text) < 15 or len(text) > 200:
                continue
            if text in seen:
                continue
            if any(w in text.lower() for w in src['keywords']):
                seen.add(text)
                found.append((text, href))
        print(f"Намерени линкове с ключови думи: {len(found)}")
        for title, href in found[:15]:
            print(f"  - {title[:80]}")
            print(f"    {href[:80]}")
    except Exception as e:
        print(f"  ✗ Грешка: {e}")

if __name__ == "__main__":
    for src in CANDIDATES:
        test_source(src)
    print(f"\n{'='*60}")
    print("Готово! Покажи изхода — добавяме само работещите.")
