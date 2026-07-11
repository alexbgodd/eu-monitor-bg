import json

with open('../data/programs.json', encoding='utf-8') as f:
    programs = json.load(f)

remove_exact = [
    'Индикативна годишна работна програма (ИГРП) на ПНИИДИТ',
    'Изпълнение на програмата',
    'Линк към Програмата',
    'Индикативни годишни работни програми',
    'Отворени процедури',
    'Процедури за избор на изпълнител',
    'Финансиране в област "Вътрешни работи" 2021-2027',
    'ИНОВАЦИИ И РАСТЕЖ',
    'Политики и програми',
    'Схеми и мерки',
    'Активни програми',
]
remove_contains = ['2014-2020', 'е част от Европейския университетски']

before = len(programs)
kept = []
for p in programs:
    t = p['title']
    if t in remove_exact:
        continue
    if any(w in t for w in remove_contains):
        continue
    kept.append(p)

print(f'Премахнати: {before - len(kept)}, остават: {len(kept)}')
with open('../data/programs.json', 'w', encoding='utf-8') as f:
    json.dump(kept, f, ensure_ascii=False, indent=2)
