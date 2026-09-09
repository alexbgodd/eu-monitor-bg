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
- ~100 реални абоната към 16.07.2026 (дошли органично от Facebook; ~37 в началото на юли)
- Python достъп: директни REST API заявки с `urllib.request` (без supabase-py)
- **Free tier паузира проекта след ~седмица без заявки** (случи се 17.08.2026 — регистрациите спряха, седмичният имейл мина на празно). Решение: дневен keep-alive пинг в `daily-run.yml` + `blast_existing.py` пада с exit 1 при 0 заредени потребители. Ръчно събуждане: Supabase dashboard → Resume project.
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

### ЦАИС ЕОП — файлът "поръчки" е основният източник (септ. 2026)

**ВАЖНО — това замени openprocurements хака.** В bucket-а `open-data-<дата>/`
има ЧЕТИРИ файла, не един:

| Файл | Съдържание | Ползваме ли го |
|------|-----------|----------------|
| `...обявления... съгласно стандарт OCDS.json` | OCDS releases; **няма `tenderPeriod`** | да, вторично (допълва) |
| `...поръчки....json` | **основният** — покани за оферти | **да, първично** |
| `...договори....json` | възложени договори + изпълнители | още не (виж TODO) |
| `...анекси....json` | анекси към договори | не |

Файлът "поръчки" дава за **100%** от записите:
`submissionDeadline` · `estimatedValue` + `currency` (EUR) · `mainCpvCode` +
`mainCpvDescription` (на български) · `executionPlaceNuts` · `isEuFunded` +
`europeanProgram` · `isCancelled` · `procedureType` · `buyerRegistryNumber`.

Ключ за свързване: `tenderId` == числовата част на `ocid`
(`ocds-e82gsb-585359` → `585359`). Проверено на 75 дни: по един ред на
`tenderId`, без дубликати, файлът присъства всеки ден.

**КАПАН: обособените позиции са отделни редове.** Всяка обособена позиция
идва като СВОЙ ред със СВОЙ `tenderId`, но с общ `uniqueProcurementNumber`.
Без групиране поръчка с 51 позиции става 51 записа в потока и залива имейла
(случи се при първото пускане на 09.09.2026 — „Доставка на лекарствени
продукти за МБАЛНП Свети Наум“ × 51). Групиране по `uniqueProcurementNumber`;
каноничният ред е първо не-lot, иначе най-малкият `tenderId` — детерминистично,
за да не се сменя `id` между пусканията. Измерено на 7 дни: 666 реда → 257
поръчки (−61%), 76 поръчки с повече от една позиция.
Стойността на слятата поръчка: ако има родителски ред — неговата; ако има
само позиции — сумата им. Броят позиции се пази в поле `lots`.

Функции в `scraper.py`:
- `fetch_eop_procurements(days_back)` → `{tenderId: (day_iso, row)}`; никога не вдига изключение
- `parse_eop_procurements()` → нови записи със същите `id` и `source` като OCDS пътя (дедуплицират се взаимно)
- `enrich_from_eop_procurements()` → допълва вече съществуващи записи
- `_eop_category_v2()` → категория по CPV дивизия, с fallback към старите ключови думи
- `scraper/backfill_eop.py` → еднократно обогатяване на стария `programs.json` (dry-run по подразбиране)
- `scraper/dedupe_eop.py` → слива вече записаните обособени позиции (dry-run по подразбиране)
- `_eop_group_key()` / `_eop_canonical_row()` / `_eop_group_value()` → групиране на позиции
- `scraper/test_eop_procurements.py` → офлайн тест, пусни преди push

**Нови полета в programs.json** (по избор, само за ЕОП записи):
`value`, `currency`, `cpv`, `cpv_desc`, `nuts`, `eu_funded`, `eu_program`,
`procedure`, `contract_type`, `buyer_id`, `procurement_no`, `lots`.
Фронтендът чете само старите полета — допълнителните не могат да счупят нищо.

Измерен ефект при backfill върху 1554 ЕОП записа (09.09.2026):
съвпадение 1552/1554; със срок 551 → 1552; със стойност 0 → 1552;
**1063 срока се променят** (fuzzy match-ът от openprocurements е бъркал);
592 записа се оказват вече изтекли и ще отпаднат при следващ scrape.

