"""
Тест на TED API (Tenders Electronic Daily) за български поръчки.
Пусни: python test_ted_api.py
"""
import requests
import json

BASE = "https://api.ted.europa.eu/v3/notices/search"

# TED v3 използва POST с JSON body
payload = {
    "query": "BT-514-Organization-Company=BG AND publication-date>=20260708",
    "page": 1,
    "limit": 3,
    "fields": ["publication-date", "notice-type", "ted-id", "BT-21-Lot", "BT-131(d)-Lot", "BT-27-Lot"]
}

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

print("Тестваме TED API (POST)...")
try:
    r = requests.post(BASE, json=payload, headers=headers, timeout=15)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"Общо резултати: {data.get('totalNoticeCount', '?')}")
        notices = data.get('notices', [])
        print(f"Върнати: {len(notices)}")
        if notices:
            # Покажи keys на първия резултат
            print(f"\nПолета в първия запис:")
            first = notices[0]
            for k, v in first.items():
                print(f"  {k}: {str(v)[:100]}")
    else:
        print(f"Грешка: {r.text[:300]}")
except Exception as e:
    print(f"Изключение: {e}")

# Опит с GET
print("\n\nТестваме TED API (GET)...")
params = {
    "q": "BT-514-Organization-Company=BG",
    "page": 1,
    "limit": 5
}
try:
    r = requests.get(BASE, params=params, headers={"Accept": "application/json"}, timeout=15)
    print(f"Status: {r.status_code}")
    print(r.text[:500])
except Exception as e:
    print(f"Изключение: {e}")
