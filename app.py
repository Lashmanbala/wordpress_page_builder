import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from read import read_tab
from post import post_to_wp
from write_url import write_url_sheet

load_dotenv()  # loads .env into environment

USERNAME = os.getenv("WP_USERNAME")
APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
WP_URL = os.getenv("WP_URL")

doc_id = os.getenv("doc_id")
google_credentisals_file = "doc-reader.json"

SCOPES = ["https://www.googleapis.com/auth/documents.readonly", "https://www.googleapis.com/auth/spreadsheets"]

creds = service_account.Credentials.from_service_account_file(google_credentisals_file, scopes=SCOPES)

doc_service = build("docs", "v1", credentials=creds)

doc = doc_service.documents().get(documentId=doc_id, includeTabsContent=True).execute()

sheet_service = build("sheets", "v4", credentials=creds)
spreadsheetId = os.getenv("SPREADSHEET_ID")
sheet_name = os.getenv("SHEET_NAME")   

sheet = sheet_service.spreadsheets().values().get(
                        spreadsheetId=spreadsheetId,
                        range=f"{sheet_name}!A2:A"  # Column A
                    ).execute()

cities = sheet.get("values", [])

# Featured_img_url = 'http://my-site.local/wp-content/uploads/2025/09/Loclite-cover-image-300x111-1.png'
featured_img_url = 'https://www.loclite.co.uk/wp-content/uploads/2025/09/Loclite-cover-image-1.png'
social_image = 'https://www.loclite.co.uk/wp-content/uploads/2025/09/LOClite-744x238-yellow.png'

# Loop through all tabs
for tab in doc.get("tabs", []):
    city_name = tab["tabProperties"]["title"]
    tab_content = tab["documentTab"]["body"]["content"]
    html_content = read_tab(tab_content)
    # print(city_name)
    # print(html_content)

    page_title_format = os.getenv("page_title_format")
    key_phrase_format = os.getenv("key_phrase_format")
    description_format = os.getenv("description_format")

    page_title = page_title_format.format(city_name=city_name)
    key_phrase = key_phrase_format.format(city_name=city_name)
    description = description_format.format(city_name=city_name)

    response = post_to_wp(html_content, featured_img_url, page_title, key_phrase, description, social_image, WP_URL, USERNAME, APP_PASSWORD)

    page_url = response.json()["link"]

    if response.status_code == 201:
        print("✅ Page created successfully!")
        print("Page URL:", page_url)

        write_res = write_url_sheet(sheet_service, spreadsheetId, sheet_name, page_url, city_name, cities)
        print(write_res)

        