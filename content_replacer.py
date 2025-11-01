from urllib.parse import urlparse
import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account
from logging_config import logger
from read import read_tab, validate_meta_details
import json
from write_url import write_url_to_sheet
from read import read_tab, validate_meta_details, process_tab_and_child_tabs

load_dotenv()  # loads .env into environment

wp_username = os.getenv("WP_USERNAME")
wp_app_pasword = os.getenv("WP_APP_PASSWORD")
WP_BASE = os.getenv("WP_URL")
valid_urls = os.getenv("VALID_URLS").split(", ")

google_credentisals_file = "doc-reader.json"
SCOPES = ["https://www.googleapis.com/auth/documents.readonly", "https://www.googleapis.com/auth/spreadsheets"]
creds = service_account.Credentials.from_service_account_file(google_credentisals_file, scopes=SCOPES)

doc_id = os.getenv("NEW_CONTENT_DOC_ID")
doc_service = build("docs", "v1", credentials=creds)
doc = doc_service.documents().get(documentId=doc_id, includeTabsContent=True).execute()

doc_title = doc.get("title")
country_name = os.getenv("COUNTRY_NAME")
category_name = os.getenv("CATEGORY_NAME")

try:
    if not validate_meta_details(doc_title, country_name, category_name):
        raise Exception ("Meta validation failed")
except Exception as e:
    logger.error("❌ country_name or category_name is not correct. please check them in the .env file... Or you have given wrong document...check the doc name")
    exit(1)  # stops further execution

spreadsheetId = '1pnyXlhAhIEEqcI24HIWoVz7lq6icYjZjg2aF4KwrbG0'
sheet_name = 'Sheet1'

sheet_service = build("sheets", "v4", credentials=creds)
sheet = sheet_service.spreadsheets().values().get(
                        spreadsheetId=spreadsheetId,
                        range=f"{sheet_name}!A2:B"  # Column A to B
                    ).execute()

city_urls = dict(sheet.get("values", []))   # dictionary of city and urls
cities = city_urls.keys()

PROGRESS_FILE = "progress.json"

# Load progress file (create empty dict if missing)
if os.path.exists(PROGRESS_FILE):
    with open(PROGRESS_FILE, "r") as f:
        progress = json.load(f)
else:
    progress = {}

if doc_id not in progress:
    progress[doc_id] = []

tabs = doc.get("tabs", [])
total_tab_count = len(tabs)
logger.info(f"📄 Document ID: {doc_id} has {total_tab_count} tabs to process.")    

counter = {
            'processed_count' : 0,
            'skipped_count' : 0,
            'wrong_city_name_count' : 0,
            'wrong_internal_link_content_count' : 0,
            'empty_tab_count' : 0,
            'subtab_count' : 0
          }

for tab in tabs:
    html_content_dict = process_tab_and_child_tabs(tab, progress, cities, valid_urls, doc_id, logger, counter)
    
    for city_name, html_content in html_content_dict.items():
    
        
        if city_name in cities:

            page_url = city_urls[city_name]
            logger.info(f'{city_name} found and its link is {city_urls[city_name]}')

                    
            # page_url = 'https://www.loclite.co.uk/test_page/'

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

            # new_content = "<p>new data new data new data</p>"

            payload = {
                "content": html_content
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

            """ ______________ updating the sheet ______________"""

            row_index = None

            for i, row in enumerate(cities, start=2): # 1st row is title so, starting from 2nd row
                if row == city_name:
                    row_index = i
                    break

            if row_index:
                # Update column B in the correct row
                sheet_service.spreadsheets().values().update(
                    spreadsheetId=spreadsheetId,
                    range=f"{sheet_name}!C{row_index}",
                    valueInputOption="RAW",
                    body={"values": [['New Content Updated']]}
                ).execute()
                logger.info (f"✅ Link updated in the sheet successfully!")
            else:
                logger.info(f"⚠️ City '{city_name}' not found in sheet!" )

        else:
            logger.info(f'{city_name} not found in the sheet')




