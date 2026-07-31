"""
Еднократна прекатегоризация: отделя "здравеопазване" от "социални"/"търгове"/"общи"
в съществуващите записи на data/programs.json.

Ползва СЪЩАТА _is_health() логика като scraper.py (единен източник на истина):
STRONG думи винаги печелят; WEAK думи се броят само без EXCLUDE дума.

Пускане: python reclassify_health.py           (dry run — само показва)
         python reclassify_health.py --apply   (записва промените)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from scraper import _is_health, _HEALTH_STRONG

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'programs.json')

# Прекатегоризираме само от тези категории (не пипаме ит/бизнес/земеделие и т.н.)
FROM_CATEGORIES = {"социални", "търгове", "общи"}


def main():
    apply = '--apply' in sys.argv

    with open(DATA_FILE, encoding='utf-8') as f:
        programs = json.load(f)

    changed = []
    for p in programs:
        cat = p.get('category')
        if cat == 'здравеопазване':
            continue
        title = p.get('title', '')
        t = title.lower()
        # Силна здравна дума → прекатегоризирай от ВСЯКА категория.
        # Слаба (болница като контекст) → само от широките категории.
        strong = any(w in t for w in _HEALTH_STRONG)
        if strong or (cat in FROM_CATEGORIES and _is_health(title)):
            changed.append((cat, title[:80]))
            p['category'] = 'здравеопазване'

    print(f"Записи за прекатегоризация към 'здравеопазване': {len(changed)}\n")
    for old_cat, title in changed[:60]:
        print(f"  [{old_cat}] {title}")
    if len(changed) > 60:
        print(f"  ... и още {len(changed) - 60}")

    if apply:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            f.write(json.dumps(programs, ensure_ascii=False, indent=2))
            f.truncate()
        print(f"\n✓ Записано в programs.json.")
    else:
        print(f"\nDry run — нищо не е записано. Пусни с --apply за да запишеш.")


if __name__ == '__main__':
    main()
