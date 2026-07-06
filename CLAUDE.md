# CLAUDE.md — Second Brain: eu-monitor-bg

> Чети този файл в началото на всяка нова сесия за пълен контекст на проекта.

---

## Какво е проектът

**ОП + Фондове БГ** — безплатен имейл alert сервиз за обществени поръчки и EU финансиране в България.
- URL: https://tools.gdprcheck.bg
- Домейн: tools.gdprcheck.bg (subdomain на gdprcheck.bg)
- Хостинг: Vercel (free tier)
- Репо: C:\Users\User\eu-monitor-bg

---

## Архитектура

```
eu-monitor-bg/
├── api/
│   ├── register.py          # POST /api/register → записва в Supabase
│   └── unsubscribe.py       # GET /unsubscribe?email=&token= → изтрива от Supabase
├── scraper/
│   ├── scraper.py           # Главен scraper — 13+ източници
│   ├── matcher.py           # Matching потребители ↔ програми по категория
│   ├── send_alerts.py       # Изпращане на имейли (Resend API)
│   ├── blast_existing.py    # Еднократен blast към съществуващи абонати
│   ├── generate_seo_pages.py # Генерира institucii/*.html SEO страници
│   ├── check_deadlines.py   # Анализ на крайни срокове в programs.json
│   └── scrape_eu_news.py    # RSS агрегатор за новини (нов — юли 2026)
├── data/
│   ├── programs.json        # ~906 активни програми и поръчки
│   └── eu-news.json         # Последни новини (2 дни, ~46 статии)
├── web/
│   ├── index.html           # Начална страница
│   ├── programs.html        # Списък с всички програми
│   ├── eu-news.html         # Новини страница (/eu-news)
│   ├── privacy.html         # Политика за поверителност
│   ├── style.css            # Главен CSS
│   ├── script.js            # JS за регистрация
│   ├── water.min.css        # Base CSS library
│   └── institucii/          # SEO страници по институция
├── vercel.json              # Routing + headers + builds
├── CLAUDE.md                # Този файл
└── .env                     # НЕ СЕ COMMIT-ВА — само локално
```

---

## .env променливи

```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SECRET_KEY=eyJ...           # service_role ключ
RESEND_API_KEY=re_...
UNSUBSCRIBE_SECRET=random_string     # за HMAC токени при unsubscribe
```

**.env е в .gitignore — никога не се commit-ва.**

---

## Supabase

- Таблица: `registrations`
- Колони: `id, email, name, org_type, interests (text[]), created_at`
- ~4 записа (2 реални, 2 тестови) към юли 2026
- Python достъп: директни REST API заявки с `urllib.request` (без supabase-py)

---

## Scraper — източници (scraper.py)

13+ активни източници:

| Badge | Източник | Parser |
|-------|----------|--------|
| EU | ИСУН 2020 — EU процедури | `isun` |
| ОП | ЦАИС ЕОП — Поръчки | `eop` |
| МИ | Мин. на иновациите | `mi` |
| ДФЗ | Държавен фонд Земеделие | `dfz` |
| ЕСФ | ЕСФ България | `esf` |
| ЕР | ЦРЧР — Еразъм+ | `erasmus` |
| МК | Министерство на културата | `kultura` |
| НФК | Национален фонд Култура | `nfk` |
| НПО | НПО Портал (ngobg.info) | `ngobg` |
| ПНИИДИТ | ПНИИДИТ | `pniidit` |
| ЕОП | ЦАИС ЕОП — Обявления | `eop_notices` |
| ФНИ | Фонд Научни изследвания (fni.bg) | `fni` |

**ВАЖНО: ИСУН не се премахва — дава най-много резултати.**

### Мъртви sources за programs (не добавяй без проверка)
- cedesk.bg — DNS не резолвира
- auer.bg — DNS не резолвира

### CATEGORY_MAP (matcher.py)

```python
{
  "бизнес":      ["иновац", "дигитал", "конкурентоспособ", "предприят"],
  "земеделие":   ["земедел", "рибарств", "аквакулт", "морско"],
  "култура":     ["култур", "изкуств", "театър", "музей", "филм"],
  "социални":    ["социал", "заетост", "труд", "здрав", "деца"],
  "образование": ["образован", "обучен", "училищ", "висше"],
  "туризъм":     ["туризъм", "хотел", "курорт"],
  "екология":    ["околна среда", "природ", "натура", "води"],
  "ит":          ["информацион", "технолог", "софтуер", "цифров"],
  "общини":      ["общин", "регион", "градск", "инфраструктур"],
}
```

---

## EU Новини — scrape_eu_news.py (нов юли 2026)

### Активни RSS sources

| Източник | URL | Език | Филтър |
|----------|-----|------|--------|
| Google News BG | news.google.com/rss/search?q=EU+финансиране+България | bg | няма |
| Google News EN | news.google.com/rss/search?q=EU+Bulgaria+funding+grants | en | няма |
| European Commission | ec.europa.eu/commission/presscorner/api/rss | en | bulgar, cohesion, structural |
| Dnevnik.bg | dnevnik.bg/rss/ | bg | ес, европейски, еврофонд... |
| Capital.bg | capital.bg/rss/ | bg | ес, европейски, еврофонд... |
| Investor.bg | investor.bg/rss/news | bg | ес, европейски, еврофонд... |

