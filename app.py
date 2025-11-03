import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from logging_config import logger

from read import validate_meta_details, process_tab_and_child_tabs
from post import post_to_wp
from write_url import write_url_to_sheet

def load_configuration():
    """Load environment variables and handle missing configurations."""
    try:
        load_dotenv()
        config = {
            "wp_username": os.getenv("WP_USERNAME"),
            "wp_app_password": os.getenv("WP_APP_PASSWORD"),
            "wp_url": os.getenv("WP_URL"),
            "featured_img_url": os.getenv("FEATURED_IMAGE_URL"),
            "social_image": os.getenv("SOCIAL_IMAGE_URL"),
            "doc_id": os.getenv("DOC_ID"),
            "spreadsheet_id": os.getenv("SPREADSHEET_ID"),
            "sheet_name": os.getenv("SHEET_NAME"),
            "url_column": os.getenv("URL_COLUMN"),
            "valid_urls": os.getenv("VALID_URLS", "").split(", "),
            "country_name": os.getenv("COUNTRY_NAME"),
            "category_name": os.getenv("CATEGORY_NAME"),
            "page_title_format": os.getenv("page_title_format"),
            "key_phrase_format": os.getenv("key_phrase_format"),
            "description_format": os.getenv("description_format"),
            "brand_name": os.getenv("BRAND_NAME"),
            "google_credentials_file": "doc-reader.json",
            "progress_file": "progress.json"
        }

        # Basic validation
        missing_keys = [k for k, v in config.items() if not v]
        if missing_keys:
            logger.error(f"❌ Missing required environment variables: {', '.join(missing_keys)}")
            exit(1)

        return config

    except Exception as e:
        logger.exception(f"❌ Failed to load configuration: {e}")
        exit(1)


# google_credentisals_file = "doc-reader.json"

# SCOPES = ["https://www.googleapis.com/auth/documents.readonly", "https://www.googleapis.com/auth/spreadsheets"]
# creds = service_account.Credentials.from_service_account_file(google_credentisals_file, scopes=SCOPES)

# doc_service = build("docs", "v1", credentials=creds)
# doc = doc_service.documents().get(documentId=doc_id, includeTabsContent=True).execute()

# doc_title = doc.get("title")

def get_google_services(credentials_file):
    """Authenticate and return Google Docs and Sheets services."""
    try:
        SCOPES = [
            "https://www.googleapis.com/auth/documents.readonly",
            "https://www.googleapis.com/auth/spreadsheets"
        ]
        creds = service_account.Credentials.from_service_account_file(credentials_file, scopes=SCOPES)

        doc_service = build("docs", "v1", credentials=creds)
        sheet_service = build("sheets", "v4", credentials=creds)

        return doc_service, sheet_service

    except FileNotFoundError:
        logger.error(f"❌ Credentials file not found: {credentials_file}")
        exit(1)

    except HttpError as e:
        logger.error(f"❌ Google API HTTP error: {e}")
        exit(1)

    except Exception as e:
        logger.exception(f"❌ Failed to authenticate Google services: {e}")
        exit(1)

def load_document(doc_service, doc_id):
    """Load Google Document content safely."""
    try:
        doc = doc_service.documents().get(documentId=doc_id, includeTabsContent=True).execute()
        logger.info(f"📄 Loaded document '{doc.get('title')}' successfully.")
        return doc
    except HttpError as e:
        logger.error(f"❌ Google Docs API error: {e}")
        exit(1)
    except Exception as e:
        logger.exception(f"❌ Failed to load document {doc_id}: {e}")
        exit(1)


# sheet_service = build("sheets", "v4", credentials=creds)
# sheet = sheet_service.spreadsheets().values().get(
#                         spreadsheetId=spreadsheetId,
#                         range=f"{sheet_name}!A2:A"  # Column A
#                     ).execute()

# cities = sheet.get("values", [])   # it gives list of lists

# flattened_cities_list = [cell for row in cities for cell in row]
# # print(flattened_cities_list)
def load_cities(sheet_service, spreadsheet_id, sheet_name):
    """Retrieve list of cities from Google Sheet with fallback."""
    try:
        result = sheet_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A2:A"
        ).execute()

        cities = result.get("values", [])
        flattened = [cell for row in cities for cell in row]
        if not flattened:
            raise ValueError("No cities found in the sheet.")
        logger.info(f"📊 Retrieved {len(flattened)} cities from '{sheet_name}'.")
        return flattened

    except HttpError as e:
        logger.error(f"❌ Google Sheets API error: {e}")
        exit(1)
    except Exception as e:
        logger.exception(f"❌ Failed to load city list: {e}")
        exit(1)

