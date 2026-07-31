"""
Еднократно: записва в sent_log.json програмите, изпратени на 31.07.2026
от инцидентния run на send_alerts.py (който не ползва sent_log).
Иначе понеделнишкият blast ще прати същите програми втори път.

Намира "новите" програми като разлика между текущия data/programs.json
и версията в последния commit (git show HEAD). ЗАДЪЛЖИТЕЛНО се пуска
ПРЕДИ да commit-неш data/programs.json!

Пускане: python mark_as_sent.py           (dry run)
         python mark_as_sent.py --apply
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from matcher import load_users, match_users_to_program
from blast_existing import load_sent_log, save_sent_log

ROOT = os.path.join(os.path.dirname(__file__), '..')
DATA_FILE = os.path.join(ROOT, 'data', 'programs.json')


def main():
    apply = '--apply' in sys.argv

    with open(DATA_FILE, encoding='utf-8') as f:
        current = json.load(f)

    head_raw = subprocess.run(
        ['git', 'show', 'HEAD:data/programs.json'],
        cwd=ROOT, capture_output=True,
    ).stdout
    head_ids = {p['id'] for p in json.loads(head_raw.decode('utf-8'))}

    new_programs = [p for p in current if p['id'] not in head_ids]
    print(f"Нови програми от днешния scrape (изпратени с инцидентния run): {len(new_programs)}")
    if not new_programs:
        print("Нищо за маркиране — данните вероятно вече са commit-нати.")
        return

    users = load_users()
    sent_log = load_sent_log()
    total = 0
    for user in users:
        matched_ids = [p['id'] for p in new_programs
                       if p.get('id') and match_users_to_program(p, [user])]
        if not matched_ids:
            continue
        email = user['email']
        already = set(sent_log.get(email, []))
        add = [i for i in matched_ids if i not in already]
        if add:
            print(f"  {email}: +{len(add)} маркирани като изпратени")
            total += len(add)
            if apply:
                sent_log[email] = list(already | set(add))

    if apply:
        save_sent_log(sent_log)
        print(f"\n✓ Записани {total} маркировки в sent_log.json.")
    else:
        print(f"\nDry run — {total} маркировки БИХА се записали. Пусни с --apply.")


if __name__ == '__main__':
    main()
