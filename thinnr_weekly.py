import requests
from datetime import datetime, timezone, timedelta
from pycognito import Cognito
import warnings
warnings.filterwarnings("ignore")

THINNR_EMAIL = "terry@atlbodysculpt.com"
THINNR_PASSWORD = "Steelers1!"
USER_POOL_ID = "us-east-2_tYgQh1gc8"
CLIENT_ID = "6o93td7t8m6inee9noheitceds"
API = "https://fq6da3scsi.execute-api.us-east-2.amazonaws.com/prod/data/query"
WATER_TARGET_OZ = 96

PATIENTS = [
    {"id": "84cc7d94-c464-4be6-93ff-9aae15e74615", "name": "Yashema Haley"},
    {"id": "af282bfa-9d24-4ac3-8fbf-693e2e61ff27", "name": "Amber Linton"},
    {"id": "d0fbd6f6-d642-4703-85e4-01364184fbdd", "name": "Sabrina Dotson-Ellis"},
    {"id": "e1b288ee-41d6-4471-a25b-ca7c7c8c49ee", "name": "Derdrick Carr"},
    {"id": "168fbebb-cd9e-4248-9ccd-4830692019b8", "name": "Sharonda Timberlake"},
    {"id": "8a048592-dc94-4611-8e40-c58afd4bab02", "name": "Tamara Nerestant"},
    {"id": "cae6e480-59ee-4d56-bcca-93fb1cf24e2b", "name": "Kia Maduro"},
    {"id": "2c0d366a-f245-48bb-8b59-95110e1041f8", "name": "Marquita McCall"},
    {"id": "1d359d00-19ea-437f-824e-6b8fdbb1084a", "name": "Debroah Ogunbode"},
    {"id": "92a532ec-d295-4af4-ba04-c242810d1e1d", "name": "Yvette Plaisance"},
    {"id": "9bdde427-4f73-4fbe-80de-ebcecb2ae116", "name": "Veronica Garcia"},
    {"id": "f95c6c8a-6674-4461-aeab-0a4c81e1a4be", "name": "Lisa Dinh"},
    {"id": "a865e8ed-fa46-40b5-b4af-a2293750b189", "name": "Camille Gordon"},
    {"id": "cc8e0668-6b31-4a1b-b503-fc258951ceba", "name": "Shakeela Thompson"},
    {"id": "c3c911b0-80d8-4246-b6dd-707ab11a3bc6", "name": "Tianna Carty"},
    {"id": "39956886-2393-481a-9ff0-b0d8184415c4", "name": "Sonya Logan"},
]

def get_token():
    u = Cognito(USER_POOL_ID, CLIENT_ID, username=THINNR_EMAIL)
    u.authenticate(password=THINNR_PASSWORD)
    return u.id_token

def pick_week():
    today = datetime.now(timezone.utc).date()
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(weeks=1)
    print("\nWhich week do you want to check?")
    print(f"  1. Last week  ({last_monday.strftime('%b %d')} — {(last_monday + timedelta(days=6)).strftime('%b %d')})")
    print(f"  2. This week  ({this_monday.strftime('%b %d')} — {(this_monday + timedelta(days=6)).strftime('%b %d')})")
    print(f"  3. Custom date range")
    choice = input("\nEnter 1, 2, or 3: ").strip()
    if choice == "1":
        monday = last_monday
    elif choice == "2":
        monday = this_monday
    elif choice == "3":
        start = input("Enter start date (YYYY-MM-DD): ").strip()
        monday = datetime.strptime(start, "%Y-%m-%d").date()
    else:
        print("Invalid choice, defaulting to last week")
        monday = last_monday
    sunday = monday + timedelta(days=6)
    return monday, sunday

def fetch_logs(patient_id, token, start_date, end_date):
    payload = {
        "query": "patientLogsByDate",
        "items": ["date", "meals", "waterIntake", "logMacros"],
        "variables": {
            "pk": {"name": "patientID", "value": patient_id},
            "sortDirection": "ASC"
        }
    }
    r = requests.post(API, headers={
        "Content-Type": "application/json",
        "Authorization": token
    }, json=payload)
    items = r.json().get("data", {}).get("items", [])
    return {
        item["date"]: item
        for item in items
        if start_date.isoformat() <= item.get("date", "") <= end_date.isoformat()
    }

def group_by_time(meals):
    groups = {}
    for meal in meals:
        t = meal.get("time")
        if t not in groups:
            groups[t] = {"time": t, "ingredients": []}
        groups[t]["ingredients"].extend(meal.get("ingredients", []))
    return groups

