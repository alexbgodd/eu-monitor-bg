"""
Еднократно обогатяване на СЪЩЕСТВУВАЩИТЕ ЕОП записи в data/programs.json
с официалните данни от файла "поръчки" на storage.eop.bg:
срок, стойност, CPV + описание, NUTS регион, EU програма.

По подразбиране НЕ пипа файла — само показва какво би се променило:

    python scraper/backfill_eop.py                # само отчет (dry-run)
    python scraper/backfill_eop.py --days 120     # по-дълъг период назад
    python scraper/backfill_eop.py --apply        # записва + прави .bak копие

Записът с --apply прави резервно копие data/programs.json.bak преди да пише.
Скриптът НЕ трие изтекли записи — това остава работа на scraper.py.
"""
import argparse
import json
import os
import shutil
import sys
from collections import Counter
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper import (                      # noqa: E402
    DATA_FILE,
    fetch_eop_procurements,
    enrich_from_eop_procurements,
)


def stats(programs):
    eop = [p for p in programs if "ЕОП" in str(p.get("source", ""))]
    return {
        "ЕОП записи":     len(eop),
        "със срок":       sum(1 for p in eop if p.get("deadline")),
        "със стойност":   sum(1 for p in eop if p.get("value") is not None),
        "с CPV":          sum(1 for p in eop if p.get("cpv")),
        "с NUTS":         sum(1 for p in eop if p.get("nuts")),
        "по ЕС програма": sum(1 for p in eop if p.get("eu_funded")),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90,
                    help="колко дни назад да се четат файловете (по подр. 90)")
    ap.add_argument("--apply", action="store_true",
                    help="наистина запиши промените (иначе само отчет)")
    args = ap.parse_args()

    path = os.path.abspath(DATA_FILE)
    if not os.path.exists(path):
        print(f"Няма файл {path}")
        return 1
    with open(path, encoding="utf-8") as f:
        programs = json.load(f)

    before = stats(programs)
    print(f"Файл: {path}\nЗаписи общо: {len(programs)}\n")
    print("ПРЕДИ:")
    for k, v in before.items():
        print(f"  {k:16s} {v}")

    print(f"\nЧета файловете 'поръчки' за последните {args.days} дни "
          f"(това отнема няколко минути)...")
    proc_map = fetch_eop_procurements(days_back=args.days, quiet=True)
    print(f"Заредени {len(proc_map)} уникални поръчки от storage.eop.bg")
    if not proc_map:
        print("Няма данни — нищо не се променя.")
        return 1

    n_enriched, n_dl = enrich_from_eop_procurements(programs, proc_map)
    after = stats(programs)

    print("\nСЛЕД:")
    for k, v in after.items():
        delta = v - before[k]
        print(f"  {k:16s} {v}" + (f"   ({delta:+d})" if delta else ""))
    print(f"\nОбогатени записи: {n_enriched} · коригирани срокове: {n_dl}")

    # Колко ще отпаднат при следващото пускане на scraper.py заради
    # вече истинския краен срок — важно е да се види ПРЕДИ да се запише.
    today = date.today()
    expiring = [p for p in programs
                if p.get("type") == "tender" and p.get("deadline")
                and p["deadline"][:10] < today.isoformat()]
    print(f"\nВНИМАНИЕ: {len(expiring)} записа вече имат изтекъл срок и "
          f"ще бъдат премахнати от следващото пускане на scraper.py.")
    if expiring:
        cats = Counter(p.get("category", "?") for p in expiring)
        print("  по категории: " + ", ".join(f"{k} {v}" for k, v in cats.most_common(6)))
        print("  примери:")
        for p in expiring[:3]:
            print(f"    · {p['deadline']}  {p['title'][:70]}")

    if not args.apply:
        print("\n[dry-run] Нищо не е записано. Пусни със --apply, за да запишеш.")
        return 0

    backup = path + ".bak"
    shutil.copy2(path, backup)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(programs, ensure_ascii=False, indent=2))
    print(f"\nЗаписано. Резервно копие: {backup}")
    print("Върни назад при нужда:  copy data\\programs.json.bak data\\programs.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
