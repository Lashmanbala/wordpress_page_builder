from urllib.parse import urlparse
import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account
import gspread

load_dotenv()  # loads .env into environment

wp_username = os.getenv("WP_USERNAME")
wp_app_pasword = os.getenv("WP_APP_PASSWORD")
WP_BASE = os.getenv("WP_URL")

google_credentisals_file = "doc-reader.json"
SCOPES = ["https://www.googleapis.com/auth/documents.readonly", "https://www.googleapis.com/auth/spreadsheets"]
creds = service_account.Credentials.from_service_account_file(google_credentisals_file, scopes=SCOPES)

spreadsheetId = '1pnyXlhAhIEEqcI24HIWoVz7lq6icYjZjg2aF4KwrbG0'
sheet_name = 'Sheet1'


sheet_service = build("sheets", "v4", credentials=creds)
sheet = sheet_service.spreadsheets().values().get(
                        spreadsheetId=spreadsheetId,
                        range=f"{sheet_name}!A1:B"  # Column A
                    ).execute()

cities = sheet.get("values", [])   # it gives list of lists

flat_cities_list = [cell for row in cities for cell in row]
print(cities)



# sheet_service.spreadsheets().values().update(
#     spreadsheetId=spreadsheetId,
#     range=f"{sheet_name}!B2",
#     valueInputOption="USER_ENTERED",
#     body={"values": [["✅ Updated"] for _ in urls]}
# ).execute()



'''
page_url = 'https://www.loclite.co.uk/test_page/'

slug = urlparse(page_url).path.strip("/")

if not slug:
    print(ValueError("Invalid page URL — cannot extract slug."))
          
print(slug)  


res = requests.get(f"{WP_BASE}?slug={slug}", auth=HTTPBasicAuth(wp_username, wp_app_pasword))

if res.status_code != 200:
    print(Exception(f"Failed to fetch page info: {res.status_code} {res.text}"))

data = res.json()
page_id = data[0]["id"]

print(page_id)
print(data)

new_content = "<p>new data new data new data</p>"

payload = {
    "content": new_content
}

update_res = requests.post(
    f"{WP_BASE}/{page_id}",
    auth=HTTPBasicAuth(wp_username, wp_app_pasword),
    json=payload
)

if update_res.status_code == 200:
    print(f"✅ Content updated for page: {page_url}")
else:
    print(f"❌ Failed to update page content: {update_res.status_code}")
    print(update_res.text)
'''