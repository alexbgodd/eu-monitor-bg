"""
Поправя името на абонат в Supabase (registrations таблицата).
Пускане: python fix_user_name.py email@abv.bg "Правилно Име"
"""
import json
import os
import sys
import urllib.request

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

URL = os.getenv('SUPABASE_URL')
KEY = os.getenv('SUPABASE_SECRET_KEY')


def main():
    if len(sys.argv) < 3:
        print('Ползване: python fix_user_name.py email "Ново Име"')
        return
    email, new_name = sys.argv[1], sys.argv[2]

    req = urllib.request.Request(
        f"{URL}/rest/v1/registrations?email=eq.{urllib.parse.quote(email)}",
        data=json.dumps({"name": new_name}).encode(),
        method='PATCH',
        headers={
            'apikey': KEY,
            'Authorization': f'Bearer {KEY}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation',
        },
    )
    with urllib.request.urlopen(req) as r:
        rows = json.loads(r.read().decode())
    if rows:
        print(f"✓ Обновено: {rows[0]['email']} -> {rows[0]['name']}")
    else:
        print(f"Не е намерен абонат с имейл {email}")


import urllib.parse
if __name__ == '__main__':
    main()
