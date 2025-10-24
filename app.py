from dotenv import load_dotenv
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from read import read_tab
from post import post_to_wp
from write_url import write_url_to_sheet
import json
from logging_config import logger
import re

load_dotenv()  # loads .env into environment

wp_username = os.getenv("WP_USERNAME")
wp_app_pasword = os.getenv("WP_APP_PASSWORD")
wp_url = os.getenv("WP_URL")
featured_img_url = os.getenv("FEATURED_IMAGE_URL")
social_image = os.getenv("SOCIAL_IMAGE_URL")

doc_id = os.getenv("DOC_ID")
spreadsheetId = os.getenv("SPREADSHEET_ID")
sheet_name = os.getenv("SHEET_NAME")  
valid_urls = os.getenv("VALID_URLS").split(", ")   # returns a list

google_credentisals_file = "doc-reader.json"

SCOPES = ["https://www.googleapis.com/auth/documents.readonly", "https://www.googleapis.com/auth/spreadsheets"]
creds = service_account.Credentials.from_service_account_file(google_credentisals_file, scopes=SCOPES)

doc_service = build("docs", "v1", credentials=creds)
doc = doc_service.documents().get(documentId=doc_id, includeTabsContent=True).execute()

def normalize(text):
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text)  # remove punctuation/symbols
    return set(text.lower().split())

doc_title = doc.get("title")
page_title_format = os.getenv("page_title_format")
key_phrase_format = os.getenv("key_phrase_format")
description_format = os.getenv("description_format")

# Normalize all strings
title_words = normalize(doc_title)
page_title_words = normalize(page_title_format)
key_phrase_words = normalize(key_phrase_format)
description_words = normalize(description_format)

# Check matches individually
title_match = title_words & page_title_words
key_match = title_words & key_phrase_words
desc_match = title_words & description_words

# Exit the program if any of them is False
if not (title_match and key_match and desc_match):
    logger.info("❌ page_title or key_phrase or description is not correct. please check...")
    raise Exception("Stopping script due to missing matches") 

sheet_service = build("sheets", "v4", credentials=creds)
sheet = sheet_service.spreadsheets().values().get(
                        spreadsheetId=spreadsheetId,
                        range=f"{sheet_name}!A2:A"  # Column A
                    ).execute()

cities = sheet.get("values", [])   # it gives list of lists

flat_cities_list = [cell for row in cities for cell in row]
# print(flat_cities_list)

PROGRESS_FILE = "progress.json"

# Load progress file (create empty dict if missing)
if os.path.exists(PROGRESS_FILE):
    with open(PROGRESS_FILE, "r") as f:
        progress = json.load(f)
else:
    progress = {}

if doc_id not in progress:
    progress[doc_id] = []

processed_count = 0
skipped_count = 0
wrong_city_name_count = 0
wrong_internal_link_content_count = 0

tabs = doc.get("tabs", [])
total_tab_count = len(tabs)
logger.info(f"📄 Document ID: {doc_id} has {total_tab_count} tabs to process.")

# Loop through all tabs
for tab in tabs:
    city_name = tab["tabProperties"]["title"]

    if city_name in progress[doc_id]:
        logger.info(f"⏩ Skipping already processed tab: {city_name}")
        skipped_count += 1
        continue

    if city_name not in flat_cities_list:
        logger.info(f"⚠️ City '{city_name}' not found in sheet. Skipping tab.")
        wrong_city_name_count += 1
        continue
    try:
        logger.info(f"Reading {city_name} tab content...")
        tab_content = tab["documentTab"]["body"]["content"]
        html_content = read_tab(tab_content, valid_urls)

        page_title_format = os.getenv("page_title_format")
        key_phrase_format = os.getenv("key_phrase_format")
        description_format = os.getenv("description_format")

        page_title = page_title_format.format(city_name=city_name)
        key_phrase = key_phrase_format.format(city_name=city_name)
        description = description_format.format(city_name=city_name)

        response = post_to_wp(html_content, featured_img_url, page_title, key_phrase, description, social_image, wp_url, wp_username, wp_app_pasword)
    
    except ValueError as ve:
        logger.warning(f"🚫 Skipping tab '{city_name}' due to invalid internal link: {ve}. Check all the internal links.")
        wrong_internal_link_content_count += 1
        continue

    if response.status_code == 201:
        page_url = response.json()["link"]
        logger.info(f"✅ Page created successfully for {city_name}!")
        logger.info(f"Page URL: {page_url}")

        write_res = write_url_to_sheet(sheet_service, spreadsheetId, sheet_name, page_url, city_name, cities)
        logger.info(write_res)

        # Update progress
        progress[doc_id].append(city_name)
        processed_count += 1

        # Save progress to file
        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f, indent=4)
    else:
        logger.info(f"❌ Failed to create page for {city_name}. {response.status_code} - {response.text}")
        logger.info(f"Response: {response.text}")

# Summary after processing document
logger.info(f"📊 ======= Summary for Document: {doc_id} =======")
logger.info(f"✅ Processed new tabs: {processed_count}")
logger.info(f"⏩ Skipped already processed: {skipped_count}")
logger.info(f"⏩ Tabs with wrong city names: {wrong_city_name_count}")
if wrong_internal_link_content_count > 0:
    logger.warning(f"⚠️ Tabs with wrong internal links: {wrong_internal_link_content_count}")

if (processed_count == total_tab_count and wrong_city_name_count == 0 and wrong_internal_link_content_count == 0) or (processed_count + skipped_count == total_tab_count and wrong_city_name_count == 0 and wrong_internal_link_content_count == 0 and processed_count > 0):
    logger.info(f"✅ All the {total_tab_count} tabs of the document {doc_id} processed successfully.")

elif skipped_count == total_tab_count:
    logger.info(f"ℹ️ All tabs already processed for this document {doc_id}.")

elif wrong_city_name_count > 0:
    logger.warning(f"⚠️ {wrong_city_name_count} city names in the tabs of the document {doc_id} mis-matched with the sheet cities.")

elif wrong_internal_link_content_count > 0:
    logger.warning(f"⚠️ {wrong_internal_link_content_count} tabs in the document {doc_id} have wrong internal links in the content.")

else:
    logger.warning(f"⚠️ Document {doc_id} processing completed with mixed results. Something wrong with processing this doc. Check manually.")