### enrich_eop_deadlines() — стар резервен път
Остава в кода, но вече се вика САМО ако след официалното обогатяване още
има ЕОП записи без срок. Историческа бележка: OCDS файлът "обявления"
наистина няма `tenderPeriod.endDate` — грешката беше, че не гледахме
съседния файл "поръчки". Как работеше резервният път:
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
  "социални":    ["социал", "заетост", "труд", "деца"],
  "здравеопазване": ["здрав", "медицин", "болниц", "лекарств", "фармацевт"],  # ново юли 2026; interest "социални" покрива и здравеопазване (обратна съвместимост)
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
| Focus News | focus-news.net/rss.php?cat=6 (национални) | bg | няма — общи БГ новини |
| BG ON AIR | bgonair.bg/rss/c/2-bulgaria | bg | няма — общи БГ новини |
| Bloomberg TV BG | bloombergtv.bg/rss/c/9-bulgaria | bg | няма — общи БГ новини |

**Общи БГ новини (юли 2026):** Focus/BG ON AIR/Bloomberg TV BG се четат без keyword филтър, за да захранят тематичните категории по-долу (не само EU финансиране).

### Мъртви sources (не добавяй отново без проверка)
- TED europa.eu — URL е сменен, 404
- БТА bta.bg — malformed XML, 0 резултата
- Mediapool.bg — 404
- Euractiv — 403 (блокира ботове)
- EU Parliament rss — 404

### Тематични категории (get_topic(), юли 2026)
Вече не е само eu/вътрешни — категоризация като при програмите (matcher.py CATEGORY_MAP):
`eu`, `бизнес`, `земеделие`, `култура`, `социални`, `образование`, `туризъм`, `екология`, `ит`, `общини`, и `общи` (catch-all, ако не съвпада никъде). Keyword listите са в `NEWS_TOPIC_KEYWORDS` в `scrape_eu_news.py`. Филтър бутоните на `/eu-news` са обновени съответно.

### Настройки
- `DAYS_BACK = 2` — само последните 2 дни
- `MAX_ITEMS = 200` (реално ~40-60 след date филтър)
- **Fix (юли 2026):** статии с непризната/непълна дата вече се ИЗКЛЮЧВАТ от филтъра (преди грешка ги третираше като "най-нови" и винаги минаваха).

---

## Vercel routing (vercel.json)

```json
/eu-news     → web/eu-news.html
/notice      → web/notice.html   (детайлна страница, ?id= от programs.json, noindex)
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
- **Групиране (юли 2026):** програмите в имейла са групирани в секции по категория (най-многобройните първи); линковете сочат към /notice
- **blast_existing.py:** изпраща до всички или до конкретен имейл (`python blast_existing.py email@test.com`)
- **sent_log.json:** дедупликация — не праща два пъти едно и също на един абонат
- **Лимит:** 20 програми на имейл (top 20 по found_at desc)
- **Спам проблем при ABV:** domain reputation на Brevo + нов домейн → решение: абонатите да кликнат "Не е спам"

---

## EOP линкове

- Правилен формат: `https://app.eop.bg/today/<tender_id>`
- Стар (грешен) формат: `/bg-BG/notice/0/<id>` — не използвай
- Линковете изискват регистрация в ЦАИС ЕОП (жълтата бележка на /programs беше премахната — юли 2026)

---

## Expire логика (scraper.py)

```python
# Тендери с краен срок → изтичат когато срокът мине
# Тендери без срок → изтичат след 30 дни от found_at
# EU фондове → изтичат след 90 дни от found_at
```

---

## Автоматизация (GitHub Actions) — юли 2026

Разделена на два workflow-а (преди: един daily, който правеше scrape + имейли заедно → имейли всеки ден):

| Workflow | Файл | Кога | Какво прави |
|----------|------|------|-------------|
| Daily scrape | `.github/workflows/daily-run.yml` | всеки ден 06:17 UTC | `scraper.py` + `scrape_eu_news.py` + `generate_seo_pages.py` → commit `data/` + `web/institucii/`. БЕЗ имейли. |
| Weekly alerts | `.github/workflows/weekly-alerts.yml` | понеделник 05:23 / 09:23 / 13:23 UTC | `blast_existing.py` (sent_log дедупликация, top 20 по found_at) → commit `data/sent_log.json` + `data/last_sent_week.txt` |
| News refresh | `.github/workflows/news-refresh.yml` | всеки ден 09:27 UTC (~12:27 BG) | само `scrape_eu_news.py` → commit `data/eu-news.json`. Второ обедно обновяване на /eu-news. |

