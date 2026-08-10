"""
Изчиства шумните записи от Министерство на културата (меню и архив),
влезли при първия scrape с новия URL — 01.08.2026.

Ползва mc_is_valid() от scraper.py (единен източник на истина).
Пускане: python clean_mc.py            (dry run)
         python clean_mc.py --apply
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from scraper import mc_is_valid

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'programs.json')
SOURCE = "Министерство на културата"


def main():
    apply = '--apply' in sys.argv

    with open(DATA_FILE, encoding='utf-8') as f:
        programs = json.load(f)

    keep, drop = [], []
    for p in programs:
        if p.get('source') == SOURCE and not mc_is_valid(p.get('title', '')):
            drop.append(p)
        else:
            keep.append(p)

    mc_kept = [p for p in keep if p.get('source') == SOURCE]
    print(f"МК записи: {len(drop) + len(mc_kept)} → остават {len(mc_kept)}, махат се {len(drop)}\n")
    print("ОСТАВАТ:")
    for p in mc_kept:
        print(f"  ✓ {p['title'][:90]}")
    print("\nМАХАТ СЕ:")
    for p in drop:
        print(f"  ✗ {p['title'][:90]}")

    if apply:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            f.write(json.dumps(keep, ensure_ascii=False, indent=2))
            f.truncate()
        print(f"\n✓ Записано. Общо активни: {len(keep)}")
    else:
        print(f"\nDry run — нищо не е записано. Пусни с --apply.")


if __name__ == '__main__':
    main()
