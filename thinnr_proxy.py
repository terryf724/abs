from flask import Flask, jsonify, request
from flask_cors import CORS
from pycognito import Cognito
import requests
import warnings
import json
import os
warnings.filterwarnings("ignore")

from ghl_bot_route import register_ghl_bot


app = Flask(__name__)
CORS(app)

register_ghl_bot(app)

THINNR_EMAIL = "terry@atlbodysculpt.com"
THINNR_PASSWORD = "Steelers1!"
USER_POOL_ID = "us-east-2_tYgQh1gc8"
CLIENT_ID = "6o93td7t8m6inee9noheitceds"
API = "https://fq6da3scsi.execute-api.us-east-2.amazonaws.com/prod/data/query"
ONBOARD_API = "https://fq6da3scsi.execute-api.us-east-2.amazonaws.com/prod/patient/onboard"
PATIENTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patients.json")

WATER_TARGET_OZ = 96
_token_cache = {"token": None}

def load_patients():
    with open(PATIENTS_FILE, "r") as f:
        return json.load(f)

def save_patients(patients):
    with open(PATIENTS_FILE, "w") as f:
        json.dump(patients, f, indent=4)

def get_token():
    if not _token_cache["token"]:
        u = Cognito(USER_POOL_ID, CLIENT_ID, username=THINNR_EMAIL)
        u.authenticate(password=THINNR_PASSWORD)
        _token_cache["token"] = u.id_token
    return _token_cache["token"]

def fetch_logs(patient_id, start_date, end_date):
    token = get_token()
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
        if start_date <= item.get("date", "") <= end_date
    }

def group_by_time(meals):
    groups = {}
    for meal in meals:
        t = meal.get("time")
        ingredients = meal.get("ingredients", [])
        if not ingredients:
            continue
        if t not in groups:
            groups[t] = {"time": t, "ingredients": []}
        groups[t]["ingredients"].extend(ingredients)
    return groups

def check_slot(slot_name, slot):
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
    return len(issues) == 0, issues, {"protein": round(protein_oz,1), "veg": round(veg_oz,1), "fruit": round(fruit_oz,1)}

def analyze_day(day_data):
    if not day_data:
        return {"logged": False, "two_meals": False, "no_snacking": False, "on_plan": False, "water_ok": False, "water_oz": 0, "meal_times": [], "plan_notes": [], "meals_detail": [], "snacking": False}
    meals = day_data.get("meals", [])
    water = float(day_data.get("waterIntake") or 0)
    meals_with_food = [m for m in meals if m.get("ingredients")]
    if not meals_with_food:
        return {"logged": False, "two_meals": False, "no_snacking": False, "on_plan": False, "water_ok": False, "water_oz": water, "meal_times": [], "plan_notes": [], "meals_detail": [], "snacking": False}
    groups = group_by_time(meals)
    main_slots = {k: v for k, v in groups.items() if k in ["breakfast", "lunch", "dinner"]}
    has_snacks = "snacks" in groups
    meal_times = list(main_slots.keys())
    no_snacking = not has_snacks
    water_ok = water >= WATER_TARGET_OZ
    exactly_two = len(main_slots) == 2
    plan_notes = []
    meals_detail = []
    all_on_plan = True
    for slot_name, slot in main_slots.items():
        ok, issues, macros = check_slot(slot_name, slot)
        if not ok:
            all_on_plan = False
            plan_notes.extend(issues)
        meals_detail.append({"slot": slot_name, "macros": macros, "on_plan": ok})
    on_plan = all_on_plan and len(main_slots) >= 2
    logged = len(main_slots) >= 2 and on_plan and no_snacking
    return {"logged": logged, "two_meals": exactly_two, "no_snacking": no_snacking, "on_plan": on_plan, "water_ok": water_ok, "water_oz": water, "meal_times": meal_times, "plan_notes": plan_notes, "meals_detail": meals_detail, "snacking": has_snacks}

@app.route("/patients")
def get_patients():
    return jsonify(load_patients())

@app.route("/compliance")
def get_compliance():
    start = request.args.get("start")
    end = request.args.get("end")
    if not start or not end:
        return jsonify({"error": "start and end dates required"}), 400
    _token_cache["token"] = None
    patients = load_patients()
    results = []
    for patient in patients:
        logs = fetch_logs(patient["id"], start, end)
        days = {}
        from datetime import datetime, timedelta
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        for i in range(7):
            date = (start_dt + timedelta(days=i)).strftime("%Y-%m-%d")
            days[date] = analyze_day(logs.get(date))
        results.append({"id": patient["id"], "name": patient["name"], "days": days})
    return jsonify(results)

@app.route("/onboard", methods=["POST"])
def onboard_patient():
    data = request.json
    name = data.get("name")
    phone = data.get("phone")
    start_date = data.get("programStartDate")
    if not name or not phone or not start_date:
        return jsonify({"error": "name, phone, and programStartDate are required"}), 400
    phone = ''.join(filter(str.isdigit, phone))
    _token_cache["token"] = None
    token = get_token()
    payload = {
        "name": name,
        "phone": phone,
        "programID": "thinnr",
        "programStartDate": start_date,
        "mobileAppOnboard": True
    }
    r = requests.post(ONBOARD_API, headers={
        "Content-Type": "application/json",
        "Authorization": token
    }, json=payload)
    result = r.json()
    print(f"Onboarded: {name} ({phone}) — Response: {result}")

    if result.get("statusCode") == 200:
        patient_id = result.get("data", {}).get("id")
        if patient_id:
            patients = load_patients()
            if not any(p["id"] == patient_id for p in patients):
                patients.append({"id": patient_id, "name": name})
                save_patients(patients)
                print(f"Added {name} to patients.json")

    return jsonify({"success": True, "patient": name, "phone": phone, "response": result})

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    print("\nTHINNR Proxy Server running on http://localhost:5001")
    print("Keep this terminal open while using the dashboard\n")
    app.run(port=5001)