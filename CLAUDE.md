# ОП + Фондове БГ — Second Brain

Мониторинг на EU финансиране и обществени поръчки с имейл alerts.
**Live сайт:** https://tools.gdprcheck.bg (хостван като инструмент на gdprcheck.bg)
**GitHub:** https://github.com/alexbgodd/eu-monitor-bg
**Vercel проект:** alexbgodd-s-projects/eu-monitor-bg

---

## Архитектура

```
eu-monitor-bg/
├── api/
│   ├── register.py          # Стар fallback (не се ползва — фронтендът пише директно в Supabase)
│   ├── unsubscribe.py       # GET /unsubscribe?email=...&token=... → изтрива от Supabase
│   └── notify_registration.py
├── scraper/
│   ├── scraper.py           # Скрейпва 13+ източника → data/programs.json
│   ├── matcher.py           # Зарежда потребители от Supabase, матчва с програми
│   ├── send_alerts.py       # Изпраща имейл alerts (Gmail SMTP)
│   ├── blast_existing.py    # Еднократен blast към всички потребители от programs.json
│   └── add_isun.py          # Помощен скрипт за добавяне на ИСУН записи
├── web/
│   ├── index.html           # Начална страница + регистрация форма
│   ├── programs.html        # Списък с програми и поръчки (чете /data/programs.json)
│   ├── privacy.html         # GDPR политика за поверителност
│   ├── style.css            # Основен CSS (maze pattern, glassmorphism, badges)
│   ├── water.min.css        # Self-hosted Water.css за типография (без external CDN)
│   └── script.js            # Регистрация форма → Supabase директно
├── data/
│   └── programs.json        # Кешираните програми (обновява се от scraper.py)
├── vercel.json              # Vercel config: rewrites + security headers
├── requirements.txt         # requests, beautifulsoup4, python-dotenv
└── .env                     # НЕ е в git! (вж. секцията по-долу)
```

---

## .env файл (никога не се commit-ва)

```env
SUPABASE_URL=https://jrbmhftixkwcgyjuijji.supabase.co
SUPABASE_SECRET_KEY=<service role key от Supabase>
EMAIL_USER=<gmail адрес>
EMAIL_PASS=<gmail app password — не паролата за акаунта>
```

**Как се вземат:**
- Supabase → Settings → API → service_role key (НЕ anon key)
- Gmail → Акаунт → Сигурност → Двустепенна → App passwords → "eu-monitor"

---

## Supabase

**Проект:** jrbmhftixkwcgyjuijji.supabase.co
**Таблица:** `registrations`

| Колона | Тип | Описание |
|--------|-----|----------|
| id | uuid | auto |
| name | text | Три имена |
| email | text | Уникален |
| org_type | text | НПО / Фирма / Община / ... |
| interests | text | "бизнес, земеделие" (comma-separated string) |
| created_at | timestamp | auto |

**Публичен ключ** (в script.js — окей да е visible):
`sb_publishable_p2RG_e2n7Dm-D6cnzCGrbg_oZAibpIY`

---

## Как работи системата

### 1. Регистрация
Потребителят попълва форма на index.html → script.js пише директно в Supabase REST API.

### 2. Scraping
```bash
cd scraper
python scraper.py
```
Скрейпва 13+ източника, записва нови програми в `data/programs.json`.
Всяка програма има: `id, title, source, category, url, deadline, found_at, type (fund/tender)`.

### 3. Matching + Alerts
```bash
cd scraper
python send_alerts.py
```
- Зарежда потребители от Supabase
- Матчва интересите им с категориите на новите програми (вж. CATEGORY_MAP в matcher.py)
- Изпраща персонализиран HTML имейл с unsubscribe линк

### 4. Blast (еднократно към всички)
```bash
cd scraper
python blast_existing.py
```
Ползва се когато искаш да пратиш всичко от programs.json на всички регистрирани.

---

## Категории и матчинг