def check_slot_on_plan(slot_name, slot):
    protein_oz = sum(i.get("oz", 0) for i in slot["ingredients"] if i.get("category") == "protein")
    veg_oz = sum(i.get("oz", 0) for i in slot["ingredients"] if i.get("category") == "vegetable")
    fruit_oz = sum(i.get("oz", 0) for i in slot["ingredients"] if i.get("category") == "fruit")
    issues = []
    if protein_oz < 3:
        issues.append(f"{slot_name}: low protein ({round(protein_oz,1)}oz)")
    if veg_oz < 3:
        issues.append(f"{slot_name}: low veg ({round(veg_oz,1)}oz)")
    if fruit_oz < 3:
        issues.append(f"{slot_name}: low fruit ({round(fruit_oz,1)}oz)")
    return len(issues) == 0, issues

def analyze_day(day_data):
    if not day_data:
        return {"logged": False, "two_meals": False, "no_snacking": False, "on_plan": False, "water_ok": False, "water_oz": 0, "meal_times": [], "snack_count": 0, "plan_notes": []}
    meals = day_data.get("meals", [])
    water = float(day_data.get("waterIntake") or 0)
    groups = group_by_time(meals)
    main_slots = {k: v for k, v in groups.items() if k in ["breakfast", "lunch", "dinner"]}
    has_snacks = "snacks" in groups
    meal_times = list(main_slots.keys())
    no_snacking = not has_snacks
    water_ok = water >= WATER_TARGET_OZ
    exactly_two = len(main_slots) == 2
    plan_notes = []
    all_on_plan = True
    for slot_name, slot in main_slots.items():
        ok, issues = check_slot_on_plan(slot_name, slot)
        if not ok:
            all_on_plan = False
            plan_notes.extend(issues)
    on_plan = all_on_plan and len(main_slots) > 0
    logged = len(main_slots) >= 2 and on_plan and no_snacking
    return {"logged": logged, "two_meals": exactly_two, "no_snacking": no_snacking, "on_plan": on_plan, "water_ok": water_ok, "water_oz": water, "meal_times": meal_times, "snack_count": 1 if has_snacks else 0, "plan_notes": plan_notes}

def sym(val):
    return "✓" if val else "✗"

def print_report(patient, logs, monday, sunday):
    print(f"\n{'='*70}")
    print(f"  {patient['name']}")
    print(f"  Week: {monday.strftime('%b %d')} — {sunday.strftime('%b %d, %Y')}")
    print(f"{'='*70}")
    print(f"  {'':14} {'LOG':^5} {'2MLs':^5} {'SNCK':^5} {'PLAN':^5} {'H2O':^5}  {'DETAIL'}")
    print(f"  {'-'*58}")
    days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    totals = {"logged":0,"two_meals":0,"no_snacking":0,"on_plan":0,"water_ok":0}
    today = datetime.now(timezone.utc).date()
    days_elapsed = 0
    for i, day_name in enumerate(days):
        date = monday + timedelta(days=i)
        if date > today:
            print(f"  D{i+1} {day_name} {date.strftime('%m/%d')}   {'—':^5} {'—':^5} {'—':^5} {'—':^5} {'—':^5}")
            continue
        days_elapsed += 1
        result = analyze_day(logs.get(date.isoformat()))
        for key in totals:
            if result[key]: totals[key] += 1
        water_note = f"{int(result['water_oz'])}oz" if result["meal_times"] else ""
        times_note = "+".join(result["meal_times"]) if result["meal_times"] else "nothing logged"
        snack_note = "+snacks" if result["snack_count"] > 0 else ""
        detail = " ".join(filter(None, [times_note, snack_note, water_note]))
        print(f"  D{i+1} {day_name} {date.strftime('%m/%d')}   {sym(result['logged']):^5} {sym(result['two_meals']):^5} {sym(result['no_snacking']):^5} {sym(result['on_plan']):^5} {sym(result['water_ok']):^5}  {detail}")
        if result["plan_notes"]:
            for note in result["plan_notes"]:
                print(f"  {'':44}  ⚠ {note}")
    print(f"  {'-'*58}")
    print(f"  {'Score':14} {totals['logged']}/{days_elapsed}   {totals['two_meals']}/{days_elapsed}   {totals['no_snacking']}/{days_elapsed}   {totals['on_plan']}/{days_elapsed}   {totals['water_ok']}/{days_elapsed}")

def main():
    print("\nLogging into THINNR...")
    token = get_token()
    print("Logged in")
    monday, sunday = pick_week()
    print(f"\nPulling data for {monday.strftime('%b %d')} — {sunday.strftime('%b %d, %Y')}\n")
    for patient in PATIENTS:
        print(f"  Fetching {patient['name']}...", end="\r")
        logs = fetch_logs(patient["id"], token, monday, sunday)
        print_report(patient, logs, monday, sunday)
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    main()
