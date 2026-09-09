"""
Слива обособените позиции на една и съща обществена поръчка в ЕДИН запис.

ЦАИС публикува всяка обособена позиция като отделен ред с отделен tenderId,
но с общ uniqueProcurementNumber. Затова поръчка с 50 позиции влизаше като
50 записа — в потока и в имейла (случи се при първото пускане на 09.09.2026).
scraper.py вече групира при внасяне; този скрипт чисти вече записаното.

    python scraper/dedupe_eop.py            # само отчет (dry-run)
    python scraper/dedupe_eop.py --apply    # записва + прави .bak копие

Правило за оставащия запис: този с най-малък tenderId в групата — същото,
което ползва scraper.py, за да не се появи пак при следващото пускане.
Стойностите на позициите се сумират в общата стойност на поръчката.
"""
import argparse
import json
import os
import re
import shutil
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper import DATA_FILE                      # noqa: E402


def _norm(text):
    return re.sub(r"[^\w]+", " ", str(text or "").lower()).strip()


def group_key(p):
    """Първо по официалния номер на поръчката; иначе по възложител + заглавие."""
    no = str(p.get("procurement_no") or "").strip()
    if no:
        return ("no", no)
    return ("t", _norm(p.get("authority"))[:60], _norm(p.get("title"))[:120])


def tid_of(p):
    code = str(p.get("code") or "")
    if code.isdigit():
        return int(code)
    tail = str(p.get("id", "")).rsplit("-", 1)[-1]
    return int(tail) if tail.isdigit() else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="запиши промените")
    args = ap.parse_args()

    path = os.path.abspath(DATA_FILE)
    with open(path, encoding="utf-8") as f:
        programs = json.load(f)

    eop, others = [], []
    for p in programs:
        (eop if "ЕОП" in str(p.get("source", "")) else others).append(p)

    groups = defaultdict(list)
    for p in eop:
        groups[group_key(p)].append(p)

    dupes = {k: v for k, v in groups.items() if len(v) > 1}
    print(f"Файл: {path}")
    print(f"Записи общо: {len(programs)} · ЕОП: {len(eop)}")
    print(f"Поръчки с повече от един запис: {len(dupes)}")
    print(f"Излишни записи за сливане: {sum(len(v) for v in dupes.values()) - len(dupes)}")

    if dupes:
        top = sorted(dupes.items(), key=lambda kv: -len(kv[1]))[:5]
        print("\nНай-разпокъсаните поръчки:")
        for _, rows in top:
            print(f"  {len(rows):3d} записа · {rows[0]['title'][:66]}")
        by_key_type = Counter(k[0] for k in dupes)
        print(f"\n  групирани по официален номер: {by_key_type.get('no', 0)}"
              f" · по заглавие+възложител: {by_key_type.get('t', 0)}")

    kept = []
    for rows in groups.values():
        rows.sort(key=tid_of)
        winner = rows[0]
        if len(rows) > 1:
            winner["lots"] = len(rows)
            total, found = 0.0, False
            for r in rows:
                v = r.get("value")
                if isinstance(v, (int, float)):
                    total += v
                    found = True
            if found:
                winner["value"] = round(total, 2)
            # най-ранната дата на намиране запазва реда в потока
            winner["found_at"] = min(r.get("found_at", "") for r in rows if r.get("found_at")) \
                or winner.get("found_at", "")
        kept.append(winner)

    result = others + kept
    print(f"\nСлед сливане: {len(result)} записа "
          f"({len(programs)} → {len(result)}, -{len(programs) - len(result)})")

    if not args.apply:
        print("\n[dry-run] Нищо не е записано. Пусни със --apply, за да запишеш.")
        return 0

    backup = path + ".dedupe.bak"
    shutil.copy2(path, backup)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nЗаписано. Резервно копие: {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
