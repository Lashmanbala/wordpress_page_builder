import os
import json
import requests
from urllib.parse import urlparse
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account

from logging_config import logger
from read import read_tab, validate_meta_details, process_tab_and_child_tabs
from write_url import write_url_to_sheet
from post import update_new_content

def load_environment():
    """Load and validate environment variables."""
    try:
        load_dotenv()

        wp_username = os.getenv("WP_USERNAME")
        wp_app_password = os.getenv("WP_APP_PASSWORD")
        WP_BASE = os.getenv("WP_URL")
        valid_urls = os.getenv("VALID_URLS", "").split(", ")
        google_credentials_file = "doc-reader.json"

        spreadsheet_id = os.getenv("EXISTING_URLS_SPREADSHEET_ID")
        sheet_name = os.getenv("EXISTING_URLS_SHEET_NAME")
        update_column = os.getenv("UPDATE_COLUMN")
        new_content_featured_img_url = os.getenv("NEW_CONTENT_FEATURED_IMAGE_URL")
        doc_id = os.getenv("NEW_CONTENT_DOC_ID")
        country_name = os.getenv("COUNTRY_NAME")
        category_name = os.getenv("CATEGORY_NAME")

        required = [
            wp_username, wp_app_password, WP_BASE,
            spreadsheet_id, sheet_name, doc_id,
            country_name, category_name
        ]
        if not all(required):
            raise EnvironmentError("❌ Missing required environment variables in .env file")

        return {
            "wp_username": wp_username,
            "wp_app_password": wp_app_password,
            "WP_BASE": WP_BASE,
            "valid_urls": valid_urls,
            "google_credentials_file": google_credentials_file,
            "spreadsheet_id": spreadsheet_id,
            "sheet_name": sheet_name,
            "update_column": update_column,
            "new_img": new_content_featured_img_url,
            "doc_id": doc_id,
            "country_name": country_name,
            "category_name": category_name
        }

    except Exception as e:
        logger.exception(f"❌ Failed to load environment variables: {e}")
        exit(1)


def setup_google_services(google_credentials_file):
    """Authenticate and return Google Docs and Sheets services."""
    try:
        SCOPES = [
            "https://www.googleapis.com/auth/documents.readonly",
            "https://www.googleapis.com/auth/spreadsheets"
        ]
        creds = service_account.Credentials.from_service_account_file(google_credentials_file, scopes=SCOPES)
        doc_service = build("docs", "v1", credentials=creds)
        sheet_service = build("sheets", "v4", credentials=creds)
        return doc_service, sheet_service
    except Exception as e:
        logger.exception(f"❌ Failed to authenticate Google API: {e}")
        exit(1)


def read_document(doc_service, doc_id, country_name, category_name):
    """Read Google Doc and validate metadata."""
    try:
        doc = doc_service.documents().get(documentId=doc_id, includeTabsContent=True).execute()
        doc_title = doc.get("title", "Untitled Document")

        if not validate_meta_details(doc_title, country_name, category_name):
            raise ValueError("Meta validation failed — wrong doc, country, or category name.")

        logger.info(f"✅ Document '{doc_title}' validated successfully.")
        return doc, doc_title
    except Exception as e:
        logger.exception(f"❌ Failed to read or validate document '{doc_title}': {e}")
        exit(1)


def read_city_urls(sheet_service, spreadsheet_id, sheet_name):
    """Fetch city and URL mapping from the sheet."""
    try:
        result = sheet_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A2:B"
        ).execute()

        values = result.get("values", [])
        if not values:
            raise ValueError("Sheet appears empty or missing data.")

        return dict(values)
    except Exception as e:
        logger.exception(f"❌ Failed to read sheet data: {e}")
        exit(1)


def load_progress(file_path, doc_id):
    """Load progress JSON or initialize a new one."""
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                progress = json.load(f)
        else:
            progress = {}

        if doc_id not in progress:
            progress[doc_id] = []

        return progress
    except Exception as e:
        logger.error(f"⚠️ Failed to load progress file ({file_path}): {e}")
        return {doc_id: []}


def save_progress(file_path, progress):
    """Save progress JSON safely."""
    try:
        with open(file_path, "w") as f:
            json.dump(progress, f, indent=4)
    except Exception as e:
        logger.error(f"⚠️ Could not save progress to {file_path}: {e}")