```python
CATEGORY_MAP = {
    "бизнес":      ["бизнес", "иновации", "общи"],
    "земеделие":   ["земеделие", "общи"],
    "култура":     ["култура", "общи"],
    "социални":    ["социални", "общи"],
    "туризъм":     ["туризъм", "бизнес", "общи"],
    "образование": ["образование", "социални", "общи"],
    "екология":    ["екология", "общи"],
    "ит":          ["бизнес", "иновации", "общи"],
    "общини":      ["общи", "социални", "земеделие", "култура"],
}
```

---

## Vercel деплой

**Автоматичен:** всеки `git push origin master` → деплой в продакшън.
**Preview:** `git push origin dev` → preview URL, продакшънът не се пипа.

```json
// vercel.json — ключови неща
"rewrites": [
  { "source": "/unsubscribe", "destination": "/api/unsubscribe.py" },
  { "source": "/programs",    "destination": "/web/programs.html"  },
  { "source": "/privacy",     "destination": "/web/privacy.html"   },
  { "source": "/",            "destination": "/web/index.html"     }
]
```

Security headers са настроени (GDPR score: 100/100 на gdprcheck.bg).

---

## Unsubscribe система

**URL формат:** `https://tools.gdprcheck.bg/unsubscribe?email=X&token=Y`

**Token:** HMAC-SHA256(email, SUPABASE_SECRET_KEY) — генерира се в send_alerts.py при всеки имейл.
**API:** api/unsubscribe.py верифицира токена → изтрива от Supabase → показва HTML страница.

---

## Източници (13+)

| Badge | Институция | Parser |
|-------|-----------|--------|
| EU | ИСУН 2020 | `isun` |
| ОП | ЦАИС ЕОП (OCDS) | `eop` |
| МИ | Мин. иновации | `mig` |
| ДФЗ | Държавен фонд Земеделие | `dfz` |
| ЕСФ | ЕСФ България | `esf` |
| ЕР | ЦРЧР Еразъм+ | `erasmus` |
| МК | Мин. Култура | `mc` |
| НФК | Национален фонд Култура | `ncf` |
| НПО | НПО портал | `ngo` |
| ЕФ | Еврофондове.бг | `evrofondove` |
| МЗ | Мин. Земеделие | `mzh` |
| ФИН | finansirane.org | `finansirane` |
| ИП | ИПУП | `ippm` |

**ВАЖНО:** ИСУН дава най-много резултати — никога не го премахвай!

---

## Setup на нова машина

```bash
# 1. Клонирай
git clone https://github.com/alexbgodd/eu-monitor-bg.git
cd eu-monitor-bg

# 2. Python зависимости
pip install -r requirements.txt

# 3. Създай .env (вж. секцията по-горе)
cp .env.example .env   # или ръчно

# 4. Тест на scraper
cd scraper && python scraper.py

# 5. Тест на имейл
python send_alerts.py test
```

---

## Task Scheduler (TODO)

Предстои: Windows Task Scheduler да пуска `scraper.py` + `send_alerts.py` всеки ден в 07:00.

```batch
cd C:\Users\User\eu-monitor-bg\scraper
python send_alerts.py
git add ../data/programs.json
git commit -m "data: автоматичен scrape"
git push
```

---

## GDPR статус: 100/100

Проверено на gdprcheck.bg. Постигнато чрез:
- Security headers в vercel.json (X-Frame-Options, CSP, Referrer-Policy и др.)
- Privacy policy страница на /privacy
- Без external CDN (water.css е self-hosted)
- Без бисквитки / tracking
- Unsubscribe линк в имейлите
- Vercel Analytics (privacy-friendly, без cookies)

---

## Визуален дизайн

- **Цветове:** primary `#2563eb`, hero `#1e40af → #2563eb`
- **Maze pattern:** SVG data URI в CSS variable `--maze` — тънки бели линии на header/hero
- **Stats:** glassmorphism (`rgba(255,255,255,0.1)` + backdrop-filter)
- **Икони:** Lucide (unpkg CDN) — briefcase, wheat, landmark, users, book-open, map-pin, leaf, monitor
- **Source badges:** `.src-badge.eu/.op/.gov/.agri/.edu/.cult`
- **CSS:** style.css + water.min.css (water.css преди style.css, body override за max-width)
