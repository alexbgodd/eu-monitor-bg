"""Добавя ИСУН 2020 процедури в programs.json."""
import json, os

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'programs.json')

ISUN_PROGRAMS = [
    {"id": "BG05SFPR001-1.002", "title": "Достъп до образование за всяко дете", "source": "ИСУН 2020", "category": "образование", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG05SFPR001-1.002", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG05SFPR001-1.002"},
    {"id": "BG05SFPR001-1.009", "title": "Достъп до образование чрез преодоляване на демографски, социални и културни бариери", "source": "ИСУН 2020", "category": "образование", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG05SFPR001-1.009", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG05SFPR001-1.009"},
    {"id": "BG05SFPR001-1.012", "title": "Комплексни програми за десегрегация на училищата и против дискриминацията", "source": "ИСУН 2020", "category": "образование", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG05SFPR001-1.012", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG05SFPR001-1.012"},
    {"id": "BG05SFPR001-2.005", "title": "Подкрепа за ученици с таланти-2", "source": "ИСУН 2020", "category": "образование", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG05SFPR001-2.005", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG05SFPR001-2.005"},
    {"id": "BG05SFPR001-3.003", "title": "Достъп на уязвими групи и непедагогически персонал до висше образование", "source": "ИСУН 2020", "category": "образование", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG05SFPR001-3.003", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG05SFPR001-3.003"},
    {"id": "BG05SFPR001-3.010", "title": "Развитие на дуалната система на обучение в ПОО", "source": "ИСУН 2020", "category": "образование", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG05SFPR001-3.010", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG05SFPR001-3.010"},
    {"id": "BG05SFPR002-1.024", "title": "Активиране, обучение и заетост на безработни и неактивни лица", "source": "ИСУН 2020", "category": "социални", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG05SFPR002-1.024", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG05SFPR002-1.024"},
    {"id": "BG05SFPR002-1.025", "title": "Нови подходи за насърчаване на ученето през целия живот в България", "source": "ИСУН 2020", "category": "социални", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG05SFPR002-1.025", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG05SFPR002-1.025"},
    {"id": "BG05SFPR002-1.029", "title": "Подкрепа за активен живот на възрастните хора в пенсионна възраст", "source": "ИСУН 2020", "category": "социални", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG05SFPR002-1.029", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG05SFPR002-1.029"},
    {"id": "BG05SFPR002-1.030", "title": "Развитие на предприемачеството и социалната икономика", "source": "ИСУН 2020", "category": "социални", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG05SFPR002-1.030", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG05SFPR002-1.030"},
    {"id": "BG05SFPR002-1.034", "title": "Подобряване на уменията на заетите и условията на труд в предприятията", "source": "ИСУН 2020", "category": "социални", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG05SFPR002-1.034", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG05SFPR002-1.034"},
    {"id": "BG05SFPR002-2.014", "title": "Подкрепа за деца и семейства по подхода ИТИ", "source": "ИСУН 2020", "category": "социални", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG05SFPR002-2.014", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG05SFPR002-2.014"},
    {"id": "BG05SFPR002-2.015", "title": "Интеграция на маргинализирани общности, достъп до здравеопазване и подкрепа на уязвими групи", "source": "ИСУН 2020", "category": "социални", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG05SFPR002-2.015", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG05SFPR002-2.015"},
    {"id": "BG14MFPR001-1.001", "title": "Контрол и правоприлагане (Морско дело и рибарство)", "source": "ИСУН 2020", "category": "земеделие", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG14MFPR001-1.001", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG14MFPR001-1.001"},
    {"id": "BG14MFPR001-1.002", "title": "Събиране и обработване на данни за управление на рибарството и аквакултурите", "source": "ИСУН 2020", "category": "земеделие", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG14MFPR001-1.002", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG14MFPR001-1.002"},
    {"id": "BG14MFPR001-4.001", "title": "Морско наблюдение", "source": "ИСУН 2020", "category": "земеделие", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG14MFPR001-4.001", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG14MFPR001-4.001"},
    {"id": "BG16FFPR002-1.008", "title": "Подкрепа за актуализирането на ПУРБ в Черноморски район 2028-2033", "source": "ИСУН 2020", "category": "екология", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG16FFPR002-1.008", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG16FFPR002-1.008"},
    {"id": "BG16FFPR002-2.005", "title": "Рекултивация на регионални депа за битови отпадъци - втора", "source": "ИСУН 2020", "category": "екология", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG16FFPR002-2.005", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG16FFPR002-2.005"},
    {"id": "BG16FFPR002-3.017", "title": "Изпълнение на мярка 71 от Националната рамка за приоритетни действия за Натура 2000", "source": "ИСУН 2020", "category": "екология", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG16FFPR002-3.017", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG16FFPR002-3.017"},
    {"id": "BG16FFPR002-3.019", "title": "Изпълнение на мерки 26, 29, 33 и 60 от Националната рамка за Натура 2000", "source": "ИСУН 2020", "category": "екология", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG16FFPR002-3.019", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG16FFPR002-3.019"},
    {"id": "BG16FFPR002-3.020", "title": "Осигуряване на условия за опазване на застрашени видове ex situ", "source": "ИСУН 2020", "category": "екология", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG16FFPR002-3.020", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG16FFPR002-3.020"},
    {"id": "BG16FFPR002-3.024", "title": "Информационни кампании - Биологично разнообразие", "source": "ИСУН 2020", "category": "екология", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG16FFPR002-3.024", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG16FFPR002-3.024"},
    {"id": "BG16FFPR002-3.026", "title": "Подкрепа за спасителни центрове", "source": "ИСУН 2020", "category": "екология", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG16FFPR002-3.026", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG16FFPR002-3.026"},
    {"id": "BG16FFPR003-1.001", "title": "Подкрепа за интегрирано градско развитие в 10-те градски общини", "source": "ИСУН 2020", "category": "общини", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG16FFPR003-1.001", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG16FFPR003-1.001"},
    {"id": "BG16FFPR003-2.002", "title": "Подкрепа за интегрирано градско развитие в 40 градски общини", "source": "ИСУН 2020", "category": "общини", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG16FFPR003-2.002", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG16FFPR003-2.002"},
    {"id": "BG16FFPR003-2.004", "title": "Подкрепа за интегрирано градско развитие в 40 градски общини - 2", "source": "ИСУН 2020", "category": "общини", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG16FFPR003-2.004", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG16FFPR003-2.004"},
    {"id": "BG16RFPR001-3.004", "title": "Зарядна инфраструктура за електрически превозни средства по пътищата - втора", "source": "ИСУН 2020", "category": "общи", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG16RFPR001-3.004", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG16RFPR001-3.004"},
    {"id": "BG16RFPR001-4.001", "title": "Интермодалност в градски условия", "source": "ИСУН 2020", "category": "общи", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG16RFPR001-4.001", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG16RFPR001-4.001"},
    {"id": "BG16RFPR002-1.011", "title": "Участие на български организации в институционализирани европейски партньорства", "source": "ИСУН 2020", "category": "бизнес", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG16RFPR002-1.011", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG16RFPR002-1.011"},
    {"id": "BG16RFPR002-1.020", "title": "Допълващо финансиране по програма Цифрова Европа", "source": "ИСУН 2020", "category": "бизнес", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG16RFPR002-1.020", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG16RFPR002-1.020"},
    {"id": "BG16RFPR002-2.017", "title": "Изграждане на Правителствен комуникационен център за сигурни сателитни комуникации", "source": "ИСУН 2020", "category": "бизнес", "url": "https://eumis2020.government.bg/bg/s/Procedure/Details/BG16RFPR002-2.017", "deadline": "", "found_at": "2026-06-27 19:21", "code": "BG16RFPR002-2.017"},
]

with open(DATA_FILE, 'r', encoding='utf-8') as f:
    existing = json.load(f)

existing_ids = {p['id'] for p in existing}
added = 0
for p in ISUN_PROGRAMS:
    if p['id'] not in existing_ids:
        existing.append(p)
        added += 1

with open(DATA_FILE, 'w', encoding='utf-8') as f:
    json.dump(existing, f, ensure_ascii=False, indent=2)

print(f"Добавени: {added} ИСУН програми. Общо: {len(existing)}")