def get_wp_page_id(base_url, slug, auth):
    """Fetch WordPress page ID safely."""
    try:
        res = requests.get(f"{base_url}?slug={slug}", auth=auth, timeout=15)
        res.raise_for_status()
        data = res.json()
        if not data or not isinstance(data, list) or "id" not in data[0]:
            raise ValueError("Invalid WordPress page response format.")
        return data[0]["id"]
    except Exception as e:
        logger.error(f"❌ Failed to fetch WP page for slug '{slug}': {e}")
        return None


def update_wp_page(page_id, city_name, html_content, base_url, auth, featured_img):
    """Update WordPress page content."""
    try:
        res = update_new_content(city_name, html_content, base_url, page_id, auth.username, auth.password, featured_img)
        if res.status_code == 200:
            logger.info(f"✅ Updated WP page ID {page_id} for city '{city_name}'")
            return True
        else:
            logger.warning(f"⚠️ WP update failed ({res.status_code}): {res.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Exception updating WP page ID {page_id}: {e}")
        return False


def replace_content():
    logger.info("****************** Starting Content Updation ******************")

    env = load_environment()
    doc_service, sheet_service = setup_google_services(env["google_credentials_file"])
    doc, doc_title = read_document(doc_service, env["doc_id"], env["country_name"], env["category_name"])
    city_urls = read_city_urls(sheet_service, env["spreadsheet_id"], env["sheet_name"])
    cities = city_urls.keys()
    auth = HTTPBasicAuth(env["wp_username"], env["wp_app_password"])

    progress_file = "progress.json"
    progress = load_progress(progress_file, env["doc_id"])

    counter = {
        'processed_count': 0,
        'skipped_count': 0,
        'wrong_city_name_count': 0,
        'wrong_internal_link_content_count': 0,
        'empty_tab_count': 0,
        'subtab_count': 0
    }

    tabs = doc.get("tabs", [])
    total_tab_count = len(tabs)
    logger.info(f"📄 Document ID: {env['doc_id']} has {total_tab_count} tabs to process.")

    for tab in tabs:
        try:
            html_content_dict = process_tab_and_child_tabs(tab, progress, cities, env["valid_urls"], env["doc_id"], logger, counter)

            for city_name, html_content in html_content_dict.items():
                if city_name not in cities:
                    logger.warning(f"⚠️ City '{city_name}' not found in sheet.")
                    counter['wrong_city_name_count'] += 1
                    continue

                page_url = city_urls[city_name]
                slug = urlparse(page_url).path.strip("/")
                if not slug:
                    logger.warning(f"⚠️ Invalid slug for '{city_name}': {page_url}")
                    continue

                page_id = get_wp_page_id(env["WP_BASE"], slug, auth)
                if not page_id:
                    logger.warning(f"⚠️ Invalid page_id for '{city_name}': {page_url}")
                    counter['skipped_count'] += 1
                    continue

                success = update_wp_page(page_id, city_name, html_content, env["WP_BASE"], auth, env["new_img"])

                if success:
                    update_msg = '✅ Content updated'
                    write_url_to_sheet(sheet_service, env["spreadsheet_id"], env["sheet_name"], env["update_column"], update_msg, city_name, cities, logger)
                    progress[env["doc_id"]].append(city_name)
                    save_progress(progress_file, progress)
                    counter["processed_count"] += 1
                else:
                    counter["skipped_count"] += 1

        except Exception as e:
            logger.exception(f"❌ Error processing tab: {e}")

    log_summary(env["doc_id"], total_tab_count, counter)


def log_summary(doc_id, total_tab_count, counter):
    logger.info(f"📊 ===== Summary for Document: {doc_id} =====")
    logger.info(f"📄 Total tabs: {total_tab_count}")
    for k, v in counter.items():
        logger.info(f"{k.replace('_', ' ').title()}: {v}")
        
    logger.info(f"*************************************************************************************************************")
    logger.info(f"*************************************************************************************************************")


if __name__ == "__main__":
    try:
        replace_content()
    except Exception as e:
        logger.exception(f"🚨 Fatal Error during content replacement: {e}")





