"""
Еднократно изпращане на имейли към регистрираните потребители
на база вече съществуващите програми в programs.json.
Стартирай от: cd scraper && python blast_existing.py
За конкретен имейл: python blast_existing.py email@test.com
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))

from matcher import load_users, match_users_to_program
from send_alerts import send_email

DATA_FILE    = os.path.join(os.path.dirname(__file__), '..', 'data', 'programs.json')
SENT_LOG     = os.path.join(os.path.dirname(__file__), '..', 'data', 'sent_log.json')
WEEK_MARKER  = os.path.join(os.path.dirname(__file__), '..', 'data', 'last_sent_week.txt')
MAX_PER_MAIL = 20


def current_week():
    """ISO седмица, напр. '2026-W35'."""
    from datetime import date
    y, w, _ = date.today().isocalendar()
    return f"{y}-W{w:02d}"


def already_sent_this_week():
    if not os.path.exists(WEEK_MARKER):
        return False
    with open(WEEK_MARKER, encoding='utf-8') as f:
        return f.read().strip() == current_week()


def mark_week_sent():
    with open(WEEK_MARKER, 'w', encoding='utf-8') as f:
        f.write(current_week())

def load_sent_log():
    if os.path.exists(SENT_LOG):
        with open(SENT_LOG, encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_sent_log(log):
    with open(SENT_LOG, 'w', encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

def main():
    dry_run = '--dry-run' in sys.argv
    force = '--force' in sys.argv
    args = [a for a in sys.argv[1:] if a not in ('--dry-run', '--force')]
    target_email = args[0] if args else None
    if dry_run:
        print("=== DRY RUN — нищо няма да се изпрати ===\n")

    # GitHub понякога изхвърля планирани runs (случи се 31.08.2026 — понеделнишкият
    # изобщо не тръгна). Затова workflow-ът опитва няколко пъти в понеделник, а този
    # маркер пази да се изпрати само веднъж седмично.
    if not dry_run and not force and not target_email and already_sent_this_week():
        print(f"Вече е изпратено за седмица {current_week()} — пропускам.")
        return

    # 1. Зареди програмите — сортирани по found_at (най-нови първи)
    with open(DATA_FILE, encoding='utf-8') as f:
        programs = json.load(f)
    programs.sort(key=lambda p: p.get('found_at', ''), reverse=True)
    print(f"Заредени {len(programs)} програми (сортирани по дата).")

    # 2. Зареди sent_log
    sent_log = load_sent_log()

    # 3. Зареди потребителите от Supabase
    users = load_users()
    if not users:
        # Празен списък = или Supabase е паузиран/недостъпен, или наистина няма
        # абонати. И в двата случая мълчаливото излизане скри проблема веднъж
        # (17.08.2026) — затова падаме с грешка, за да почервенее workflow-ът.
        print("ГРЕШКА: Няма заредени потребители (Supabase паузиран/недостъпен?).")
        sys.exit(1)

    if target_email:
        users = [u for u in users if u.get('email') == target_email]
        if not users:
            print(f"Потребител {target_email} не е намерен.")
            return

    print(f"\nПотребители ({len(users)}):")
    for u in users:
        print(f"  {u.get('email')} — интереси: {u.get('interests')}")

    # 4. За всеки потребител — намери нови съвпадащи програми
    print("\nИзпращане...")
    for user in users:
        email = user['email']
        already_sent = set(sent_log.get(email, []))

        matched = [p for p in programs if match_users_to_program(p, [user])]
        new_matches = [p for p in matched if p.get('id') not in already_sent]

        print(f"\n  {email}: {len(matched)} съвпадения, {len(new_matches)} нови, "
              f"{len(already_sent)} вече изпратени")

        if not new_matches:
            print("  -> Пропускаме (всички вече изпратени)")
            continue

        to_send = new_matches[:MAX_PER_MAIL]

        if dry_run:
            print(f"  -> БИ получил {len(to_send)} програми:")
            for p in to_send:
                print(f"       [{p.get('category')}] {p.get('title', '')[:70]}")
            continue

        success = send_email(email, user.get('name', 'потребител'), to_send)

        if success:
            # Запази изпратените ID-та в лога
            sent_ids = [p['id'] for p in to_send if p.get('id')]
            sent_log[email] = list(already_sent | set(sent_ids))
            save_sent_log(sent_log)
            print(f"  -> Изпратени {len(to_send)}, пропуснати {len(already_sent)}")

    if not dry_run and not target_email:
        mark_week_sent()

    print("\n✓ Готово!")

if __name__ == '__main__':
    main()
