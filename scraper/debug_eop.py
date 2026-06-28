"""Debug: проверява storage.eop.bg и показва структурата на данните."""
import urllib.request, urllib.parse, xml.etree.ElementTree as ET, json
from datetime import date, timedelta

EOP_BASE = "https://storage.eop.bg"
UA = "eu-monitor-bg/1.0"

def check_day(day_iso):
    url = f"{EOP_BASE}/open-data-{day_iso}/"
    print(f"\n[{day_iso}] GET {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            xml_bytes = r.read()
        print(f"  Статус: OK ({len(xml_bytes)} bytes)")
        root = ET.fromstring(xml_bytes)
        ns = "{http://s3.amazonaws.com/doc/2006-03-01/}"
        keys = [el.text for el in root.iter(f"{ns}Key")]
        print(f"  Файлове ({len(keys)}):")
        for k in keys:
            print(f"    - {k}")
        return keys
    except Exception as e:
        print(f"  ГРЕШКА: {e}")
        return None

def fetch_first_record(day_iso, key):
    url = f"{EOP_BASE}/open-data-{day_iso}/{urllib.parse.quote(key)}"
    print(f"\n  Зареждам: {key[:60]}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        records = data if isinstance(data, list) else data.get("tenders", data.get("items", [data]))
        print(f"  Записи: {len(records)}")
        if records:
            print(f"  Първи запис - полета: {list(records[0].keys())}")
            print(f"  Пример: {json.dumps(records[0], ensure_ascii=False)[:400]}")
    except Exception as e:
        print(f"  ГРЕШКА при fetch: {e}")

today = date.today()
for offset in range(1, 4):
    day = today - timedelta(days=offset)
    keys = check_day(day.isoformat())
    if keys:
        # Само обявления (OCDS)
        ocds_key = next((k for k in keys if "обявлени" in k.lower()), None)
        print(f"  OCDS ключ: {ocds_key}")
        if ocds_key:
            fetch_first_record(day.isoformat(), ocds_key)
        break
