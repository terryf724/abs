import requests
from datetime import datetime, timezone
from pycognito import Cognito
import warnings
warnings.filterwarnings("ignore")

USER_POOL_ID = "us-east-2_tYgQh1gc8"
CLIENT_ID = "6o93td7t8m6inee9noheitceds"
API = "https://fq6da3scsi.execute-api.us-east-2.amazonaws.com/prod/data/query"
THINNR_EMAIL = "terry@atlbodysculpt.com"
THINNR_PASSWORD = "Steelers1!"

PATIENTS = [
    {"id": "84cc7d94-c464-4be6-93ff-9aae15e74615", "name": "Yashema Haley"},
    {"id": "af282bfa-9d24-4ac3-8fbf-693e2e61ff27", "name": "Amber Linton"},
    {"id": "d0fbd6f6-d642-4703-85e4-01364184fbdd", "name": "Sabrina Dotson-Ellis"},
    {"id": "e1b288ee-41d6-4471-a25b-ca7c7c8c49ee", "name": "Derdrick Carr"},
    {"id": "168fbebb-cd9e-4248-9ccd-4830692019b8", "name": "Sharonda Timberlake"},
    {"id": "8a048592-dc94-4611-8e40-c58afd4bab02", "name": "Tamara Nerestant"},
    {"id": "cae6e480-59ee-4d56-bcca-93fb1cf24e2b", "name": "Kia Maduro"},
]

def get_token():
    u = Cognito(USER_POOL_ID, CLIENT_ID, username=THINNR_EMAIL)
    u.authenticate(password=THINNR_PASSWORD)
    return u.id_token

def get_last_log(patient_id, token):
    payload = {
        "query": "patientLogsByDate",
        "items": ["date", "meals"],
        "variables": {
            "pk": {"name": "patientID", "value": patient_id},
            "sortDirection": "DESC"
        }
    }
    r = requests.post(API, headers={
        "Content-Type": "application/json",
        "Authorization": token
    }, json=payload)
    items = r.json().get("data", {}).get("items", [])
    for item in items:
        if item.get("meals"):
            return item.get("date")
    return None

def days_since(date_str):
    last = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return (now - last).days

print("\nLogging into THINNR...")
token = get_token()
print("Logged in\n")

warn, danger, ok = [], [], []

for p in PATIENTS:
    last_log = get_last_log(p["id"], token)
    days = days_since(last_log) if last_log else 999
    entry = {**p, "last_log": last_log or "never", "days": days}
    if days >= 4:
        danger.append(entry)
    elif days >= 2:
        warn.append(entry)
    else:
        ok.append(entry)
    print(f"  {p['name']}: {last_log or 'never logged'}")

print("\n" + "="*40)
if danger:
    print(f"\n4+ DAYS NO LOG ({len(danger)})")
    for p in danger:
        print(f"  - {p['name']} -- last logged {p['last_log']}")

if warn:
    print(f"\n2-3 DAYS NO LOG ({len(warn)})")
    for p in warn:
        print(f"  - {p['name']} -- last logged {p['last_log']}")

if ok:
    print(f"\nLOGGED RECENTLY ({len(ok)})")
    for p in ok:
        print(f"  - {p['name']} -- {p['days']} day(s) ago")

print()
