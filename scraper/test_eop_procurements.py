"""
Офлайн тест на новия ЕОП път (файл "поръчки" от storage.eop.bg).

Не пипа мрежата и не пипа data/programs.json — работи само върху
testdata/eop_procurements_sample.json. Пусни го преди всеки push:

    python scraper/test_eop_procurements.py

Излиза с код 1 при първа неуспешна проверка, за да може да се сложи в CI.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper import (                      # noqa: E402
    _eop_money,
    _eop_date10,
    _eop_category_v2,
    parse_eop_procurements,
    enrich_from_eop_procurements,
)

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "testdata", "eop_procurements_sample.json")

_failures = []


def check(label, got, expected):
    ok = got == expected
    print(f"  {'✓' if ok else '✗'} {label}: {got!r}"
          + ("" if ok else f"  (очаквано: {expected!r})"))
    if not ok:
        _failures.append(label)


def main():
    with open(FIXTURE, encoding="utf-8") as f:
        rows = json.load(f)
    proc_map = {str(r["tenderId"]): ("2026-09-03", r) for r in rows}

    print("\n[1] Парсване на суми (българският формат с десетична запетая)")
    check("179974,75",     _eop_money("179974,75"),   179974.75)
    check("1.254.705,00",  _eop_money("1.254.705,00"), 1254705.0)
    check("500000",        _eop_money("500000"),      500000.0)
    check("нула → None",   _eop_money("0,00"),        None)
    check("празно → None", _eop_money(""),            None)
    check("None → None",   _eop_money(None),          None)
    check("боклук → None", _eop_money("н/д"),         None)

    print("\n[2] Дати")
    check("ISO с час", _eop_date10("2026-10-05T23:59:59"), "2026-10-05")
    check("None",      _eop_date10(None),                  "")
    check("къс низ",   _eop_date10("2026"),                "")

    print("\n[3] Категоризация по CPV")
    check("33 → здраве",       _eop_category_v2("нещо", "33124100", "Уреди за диагностика"), "здравеопазване")
    check("48 → ит",           _eop_category_v2("нещо", "48000000", "Софтуерни пакети"),     "ит")
    check("45 → инфраструктура", _eop_category_v2("нещо", "45242000", "Строителни работи"),  "инфраструктура")
    check("без CPV → по думи", _eop_category_v2("Ремонт на улична мрежа", "", ""),           "инфраструктура")

    print("\n[4] parse_eop_procurements")
    progs = parse_eop_procurements(proc_map, set())
    # 8 реда → 1 отменен изхвърлен, 3 обособени позиции слети в 1 → 5 записа
    check("отменената е изхвърлена и позициите са слети", len(progs), 5)
    by_id = {p["id"]: p for p in progs}

    p = by_id["ocds-e82gsb-601680"]
    check("id формат",        p["id"],        "ocds-e82gsb-601680")
    check("source непроменен", p["source"],   "ЦАИС ЕОП — Обявления")
    check("url формат",       p["url"],       "https://app.eop.bg/today/601680")
    check("срок",             p["deadline"],  "2026-09-30")
    check("стойност",         p["value"],     410880.88)
    check("валута",           p["currency"],  "EUR")
    check("CPV",              p["cpv"],       "45242000")
    check("NUTS",             p["nuts"],      "BG413")
    check("EU финансиране",   p["eu_funded"], True)
    check("EU програма",      p["eu_program"], "2021BG16FFPR003 - Развитие на регионите 2021-2027")
    check("възложител ЕИК",   p["buyer_id"],  "000024745")
    check("категория",        p["category"],  "инфраструктура")

    check("всички имат срок",     all(x["deadline"] for x in progs), True)
    check("всички имат стойност", all("value" in x for x in progs),  True)
    check("всички имат CPV",      all("cpv" in x for x in progs),    True)

    print("\n[4б] Обособените позиции стават ЕДИН запис на поръчка")
    lots = [p for p in progs if p.get("procurement_no") == "00276-2026-0020"]
    check("една поръчка, не три",   len(lots),          1)
    check("канонично id = най-малък tenderId", lots[0]["id"], "ocds-e82gsb-529894")
    check("брой позиции",           lots[0]["lots"],    3)
    check("сумирана стойност",      lots[0]["value"],   1554705.0)
    check("останалите нямат lots",
          [p["id"] for p in progs if p.get("lots") and p is not lots[0]], [])

    print("\n[5] Задължителните стари полета присъстват навсякъде")
    required = {"id", "title", "source", "category", "url",
                "deadline", "type", "authority", "found_at", "code"}
    missing = [x["id"] for x in progs if not required.issubset(x)]
    check("без липсващи стари полета", missing, [])
    check("type е tender", {x["type"] for x in progs}, {"tender"})

    print("\n[6] Дедупликация срещу вече съществуващи id-та")
    again = parse_eop_procurements(proc_map, {p["id"] for p in progs})
    check("нищо не се дублира", again, [])
    # ако в базата стои ПОЗИЦИЯ (не каноничният ред), поръчката пак се
    # смята за представена — иначе щеше да се добави втори запис
    only_lot = parse_eop_procurements(proc_map, {"ocds-e82gsb-529896"})
    check("позиция в базата спира повторното добавяне",
          [p["id"] for p in only_lot if p.get("procurement_no") == "00276-2026-0020"], [])

    print("\n[7] Обогатяване на стар запис (както изглежда днес в programs.json)")
    old = [{
        "id": "ocds-e82gsb-601680",
        "title": "Реконструкция на фонтан в УПИ VII, кв. 52 по плана на гр. Гоце Делчев",
        "source": "ЦАИС ЕОП — Обявления",
        "category": "търгове",
        "url": "https://app.eop.bg/today/601680",
        "deadline": "",
        "type": "tender",
        "authority": "ОБЩИНА ГОЦЕ ДЕЛЧЕВ",
        "found_at": "2026-09-03",
        "code": "601680",
    }, {
        "id": "BG14MFPR001-2.014",
        "title": "Фонд, който не бива да се пипа",
        "source": "ИСУН 2020 — Отворени процедури",
        "category": "земеделие",
        "deadline": "",
        "type": "fund",
        "found_at": "2026-08-31",
    }]
    n_enriched, n_dl = enrich_from_eop_procurements(old, proc_map)
    check("обогатен 1 запис",   n_enriched,       1)
    check("коригиран 1 срок",   n_dl,             1)
    check("срокът е попълнен",  old[0]["deadline"], "2026-09-30")
    check("стойността е добавена", old[0]["value"], 410880.88)
    check("фондът е непокътнат", old[1], {
        "id": "BG14MFPR001-2.014",
        "title": "Фонд, който не бива да се пипа",
        "source": "ИСУН 2020 — Отворени процедури",
        "category": "земеделие",
        "deadline": "",
        "type": "fund",
        "found_at": "2026-08-31",
    })

    print("\n[8] Липсващи данни не чупят нищо")
    check("празен вход", parse_eop_procurements({}, set()), [])
    check("запис без subject",
          parse_eop_procurements({"1": ("2026-09-03", {"tenderId": 1})}, set()), [])
    n, d = enrich_from_eop_procurements([], {})
    check("празен списък за обогатяване", (n, d), (0, 0))

    print()
    if _failures:
        print(f"ПАДНАЛИ ПРОВЕРКИ ({len(_failures)}): " + ", ".join(_failures))
        return 1
    print("Всички проверки минаха.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
