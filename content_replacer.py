import os
import json
import requests
from urllib.parse import urlparse
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.errors import HttpError

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

    doc_title = None  # ✅ define upfront to avoid UnboundLocalError

    try:
        doc = doc_service.documents().get(documentId=doc_id, includeTabsContent=True).execute()
        
        doc_title = doc.get("title", "Untitled Document")

        if not validate_meta_details(doc_title, country_name, category_name):
            raise ValueError("Meta validation failed — wrong doc, country, or category name.")

        logger.info(f"✅ Document '{doc_title}' validated successfully.")
        return doc, doc_title
    
    except HttpError as e:
        # Handle specific API permission errors
        if e.resp.status == 403:
            logger.error(
                f"🚫 Permission denied for Google Doc ID '{doc_id}'. "
                "Ensure the service account has access (shared or proper OAuth scope)."
            )
        elif e.resp.status == 404:
            logger.error(
                f"📄 Google Doc ID '{doc_id}' not found. Double-check the document ID or sharing settings."
            )
        else:
            logger.exception(f"❌ Google Docs API error for doc '{doc_title or doc_id}': {e}")
        exit(1)

    except Exception as e:
        logger.exception(f"❌ Failed to read or validate document '{doc_title or doc_id}': {e}")
        exit(1)

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
        
        city_urls = dict(values)
        city_urls = {city.strip(): url for city, url in city_urls.items()}
        return city_urls

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