Бележки:
- `send_alerts.py` (scrape+send в едно, БЕЗ sent_log) вече НЕ се ползва от automation — само ръчно/за тест.
- `sent_log.json` ЗАДЪЛЖИТЕЛНО се комитва от weekly job-а — иначе дедупликацията се губи между run-ове.
- **GitHub забавя и понякога изхвърля планирани runs** (31.08.2026 — понеделнишкият изобщо не тръгна; закъснения от 30 мин до 3+ часа са нормални). Затова weekly има ТРИ cron-а в понеделник, а `data/last_sent_week.txt` (ISO седмица) пази да се изпрати само веднъж. Ръчно форсиране: `python blast_existing.py --force`.
- Windows Task Scheduler "EU Monitor Weekly Alerts" (пон. 08:00 локално) ДУБЛИРА weekly workflow-а — трябва да се изключи (Task Scheduler → Disable), иначе двойни имейли в понеделник.
- Локална работа: прави `git pull` — ботът комитва данни всеки ден.

---

## Workflow — нов scrape + blast

```powershell
cd C:\Users\User\eu-monitor-bg\scraper
python scraper.py              # scrape → programs.json (~1230 активни)
python scrape_eu_news.py       # scrape → eu-news.json
python generate_seo_pages.py   # ВАЖНО: регенерира web/institucii/*.html — иначе SEO страниците замръзват (виж юли 2026 инцидент)
python blast_existing.py       # изпрати до всички нови абонати (sent_log пропуска стари)
cd ..
git add data/ web/institucii/
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

## Vercel Analytics (към 16.07.2026)

- 257 page views на 07.07 — spike от Facebook
- Трафик: ~200 от Facebook (lm.facebook.com, m.facebook.com, facebook.com)
- 95% България, 80% мобилни
- **Обновено 16.07:** последни 30 дни — 441 visitors, 930 page views, 62% bounce rate
- Пик ~120 visitors/ден около 05-06.07 (Facebook spike), после спад към бавно намаляващ базов трафик
- ~100 регистрирани абоната в Supabase (ръст от 37 в началото на юли)

---

## Известни проблеми / TODO

- [ ] Изключи Windows Task Scheduler "EU Monitor Weekly Alerts" — дублира weekly-alerts.yml (двойни имейли в понеделник)
- [ ] Rate limiting на `/api/register` и `/api/unsubscribe`
- [ ] Намери правилни домейни за Creative Europe Desk BG и АУЕР
- [ ] allmarinkov@abv.bg — corrupted name в Supabase, поправи ръчно
- [ ] ЕСФ България (esf.bg) — чест "Read timed out" при scrape, провери стабилността на източника
- [ ] sme.government.bg (ИАНМСП, коригиран домейн — старият `iiam.government.bg` в тази бележка не резолвира) — обмисли добавяне като нов източник
- [x] `robots.txt` — добавен `Disallow: /data/` и `Disallow: /api/`
- [x] `/eu-news` — премахнат тесен keyword филтър, добавени Focus News/BG ON AIR/Bloomberg TV BG + тематични категории (юли 2026)
- [x] SEO: sitemap.xml допълнен с `/eu-news` и `/resources` (липсваха)
- [x] SEO: `generate_seo_pages.py` добавен в редовния workflow — institucii/*.html страниците бяха замръзнали от 02.07 (2 седмици стари, "0 активни" на индексирана страница)
- [x] fix: `parse_isun()` — undefined `base` bug + сменена HTML структура (`<li data-href>` вместо `<a href>`) — ИСУН даваше 0 резултата, сега дава 50+
- [x] Детайлна страница /notice?id=X (юли 2026) — client-side от programs.json, noindex; copy бутон, Google търсене, външен линк, свързани обяви, CTA. "Виж детайли" на /programs и линковете в имейлите сочат натам (fallback към p.url при липсващо id).
- [x] Категория "здравеопазване" отделена от "социални" (юли 2026) — scraper (_eop_category + parse_isun), matcher (interest "социални" пази обратна съвместимост), UI checkbox/labels, `reclassify_health.py` за старите записи (ЗБУТ изключен от health keywords)
- [x] fix: категоризация "ит" vs "бизнес" — дигитал/софтуер ключови думи вече отиват в правилната категория (isun + eop) + еднократна прекатегоризация на стари записи
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