PROGRESS_FILE = "progress.json"

# Load progress file (create empty dict if missing)
# if os.path.exists(PROGRESS_FILE):
#     with open(PROGRESS_FILE, "r") as f:
#         progress = json.load(f)
# else:
#     progress = {}

# if doc_id not in progress:
#     progress[doc_id] = []

def load_progress(progress_file, doc_id):
    """Load or initialize progress tracking file."""
    try:
        if os.path.exists(progress_file):
            with open(progress_file, "r") as f:
                progress = json.load(f)
        else:
            progress = {}

        if doc_id not in progress:
            progress[doc_id] = []
        return progress

    except json.JSONDecodeError:
        logger.warning("⚠️ Corrupted progress.json — resetting progress.")
        return {doc_id: []}
    except Exception as e:
        logger.exception(f"❌ Failed to load progress file: {e}")
        return {doc_id: []}

def save_progress(progress_file, progress):
    """Safely write progress updates to file."""
    try:
        with open(progress_file, "w") as f:
            json.dump(progress, f, indent=4)
    except Exception as e:
        logger.exception(f"⚠️ Failed to save progress: {e}")
'''
counter = {
            'processed_count' : 0,
            'skipped_count' : 0,
            'wrong_city_name_count' : 0,
            'wrong_internal_link_content_count' : 0,
            'empty_tab_count' : 0,
            'subtab_count' : 0
          }

tabs = doc.get("tabs", [])
total_tab_count = len(tabs)
logger.info(f"📄 Document ID: {doc_id} has {total_tab_count} tabs to process.")

# Loop through all tabs
for tab in tabs:
    
    html_content_dict = process_tab_and_child_tabs(tab, progress, flattened_cities_list, valid_urls, doc_id, logger, counter)
    
    for city_name, html_content in html_content_dict.items():

        page_title_format = os.getenv("page_title_format")
        key_phrase_format = os.getenv("key_phrase_format")
        description_format = os.getenv("description_format")
        country_name = os.getenv("COUNTRY_NAME")
        category_name = os.getenv("CATEGORY_NAME")
        brand_name = os.getenv("BRAND_NAME")

        page_title = page_title_format.format(category_name=category_name, city_name=city_name, brand_name=brand_name)
        key_phrase = key_phrase_format.format(category_name=category_name, city_name=city_name)
        description = description_format.format(category_name=category_name, city_name=city_name, country_name=country_name)

        response = post_to_wp(html_content, featured_img_url, page_title, brand_name, key_phrase, description, social_image, wp_url, wp_username, wp_app_pasword)

        if not response:
            continue 

        if response.status_code == 201:
            page_url = response.json()["link"]
            logger.info(f"✅ Page created successfully for {city_name}!")
            logger.info(f"Page URL: {page_url}")

            write_url_to_sheet(sheet_service, spreadsheetId, sheet_name, url_column, page_url, city_name, flattened_cities_list, logger)

            # Update progress
            progress[doc_id].append(city_name)
            counter['processed_count'] += 1

            # Save progress to file
            with open(PROGRESS_FILE, "w") as f:
                json.dump(progress, f, indent=4)
        else:
            logger.info(f"❌ Failed to create page for {city_name}. {response.status_code} - {response.text}")
            logger.info(f"Response: {response.text}")
'''