'''
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
from post import update_new_content

load_dotenv()  # loads .env into environment

logger.info(f"****************** Starting Content Updation ******************")

wp_username = os.getenv("WP_USERNAME")
wp_app_password = os.getenv("WP_APP_PASSWORD")
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
new_content_featured_img_url = os.getenv("NEW_CONTENT_FEATURED_IMAGE_URL")

try:
    if not validate_meta_details(doc_title, country_name, category_name):
        raise Exception ("Meta validation failed")
except Exception as e:
    logger.error("❌ country_name or category_name is not correct. please check them in the .env file... Or you have given wrong document...check the doc name")
    exit(1)  # stops further execution

spreadsheetId = os.getenv("EXISTING_URLS_SPREADSHEET_ID")
sheet_name = os.getenv("EXISTING_URLS_SHEET_NAME")

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

            slug = urlparse(page_url).path.strip("/")

            if not slug:
                logger.warning(ValueError("Invalid page URL — cannot extract slug."))

            res = requests.get(f"{WP_BASE}?slug={slug}", auth=HTTPBasicAuth(wp_username, wp_app_password))

            if res.status_code != 200:
                logger.warning(Exception(f"Failed to fetch page info: {res.status_code} {res.text}"))

            data = res.json()
            page_id = data[0]["id"]

            update_res = update_new_content(html_content, WP_BASE, page_id, wp_username, wp_app_password, new_content_featured_img_url)

            if update_res.status_code == 200:
                logger.info(f"✅ Content updated for page: {page_url}")
            else:
                logger.warning(f"❌ Failed to update page content: {update_res.status_code}")
                logger.warning(update_res.text)

            """ ______________ updating the sheet ______________"""
            
            update_column = os.getenv('UPDATE_COLUMN')
            update_msg = '✅ Content updated'
            write_url_to_sheet(sheet_service, spreadsheetId, sheet_name, update_column, update_msg, city_name, cities, logger)

            # Update progress
            progress[doc_id].append(city_name)
            counter['processed_count'] += 1

            # Save progress to file
            with open(PROGRESS_FILE, "w") as f:
                json.dump(progress, f, indent=4)
        else:
            logger.warning(f'{city_name} not found in the sheet')


# Summary after processing document
logger.info(f"📊 =========================Summary for Document: {doc_id}================")
logger.info(f"📄 This document has {total_tab_count} tabs")
logger.info(f"✅ Processed new tabs: {counter['processed_count']}")
logger.info(f"📄 Subtabs processed (not counted as new): {counter['subtab_count']}")
logger.info(f"⏩ Skipped already processed: {counter['skipped_count']}")
if counter['wrong_city_name_count'] > 0:
    logger.warning(f"⚠️ Tabs with wrong city names: {counter['wrong_city_name_count']}")
if counter['empty_tab_count'] > 0:
    logger.warning(f"⚠️ Empty tabs skipped: {counter['empty_tab_count']}")
if counter['wrong_internal_link_content_count'] > 0:
    logger.warning(f"⚠️ Tabs with wrong internal links: {counter['wrong_internal_link_content_count']}")


if (counter['processed_count'] - counter['subtab_count'] == total_tab_count and counter['wrong_city_name_count'] == 0 and counter['wrong_internal_link_content_count'] == 0) or (counter['processed_count'] + counter['skipped_count'] == total_tab_count and counter['wrong_city_name_count'] == 0 and counter['wrong_internal_link_content_count'] == 0 and counter['processed_count'] > 0 and counter['empty_tab_count'] == 0):
    logger.info(f"✅ All the {total_tab_count} tabs with {counter['subtab_count']} subtabs of the document {doc_id} processed successfully.")

elif counter['skipped_count'] == total_tab_count:
    logger.info(f"ℹ️ All tabs already processed for this document {doc_id}.")

elif counter['wrong_city_name_count'] > 0:
    logger.warning(f"⚠️ {counter['wrong_city_name_count']} city names in the tabs of the document {doc_id} mis-matched with the sheet cities.")

elif counter['wrong_internal_link_content_count'] > 0:
    logger.warning(f"⚠️ {counter['wrong_internal_link_content_count']} tabs in the document {doc_id} have wrong internal links in the content. Check all the internal links")

elif counter['empty_tab_count'] > 0:
    logger.warning(f"⚠️ Empty tabs skipped: {counter['empty_tab_count']}")

else:
    logger.warning(f"⚠️ Document {doc_id} processing completed with mixed results. Something wrong with processing this doc. Check manually.")

logger.info(f"*************************************************************************************************************")
logger.info(f"*************************************************************************************************************")



'''
