import json
from datetime import date

with open('../data/programs.json', encoding='utf-8') as f:
    programs = json.load(f)

today = date.today()
with_dl = [p for p in programs if p.get('deadline')]
with_dl.sort(key=lambda p: p['deadline'])

print(f'Общо активни: {len(programs)}')
print(f'С краен срок: {len(with_dl)}')
print()
print('--- Изтичат до 30 дни ---')
found = 0
for p in with_dl:
    try:
        dl = date.fromisoformat(p['deadline'])
        days = (dl - today).days
        if 0 <= days <= 30:
            print(f'{days:2}д | {p["deadline"]} | {p["source"][:18]:18} | {p["title"][:55]}')
            found += 1
    except:
        pass

if found == 0:
    print('Няма програми с краен срок до 30 дни.')
