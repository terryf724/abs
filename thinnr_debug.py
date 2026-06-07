import requests
from pycognito import Cognito
import warnings
warnings.filterwarnings("ignore")

USER_POOL_ID = "us-east-2_tYgQh1gc8"
CLIENT_ID = "6o93td7t8m6inee9noheitceds"
API = "https://fq6da3scsi.execute-api.us-east-2.amazonaws.com/prod/data/query"

u = Cognito(USER_POOL_ID, CLIENT_ID, username="terry@atlbodysculpt.com")
u.authenticate(password="Steelers1!")
token = u.id_token

print("Token acquired\n")

payload = {
    "query": "patientLogsByDate",
    "items": ["meals", "logMacros", "weight", "waterIntake", "date", "dayStarRating"],
    "variables": {
        "pk": {"name": "patientID", "value": "d0fbd6f6-d642-4703-85e4-01364184fbdd"},
        "sortDirection": "DESC"
    }
}

r = requests.post(API, headers={
    "Content-Type": "application/json",
    "Authorization": token
}, json=payload)

print("Status:", r.status_code)
print("Response:", r.text)