### Мъртви sources (не добавяй отново без проверка)
- TED europa.eu — URL е сменен, 404
- БТА bta.bg — malformed XML, 0 резултата
- Mediapool.bg — 404
- Euractiv — 403 (блокира ботове)
- EU Parliament rss — 404

### Настройки
- `DAYS_BACK = 2` — само последните 2 дни
- `MAX_ITEMS = 200` (реално ~40-60 след date филтър)
- Категории: `eu` (EU за България) / `вътрешни`
- Категоризация: по ключови думи в `get_topic()`

### Изход
- Записва в `data/eu-news.json`
- Формат: `{ updated, count, items: [{title, desc, url, date, source, lang, topic}] }`

---

## Vercel routing (vercel.json)

```json
/eu-news     → web/eu-news.html
/programs    → web/programs.html
/privacy     → web/privacy.html
/unsubscribe → api/unsubscribe.py
/institucii/:slug → web/institucii/:slug.html
/            → web/index.html
```

**CSP header:** `connect-src 'self' https://*.supabase.co`
→ Ако добавяш нов external fetch от JS, трябва да се добави тук.

**Vercel Analytics:** `<script defer src="/_vercel/insights/script.js"></script>` — вече е добавен в index.html, programs.html, eu-news.html.

---

## Дизайн токени

```css
--blue-dark:   #1d4ed8   /* header, primary */
--blue-mid:    #2563eb   /* links, buttons */
--blue-hero:   #1e40af   /* hero gradient */
--red-news:    #c0392b   /* новини банер */
--gray-text:   #1e293b
--gray-sub:    #64748b
--bg-light:    #f8fafc
```

**Logo:** `.logo-box` — glassmorphism рамка, кликаема, линк към `/`

**Hero stat counter:** динамичен — JS чете programs.json и обновява "906+"

**Категории с брояч:** секция между hero и "Как работи" — pills по категория с брой

**FAQ:** `<details>/<summary>` accordion — 5 въпроса, нулев JS риск

---

## Homepage структура (index.html)

1. Header (logo-box)
2. Hero (h1 + stats + бутони: Programs + **Новини банер**)
3. Категории с брояч (динамично от programs.json)
4. "Как работи" (3 стъпки)
5. Email preview mock
6. **Новини банер** → /eu-news (червен, между email preview и "Следим в реално време")
7. "Следим в реално време" (sources list)
8. FAQ (details/summary)
9. Регистрационна форма
10. Footer

---

## Workflow — нов scrape

```powershell
cd C:\Users\User\eu-monitor-bg\scraper
python scraper.py          # scrape всички програми → programs.json
python scrape_eu_news.py   # scrape новини → eu-news.json
cd ..
git add data/
git commit -m "chore: scrape update $(date)"
git push
```

**Важно:** `git pull` преди да започваш работа — избягва diverged history.

---

## Unsubscribe система

- URL: `/unsubscribe?email=X&token=Y`
- Token: HMAC-SHA256 на email с `UNSUBSCRIBE_SECRET`
- Контакт email в error съобщения: `info@gdprcheck.bg`
- При успех: изтрива от Supabase registrations таблицата

---

## SEO

- Google verification: `/googleaf2fb16ab37a2df7.html`
- Sitemap: `/sitemap.xml`
- Robots: `/robots.txt` — `Allow: /` за всички (TODO: Disallow /api/ /data/)
- OG tags: вече са в index.html
- Institucii SEO страници: генерирани от `generate_seo_pages.py`

---

## Известни проблеми / TODO

- [ ] `robots.txt` — добави `Disallow: /data/` и `Disallow: /api/`
- [x] Task Scheduler — "EU Monitor Weekly Alerts" — всеки понеделник 08:00
  - Команда: `python C:\Users\User\eu-monitor-bg\scraper\send_alerts.py`
  - Прави: scrape + match + изпраща само НОВИ програми до засегнатите абонати
- [ ] Rate limiting на `/api/register` и `/api/unsubscribe`
- [ ] `/eu-news` — премахни keyword филтър за BG медии, добави повече категории
- [ ] Намери правилни домейни за Creative Europe Desk BG и АУЕР
- [ ] programs.json понякога се truncate при scrape — провери с `Get-Content data/programs.json -Tail 3`
- [x] FNI parser добавен (fni.bg) — специфичен parser, изключва навигация
- [x] eu-news.html — новини страница с RSS агрегатор
- [x] Новини банер на homepage между email preview и "Следим в реално време"

### PowerShell бележки (Windows)
- `tail` не работи → използвай `Get-Content file -Tail 3`
- `git diff HEAD -w --stat` → реални промени без whitespace
- Преди push: `git diff HEAD -w --stat` + `python -c "import json; json.load(open('data/programs.json'))"` за валидация

---

## Setup на нова машина

```powershell
git clone <repo-url> eu-monitor-bg
cd eu-monitor-bg
# Създай .env с горните променливи
pip install requests beautifulsoup4 python-dotenv
cd scraper
python scraper.py
```

---

## Git правила

- `.env` никога не се commit-ва
- Преди работа: `git pull`
- Преди push: `git diff HEAD -w --stat` за проверка
- Ако има diverge: `git stash → git pull --rebase → git stash pop → git push`
- programs.json може да се truncate — провери с `tail -3 data/programs.json` дали завършва с `]`
