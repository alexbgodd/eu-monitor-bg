# CLAUDE.md — Second Brain: eu-monitor-bg

> Чети този файл в началото на всяка нова сесия за пълен контекст на проекта.

---

## Какво е проектът

**ОП + Фондове БГ** — безплатен имейл alert сервиз за обществени поръчки и EU финансиране в България.
- URL: https://tools.gdprcheck.bg
- Домейн: tools.gdprcheck.bg (subdomain на gdprcheck.bg)
- Хостинг: Vercel (free tier)
- Репо: `C:\Users\alexb\Documents\eu-monitor-bg` (старият път C:\Users\User\ вече не важи)

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
│   ├── test_new_sources.py  # Тест скрипт за нови потенциални източници
│   ├── backfill_eop.py      # Еднократно обогатяване на стар programs.json (dry-run по подр.)
│   ├── dedupe_eop.py        # Слива обособени позиции в един запис (dry-run по подр.)
│   ├── test_eop_procurements.py  # Офлайн тест на ЕОП парсването — пусни преди push
│   ├── test_email_render.py      # Офлайн тест на имейла — пусни преди push
│   └── testdata/            # Фикстури (preview_email.html е в .gitignore)
├── data/
│   ├── programs.json        # ~1150 активни програми и поръчки
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

**При нов чекаут .env го НЯМА** — трябва да се създаде ръчно (случи се 09.09.2026).
Минимум за `blast_existing.py --dry-run`: само `SUPABASE_URL` + `SUPABASE_SECRET_KEY`.
За реално изпращане локално трябват и SMTP променливите. GitHub Actions ги взима
от секретите на репото, не от .env.
`SUPABASE_SECRET_KEY` е `service_role` ключът (Supabase → Project Settings → API Keys).
Той заобикаля RLS напълно — не влиза никъде в кода на сайта.

---

## Supabase

- Таблица: `registrations`
- Колони: `id, email, name, org_type, interests (text[]), created_at`
- **65 активни абоната към 09.09.2026** (id-тата стигат до 94 → ~29 отписани/изтрити, ~30% отпадане)
- ~100 към 16.07.2026, ~37 в началото на юли — растежът е органичен от Facebook
- **RLS е проверен и работи** (09.09.2026): анонимният ключ връща празен масив при 65 реални реда → няма политика за SELECT. Само 1 политика на таблицата — при промяна провери, че остава само за INSERT.
- В таблицата има регистрации с натракани имена (id 18, 21, 31, 84, 90) — липсва валидация; името влиза в поздрава на писмото
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
- **Лимит:** 20 програми на имейл, избрани от `select_for_email()` в blast_existing.py

### Подбор за имейла (преработен 09.09.2026 — виж защо)
- **Подборът е по НАЙ-НОВО намерено**, не по най-скоро изтичащо. sent_log праща всяка
  обява точно веднъж → писмото е „какво е ново“, а новото има най-много оставащо време.
  Подредба по изтичащ срок систематично избираше обявите с най-малко време. Пробвано и
  върнато назад същия ден.
- `MIN_DAYS_TO_ACT = 5` — обяви с по-малко дни изобщо не влизат. По ЗОП минималният срок
  за оферти е 30 дни (открита процедура) и 20 (публично състезание); при 5 дни остатък
  е минала две трети от прозореца. Първият dry-run показа, че почти всеки абонат щеше
  да получи 12 поръчки с „ИЗТИЧА ДНЕС“.
- `FUND_QUOTA = 8` — гарантирано място за фондове. Без нея фондовете (които нямат
  срокове) падаха на дъното и НПО-тата спираха да получават програми изобщо.
- `NOISE_EXACT` / `NOISE_PREFIX` — бюджетни пера на управляващи органи („Техническа
  помощ“, „Бюджетни линии“, „Контрол и правоприлагане“, „Морско наблюдение“) не влизат
  в имейла. Сайтът продължава да ги показва. 9 записа отпадат.
- Редът ВЪТРЕ в писмото е по спешност — най-спешното измежду вече подбраните.

### Формат на писмото (09.09.2026)
- Текстова част (`text/plain`) + HTML. Само HTML вдига спам-рейтинга — това е първото,
  което помага при проблема с abv.bg.
- Хедъри `List-Unsubscribe` + `List-Unsubscribe-Post: One-Click` — Gmail и Yahoo ги
  изискват от масовите податели; без тях доставяемостта пада тихо.
- Всеки ред показва срок с оставащи дни (оцветен по спешност), стойност, регион,
  брой обособени позиции, знак за ЕС финансиране.
- Темата брои спешните: „20 нови програми · 6 изтичат до 7 дни“.
- **ВНИМАНИЕ при промени:** `days_left(...) or 99` е грешно — 0 дни е falsy в Python и
  точно най-спешните изпадат от бройката. Открито от теста.

### Тестове преди изпращане — ЗАДЪЛЖИТЕЛНИ
```powershell
python scraper/test_email_render.py    # офлайн, без мрежа; пише preview_email.html
python scraper/blast_existing.py --dry-run   # какво точно би получил всеки абонат
```
Dry-run хвана и трите сериозни грешки от 09.09.2026. Не пропускай тази стъпка.
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

## Състояние към 09.09.2026 (край на голямата сесия)

