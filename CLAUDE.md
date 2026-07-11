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
│   ├── scraper.py           # Главен scraper — 15+ източника
│   ├── matcher.py           # Matching потребители ↔ програми по категория
│   ├── send_alerts.py       # Изпращане на имейли (Brevo SMTP)
│   ├── blast_existing.py    # Еднократен blast към съществуващи абонати
│   ├── generate_seo_pages.py # Генерира institucii/*.html SEO страници
│   ├── check_deadlines.py   # Анализ на крайни срокове в programs.json
│   ├── scrape_eu_news.py    # RSS агрегатор за новини (нов — юли 2026)
│   └── test_new_sources.py  # Тест скрипт за нови потенциални източници
├── data/
│   ├── programs.json        # ~1230 активни програми и поръчки
│   ├── eu-news.json         # Последни новини (2 дни, ~46 статии)
│   └── sent_log.json        # Лог на изпратените имейли (дедупликация)
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
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_LOGIN=...
SMTP_KEY=...
EMAIL_FROM=info@gdprcheck.bg
```

**.env е в .gitignore — никога не се commit-ва.**

---

## Supabase

- Таблица: `registrations`
- Колони: `id, email, name, org_type, interests (text[]), created_at`
- ~37 реални абоната към юли 2026 (дошли органично от Facebook)
- Python достъп: директни REST API заявки с `urllib.request` (без supabase-py)
- `alexbgodd@gmail.com` НЕ е регистриран като абонат в Supabase
- allmarinkov@abv.bg има corrupted name в Supabase — провери и поправи ръчно

---

## Scraper — източници (scraper.py)

15+ активни източници:

| Badge | Източник | Parser |
|-------|----------|--------|
| EU | ИСУН 2020 — EU процедури | `isun` |
| ОП | ЦАИС ЕОП — Поръчки | `eop` |
| МИ | Мин. на иновациите | `mig` |
| ДФЗ | Държавен фонд Земеделие | `dfz` |
| ЕСФ | ЕСФ България | `esf` |
| ЕР | ЦРЧР — Еразъм+ | `hrdc` |
| МК | Министерство на културата | `mc` |
| НФК | Национален фонд Култура | `ncf` |
| НПО | НПО Портал (ngobg.info) | `ngobg` |
| ЕОП | ЦАИС ЕОП — Обявления | `eop` (S3) |
| ФНИ | Фонд Научни изследвания (fni.bg) | `fni` |
| МОН | МОН — Национални програми | `mon` |
| МОСВ | МОСВ — Програми и проекти | `moew` |

**ВАЖНО: ИСУН не се премахва — дава най-много резултати.**

### Мъртви sources (не добавяй без проверка)
- cedesk.bg — DNS не резолвира
- auer.bg — DNS не резолвира
- ИАНМСП (iiam.government.bg) — DNS не резолвира
- Предприемачески фонд (entrepreneurshipfund.bg) — DNS не резолвира
- Агенция по заетостта — SSL DH key too small (слаб SSL)
- МТСП — само новини и стари процедури, не е полезен
- Интеррег България-Румъния (interregrobg.eu) — 404
- ПНИИДИТ (mig.government.bg/pniidit) — изтеклите процедури са маркирани само с JS, requests не ги вижда → показваше изтекли като активни. ИСУН покрива отворените.
- bg.openprocurements.com — wrapper около TED, линкове водят към тяхна страница (не ЦАИС ЕОП). Използваме САМО за deadline enrichment (виж по-долу).

### enrich_eop_deadlines() — обогатяване с крайни срокове
ЦАИС ЕОП OCDS данните не включват `tenderPeriod.endDate`. За да попълним крайните срокове:
- bg.openprocurements.com показва `Deadline YYYY-MM-DD` на listing страницата
- `enrich_eop_deadlines()` в scraper.py scrape-ва 5 страници от тях след всеки scrape
- Fuzzy match по заглавие (word overlap ≥80%) → копира само датата, URL остава app.eop.bg
- Резултат: ~309 ЕОП записа обогатени с крайни срокове при първо пускане

### parse_hrdc — строги филтри (само реални покани)
- must_have: `['покан', 'кандидатстван', 'насоки за', 'мобилност', 'изграждане на капацитет']`
- skip: новини, срещи, меморандуми, резултати, координатори

### parse_mon — филтри
- skip: архив, 2020, 2021-2023, "за 2024 г", "за 2025 г", регионални управления

### parse_moew — филтри
- skip: приключил, архив, ИСПА, Швейцарска, "обща информация", "програми и проекти"

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

**Vercel Analytics:** добавен в index.html, programs.html, eu-news.html.

---

## Homepage структура (index.html)

1. Header (logo-box + "Полезни ресурси" бутон центриран под логото, син)
2. Hero (h1 + stats + бутони)
3. Категории с брояч (динамично от programs.json)
4. **"Последно обявени поръчки"** — 5 най-нови EOP тендера (динамично, само type=tender)
5. "Как работи" (3 стъпки)
6. Email preview mock
7. Новини банер → /eu-news (червен)
8. "Следим в реално време" (sources list)
9. FAQ (details/summary)
10. Регистрационна форма
11. Footer

---

## Имейл система (send_alerts.py + blast_existing.py)

- **Transport:** Brevo SMTP (smtp-relay.brevo.com:587)
- **От:** info@gdprcheck.bg
- **Шаблон:** 1 линк на програма (plain URL) — повече линкове → спам
- **blast_existing.py:** изпраща до всички или до конкретен имейл (`python blast_existing.py email@test.com`)
- **sent_log.json:** дедупликация — не праща два пъти едно и също на един абонат
- **Лимит:** 20 програми на имейл (top 20 по found_at desc)
- **Спам проблем при ABV:** domain reputation на Brevo + нов домейн → решение: абонатите да кликнат "Не е спам"

---

## EOP линкове

- Правилен формат: `https://app.eop.bg/today/<tender_id>`
- Стар (грешен) формат: `/bg-BG/notice/0/<id>` — не използвай
- Линковете изискват регистрация в ЦАИС ЕОП — добавена бележка на /programs при таб "Обществени поръчки"