def process_document_tabs(doc, config, sheet_service, cities, progress):
    """Process all tabs and handle posting + sheet updates."""
    tabs = doc.get("tabs", [])
    total_tabs = len(tabs)
    logger.info(f"📄 Document contains {total_tabs} tabs.")

    counters = {
        'processed_count': 0,
        'skipped_count': 0,
        'wrong_city_name_count': 0,
        'wrong_internal_link_content_count': 0,
        'empty_tab_count': 0,
        'subtab_count': 0
    }

    for tab in tabs:
        try:
            html_content_dict = process_tab_and_child_tabs(
                tab, progress, cities, config["valid_urls"], config["doc_id"], logger, counters
            )

            for city_name, html_content in html_content_dict.items():
                try:
                    page_title = config["page_title_format"].format(
                        category_name=config["category_name"],
                        city_name=city_name,
                        brand_name=config["brand_name"]
                    )
                    key_phrase = config["key_phrase_format"].format(
                        category_name=config["category_name"],
                        city_name=city_name
                    )
                    description = config["description_format"].format(
                        category_name=config["category_name"],
                        city_name=city_name,
                        country_name=config["country_name"]
                    )

                    response = post_to_wp(
                        html_content,
                        config["featured_img_url"],
                        page_title,
                        config["brand_name"],
                        key_phrase,
                        description,
                        config["social_image"],
                        config["wp_url"],
                        config["wp_username"],
                        config["wp_app_password"]
                    )

                    if not response:
                        logger.warning(f"⚠️ No response for {city_name}. Skipping.")
                        continue

                    if response.status_code == 201:
                        page_url = response.json().get("link", "")
                        logger.info(f"✅ Created page for {city_name}: {page_url}")

                        write_url_to_sheet(
                            sheet_service,
                            config["spreadsheet_id"],
                            config["sheet_name"],
                            config["url_column"],
                            page_url,
                            city_name,
                            cities,
                            logger
                        )

                        progress[config["doc_id"]].append(city_name)
                        counters["processed_count"] += 1
                        save_progress(config["progress_file"], progress)

                    else:
                        logger.error(f"❌ Failed to post {city_name}: {response.status_code} - {response.text}")

                except Exception as e:
                    logger.exception(f"⚠️ Error processing city '{city_name}': {e}")

        except Exception as e:
            logger.exception(f"⚠️ Error processing tab: {e}")
            continue

    return counters, total_tabs

def log_summary(counters, total_tabs, doc_id):
    """Log summary after all processing."""
    # Summary after processing document
    logger.info(f"📊 =========================Summary for Document: {doc_id}================")
    logger.info(f"📄 Total tabs: {total_tabs} ")
    logger.info(f"✅ Processed new tabs: {counters['processed_count']}")
    logger.info(f"📄 Subtabs processed (not counted as new): {counters['subtab_count']}")
    logger.info(f"⏩ Skipped already processed: {counters['skipped_count']}")
    if counters['wrong_city_name_count'] > 0:
        logger.warning(f"⚠️ Tabs with wrong city names: {counters['wrong_city_name_count']}")
    if counters['empty_tab_count'] > 0:
        logger.warning(f"⚠️ Empty tabs skipped: {counters['empty_tab_count']}")
    if counters['wrong_internal_link_content_count'] > 0:
        logger.warning(f"⚠️ Tabs with wrong internal links: {counters['wrong_internal_link_content_count']}")


    if (counters['processed_count'] - counters['subtab_count'] == total_tabs and counters['wrong_city_name_count'] == 0 and counters['wrong_internal_link_content_count'] == 0) or (counters['processed_count'] + counters['skipped_count'] == total_tab_count and counters['wrong_city_name_count'] == 0 and counters['wrong_internal_link_content_count'] == 0 and counters['processed_count'] > 0 and counters['empty_tab_count'] == 0):
        logger.info(f"✅ All the {total_tabs} tabs with {counters['subtab_count']} subtabs of the document {doc_id} processed successfully.")

    elif counters['skipped_count'] == total_tabs:
        logger.info(f"ℹ️ All tabs already processed for this document {doc_id}.")

    else:
        logger.warning(f"⚠️ Document {doc_id} processing completed with mixed results. Something wrong with processing this doc. Check manually.")

    logger.info(f"*************************************************************************************************************")
    logger.info(f"*************************************************************************************************************")

def main():
    try:
        config = load_configuration()
        doc_service, sheet_service = get_google_services(config["google_credentials_file"])
        doc = load_document(doc_service, config["doc_id"])

        # Validate Meta Details
        if not validate_meta_details(doc.get("title"), config["country_name"], config["category_name"]):
            logger.error("❌ Meta validation failed. Check country/category in .env or document name.")
            exit(1)

        cities = load_cities(sheet_service, config["spreadsheet_id"], config["sheet_name"])
        progress = load_progress(config["progress_file"], config["doc_id"])

        counters, total_tabs = process_document_tabs(doc, config, sheet_service, cities, progress)
        log_summary(counters, total_tabs, config["doc_id"])

    except KeyboardInterrupt:
        logger.warning("⚠️ Process interrupted by user.")
        exit(1)
    except Exception as e:
        logger.exception(f"❌ Fatal error in main: {e}")
        exit(1)


if __name__ == "__main__":
    main()