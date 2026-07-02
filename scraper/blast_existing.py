"""
Еднократно изпращане на имейли към регистрираните потребители
на база вече съществуващите програми в programs.json.
Стартирай от: cd scraper && python blast_existing.py
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))

from matcher import load_users, match_users_to_program
from send_alerts import send_email

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'programs.json')

def main():
    # 1. Зареди програмите
    with open(DATA_FILE, encoding='utf-8') as f:
        programs = json.load(f)
    print(f"Заредени {len(programs)} програми.")

    # 2. Зареди потребителите от Supabase
    users = load_users()
    if not users:
        print("Няма регистрирани потребители.")
        return

    print(f"\nПотребители ({len(users)}):")
    for u in users:
        print(f"  {u.get('email')} — интереси: {u.get('interests')}")

    # 3. За всеки потребител — намери съвпадащи програми
    print("\nИзпращане...")
    for user in users:
        matched = [p for p in programs if match_users_to_program(p, [user])]
        print(f"\n  {user.get('email')}: {len(matched)} програми съвпадат")
        if matched:
            # Изпращаме до 20 — не искаме да спамим
            send_email(
                user['email'],
                user.get('name', 'потребител'),
                matched[:20]
            )
        else:
            print("  -> Пропускаме (няма съвпадения)")

if __name__ == '__main__':
    main()