| Показател | сутринта | вечерта |
|---|---|---|
| Записи в programs.json | 1 683 | 1 148 |
| Поръчки с краен срок | 551 (33%) | 1 002 (98%) |
| Поръчки със стойност | 0 | 1 002 |
| С CPV и NUTS регион | 0 | 1 002 |
| Изтекли, но показвани | 71 | 0 |
| Свързани с ЕС програма | 0 | 172 |
| Излишни записи от позиции | 407 | слети |

Комити: `66360a1` данни · `11ce37a` фронтенд · `d25c6ad` имейл ·
`fb59370` срокове · `4ee0e23` шум в имейла.

---

## Отворени задачи — по приоритет

### 1. ИСУН срокове за фондовете — най-голямата дупка
**0 от 129 фонда имат краен срок.** Половината от бранда не изпълнява обещанието
„няма да изпуснеш срок“. Полето го има на страницата на всяка процедура в ИСУН, но
иска скрейпване на детайлната страница, не само на списъка. Внимавай: ИСУН вече веднъж
е сменял HTML структурата и е чупил парсера (виж parse_isun bug-а от юли). Прави го с
кеш и бавно темпо — 129 заявки към държавен сайт.

### 2. Категориите — продуктово решение, не технически бъг
Видими грешки: болничен кетъринг → „туризъм“ (CPV 55 = хотелиерство), самолетни билети
→ „култура“, климатици → „здравеопазване“, защитни стени → „екология“, регистриран
одитор → „екология“. 20 поръчки за доставка на храна стоят като „земеделие“.

Истинският въпрос не е как да се класифицира, а **какво търси човек, който се абонира
за „земеделие“**. Ако търси субсидии за стопанството си, доставките на храна за детски
градини му пречат. Ако е фирма, която продава храни, точно те са му интересни. Това са
два продукта в една категория. С `mainCpvCode` вече има основа за много по-точен списък
с интереси (CPV има около 45 дивизии). Не се пипа набързо.

### 3. Валидация на формата за регистрация
Няма валидация и няма rate limiting на `/api/register`. В базата стоят имена като
„дфгбсдфхгб“ и „ХЙА Хуамьь“, които влизат в поздрава на писмото („Здравей, ХЙА Хуамьь!“).
Всеки може да натъпче таблицата. Пипа точката, през която идват нови абонати — прави се
спокойно, не преди голямо изпращане.

### 4. Дребни и лесни
- [ ] ДФЗ връща „В момента няма мерки за подпомагане отворени за кандидатстване“ като
      програма — артефакт от скрейпването; добави го в `NOISE_EXACT`
- [ ] 17 ЕОП записа без новите полета (остатъци от OCDS пътя); заради тях всяко пускане
      още чука на bg.openprocurements.com напразно
- [ ] Заглавия се вмъкват без екраниране на няколко места (поправено в /programs и
      /notice, но не навсякъде)
- [ ] Няма backup на Supabase (безплатен план) — експортвай таблицата като CSV
- [ ] `/notice` е `noindex` → 1 148 записа = 1 148 неизползвани индексируеми страници.
      Най-големият пропуснат SEO канал.
- [ ] Домейнът `gdprcheck.bg` е паркинг. NIS2 е в сила от 17.02.2026, пълни санкции от
      01.06.2026, 10–12 хиляди организации в обхвата. Инструмент за самооценка там е
      по-платежоспособен бизнес от еврофондовете.

---

## Работа по проекта с Claude — научено на 09.09.2026

**CRLF илюзия.** Файловете на Windows са с CRLF, в комитите с LF, Git за Windows
превръща автоматично. От Linux (както Claude вижда папката) ВСЕКИ файл изглежда променен.
`git diff -w --stat` показва истината. **Никога `git add -A`** — рискуваш да повлечеш 60
файла нормализация в един комит. Добавяй поименно.

**index.lock.** Ако Claude пусне git команда в папката, може да остане `.git/index.lock`
и да блокира всичко. Claude няма права да трие файлове на Windows машината — изтрий го с
`Remove-Item .git\index.lock`. По-добре Claude само чете файловете, а git го караш ти.

**Лични данни.** `blast_existing.py --dry-run` печата имената и имейлите на всички
абонати. Пускай го сам и не поствай изхода никъде — това са данни на реални хора.

**Ред на работа, който сработи.** Одит → най-малкият риск първо (само визуализация) →
промяна с офлайн тест → dry-run → чак тогава нещо, което стига до хора. И трите сериозни
грешки в имейла бяха хванати от dry-run и от въпроса „а стигат ли им 5 дни да
кандидатстват?“, не от кода и не от тестовете.

**Скептицизъм към готовите решения.** Хакът с openprocurements съществуваше, защото
CLAUDE.md твърдеше, че сроковете ги няма в отворените данни. Беше вярно за файла, който
се четеше, и невярно за bucket-а. Преди да заобикаляш нещо, погледни какво още има в
източника.

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
git clone https://github.com/alexbgodd/eu-monitor-bg.git
cd eu-monitor-bg
pip install -r requirements.txt
# СЪЗДАЙ .env — не идва с репото (виж секцията „.env променливи“)
python scraper/test_eop_procurements.py   # трябва да мине без мрежа
python scraper/test_email_render.py       # трябва да мине без мрежа
python scraper/scraper.py
```

### Преди всеки push
```powershell
python scraper/test_eop_procurements.py
python scraper/test_email_render.py
python scraper/generate_seo_pages.py   # иначе institucii/*.html замръзват
git add <файловете поименно>           # НЕ git add -A
git pull --rebase                      # ботът комитва данни всеки ден
git push
```
