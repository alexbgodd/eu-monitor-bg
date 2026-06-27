import json
import os
import urllib.request

CATEGORY_MAP = {
    "бизнес":     ["бизнес", "иновации", "общи"],
    "земеделие":  ["земеделие", "общи"],
    "култура":    ["култура", "общи"],
    "социални":   ["социални", "общи"],
    "туризъм":    ["туризъм", "бизнес", "общи"],
    "образование":["образование", "социални", "общи"],
    "екология":   ["екология", "общи"],
    "ит":         ["бизнес", "иновации", "общи"],
    "общини":     ["общи", "социални", "земеделие", "култура"],
}

def load_users():
    """Зарежда потребители от Supabase."""
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SECRET_KEY')

    if not url or not key:
        print("Няма SUPABASE_URL / SUPABASE_SECRET_KEY в .env")
        return []

    try:
        req = urllib.request.Request(
            f"{url}/rest/v1/registrations?select=*",
            headers={
                'apikey': key,
                'Authorization': f'Bearer {key}'
            }
        )
        with urllib.request.urlopen(req) as response:
            users = json.loads(response.read().decode())
            # Конвертираме interests от string към list
            for u in users:
                if isinstance(u.get('interests'), str):
                    u['interests'] = [i.strip() for i in u['interests'].split(',')]
            print(f"  Заредени {len(users)} потребители от Supabase.")
            return users
    except Exception as e:
        print(f"  Грешка при зареждане от Supabase: {e}")
        return []

def match_users_to_program(program, users):
    """Връща списък с имейли на потребители, за които програмата е релевантна."""
    matched = []
    prog_category = program.get('category', '').lower()

    for user in users:
        user_interests = [i.lower() for i in user.get('interests', [])]
        for interest in user_interests:
            relevant_categories = CATEGORY_MAP.get(interest, [interest])
            if prog_category in relevant_categories:
                matched.append(user)
                break

    return matched

def get_matches(new_programs):
    """За всяка нова програма - кои потребители трябва да получат имейл."""
    users = load_users()
    if not users:
        print("Няма регистрирани потребители.")
        return {}

    results = {}
    for program in new_programs:
        matched = match_users_to_program(program, users)
        if matched:
            results[program['id']] = {
                "program": program,
                "users": matched
            }

    return results

if __name__ == "__main__":
    # Тест
    from scraper import load_existing
    programs = load_existing()
    if programs:
        matches = get_matches(programs[:3])
        print(f"Съвпадения: {len(matches)}")
        for pid, data in matches.items():
            print(f"\n  {data['program']['title'][:60]}")
            for u in data['users']:
                print(f"    -> {u['email']}")
