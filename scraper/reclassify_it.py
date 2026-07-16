"""
Еднократен скрипт: прекатегоризира вече съществуващи записи с category="бизнес",
които реално са ИТ/дигитални/софтуерни, към category="ит".

Причина: get_category() / _eop_category() в scraper.py допускаха дигитал/софтуер
ключови думи да падат в "бизнес" вместо "ит" — вече е оправено за НОВИ записи,
но старите вече записани програми трябва да се минат ръчно веднъж.

Стартирай: cd scraper && python reclassify_it.py
"""

import json
import os

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'programs.json')

IT_KEYWORDS = [
    'дигитал', 'цифров', 'софтуер', 'информационна система', 'информационни технологии',
    'информационно-технологичн', 'киберсигурност', 'ит систем', 'кибер сигурност',
]

def main():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        programs = json.load(f)

    changed = 0
    examples = []
    for p in programs:
        if p.get('category') != 'бизнес':
            continue
        title = (p.get('title') or '').lower()
        if any(kw in title for kw in IT_KEYWORDS):
            p['category'] = 'ит'
            changed += 1
            if len(examples) < 15:
                examples.append(p.get('title', '')[:80])

    if changed:
        data = json.dumps(programs, ensure_ascii=False, indent=2)
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            f.write(data)
            f.truncate()

    print(f"Прекатегоризирани {changed} записа от 'бизнес' -> 'ит'.")
    if examples:
        print("\nПримери:")
        for e in examples:
            print(f"  - {e}")

if __name__ == '__main__':
    main()