---

## Expire логика (scraper.py)

```python
# Тендери с краен срок → изтичат когато срокът мине
# Тендери без срок → изтичат след 30 дни от found_at
# EU фондове → изтичат след 90 дни от found_at
```

---

## Workflow — нов scrape + blast

```powershell
cd C:\Users\User\eu-monitor-bg\scraper
python scraper.py          # scrape → programs.json (~1230 активни)
python scrape_eu_news.py   # scrape → eu-news.json
python blast_existing.py   # изпрати до всички нови абонати (sent_log пропуска стари)
cd ..
git add data/
git commit -m "chore: scrape update"
git push
```

**Важно:** `git pull` преди да започваш работа. При diverge: `git stash → git pull --rebase → git stash pop → git push`

---

## Unsubscribe система

- URL: `/unsubscribe?email=X&token=Y`
- Token: HMAC-SHA256 на email с `UNSUBSCRIBE_SECRET`
- Контакт email в error съобщения: `info@gdprcheck.bg`

---

## SEO

- Google verification: `/googleaf2fb16ab37a2df7.html`
- Sitemap: `/sitemap.xml`
- Robots: `/robots.txt` — TODO: Disallow /data/ и /api/
- Institucii SEO страници: генерирани от `generate_seo_pages.py`

---

## Vercel Analytics (към 10.07.2026)

- 257 page views на 07.07 — spike от Facebook
- Трафик: ~200 от Facebook (lm.facebook.com, m.facebook.com, facebook.com)
- 95% България, 80% мобилни

---

## Известни проблеми / TODO

- [ ] `robots.txt` — добави `Disallow: /data/` и `Disallow: /api/`
- [ ] Rate limiting на `/api/register` и `/api/unsubscribe`
- [ ] `/eu-news` — премахни keyword филтър за BG медии, добави повече категории
- [ ] Намери правилни домейни за Creative Europe Desk BG и АУЕР
- [ ] allmarinkov@abv.bg — corrupted name в Supabase, поправи ръчно
- [x] Task Scheduler — "EU Monitor Weekly Alerts" — всеки понеделник 08:00
- [x] EOP линкове сменени на `/today/{id}` формат
- [x] blast_existing.py — дедупликация чрез sent_log.json
- [x] МОН и МОСВ добавени като нови източници
- [x] parse_hrdc, parse_mon, parse_moew — строги филтри срещу новини/стари записи
- [x] "Последно обявени поръчки" секция на homepage (само EOP тендери, динамично)
- [x] Бележка на /programs при таб "Обществени поръчки" за ЦАИС ЕОП линкове
- [x] Expire логика: тендери 30 дни, фондове 90 дни
- [x] ПНИИДИТ премахнат като source — изтеклите не се виждат от requests
- [x] enrich_eop_deadlines() — 309 ЕОП записа обогатени с крайни срокове от openprocurements.com
- [x] /resources страница — обновена с точна информация за eufunds.bg и сравнение с Румъния
- [x] "Полезни ресурси" бутон — син, по-голям, центриран под логото в header

### PowerShell бележки (Windows)
- `tail` не работи → използвай `Get-Content file -Tail 3`
- `git diff HEAD -w --stat` → реални промени без whitespace

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
