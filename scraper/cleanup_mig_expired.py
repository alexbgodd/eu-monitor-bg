"""
Премахва изтекли МИГ/ПНИИДИТ записи от programs.json.
Проверява всяка страница за текста "изтекъл срок за кандидатстване".

Пусни: python cleanup_mig_expired.py
"""
import json, os, requests, urllib3
urllib3.disable_warnings()

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'programs.json')

MIG_SOURCES = {
    'Министерство на иновациите и растежа',
    'ПНИИДИТ — Иновации и дигитализация'
}

def is_expired(url):
    try:
        r = requests.get(url, timeout=10, verify=False,
                         headers={'User-Agent': 'Mozilla/5.0'})
        return 'изтекъл срок за кандидатстване' in r.text.lower()
    except Exception:
        return False

def main():
    with open(DATA_FILE, encoding='utf-8') as f:
        programs = json.loads(f.read().rstrip('\x00'))

    to_check = [p for p in programs
                if p.get('source') in MIG_SOURCES and p.get('url', '').startswith('http')]

    print(f'Проверяваме {len(to_check)} МИГ/ПНИИДИТ записа...\n')

    expired_urls = set()
    for p in to_check:
        url = p['url']
        title = p['title'][:65]
        if is_expired(url):
            expired_urls.add(url)
            print(f'  ❌ ИЗТЕКЪЛ: {title}')
        else:
            print(f'  ✅ Активен: {title}')

    before = len(programs)
    programs = [p for p in programs if p.get('url') not in expired_urls]
    after = len(programs)

    data = json.dumps(programs, ensure_ascii=False, indent=2)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        f.write(data)
        f.truncate()

    print(f'\nПремахнати: {before - after} изтекли. Останали: {after} програми.')

if __name__ == '__main__':
    main()
