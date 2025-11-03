from dotenv import load_dotenv
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from read import read_tab, validate_meta_details, process_tab_and_child_tabs
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
url_column = os.getenv("URL_COLUMN")  
valid_urls = os.getenv("VALID_URLS").split(", ")   # returns a list

google_credentisals_file = "doc-reader.json"

SCOPES = ["https://www.googleapis.com/auth/documents.readonly", "https://www.googleapis.com/auth/spreadsheets"]
creds = service_account.Credentials.from_service_account_file(google_credentisals_file, scopes=SCOPES)

doc_service = build("docs", "v1", credentials=creds)
doc = doc_service.documents().get(documentId=doc_id, includeTabsContent=True).execute()

doc_title = doc.get("title")
country_name = os.getenv("COUNTRY_NAME")
category_name = os.getenv("CATEGORY_NAME")
page_title_format = os.getenv("page_title_format")
key_phrase_format = os.getenv("key_phrase_format")
description_format = os.getenv("description_format") 

try:
    if not validate_meta_details(doc_title, country_name, category_name):
        raise Exception ("Meta validation failed")
except Exception as e:
    logger.error("❌ country_name or category_name is not correct. please check them in the .env file... Or you have given wrong document...check the doc name")
    exit(1)  # stops further execution

sheet_service = build("sheets", "v4", credentials=creds)
sheet = sheet_service.spreadsheets().values().get(
                        spreadsheetId=spreadsheetId,
                        range=f"{sheet_name}!A2:A"  # Column A
                    ).execute()

cities = sheet.get("values", [])   # it gives list of lists

flattened_cities_list = [cell for row in cities for cell in row]
# print(flattened_cities_list)

PROGRESS_FILE = "progress.json"

# Load progress file (create empty dict if missing)
if os.path.exists(PROGRESS_FILE):
    with open(PROGRESS_FILE, "r") as f:
        progress = json.load(f)
else:
    progress = {}

if doc_id not in progress:
    progress[doc_id] = []

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

            write_res = write_url_to_sheet(sheet_service, spreadsheetId, sheet_name, url_column, page_url, city_name, flattened_cities_list)
            logger.info(write_res)

            # Update progress
            progress[doc_id].append(city_name)
            counter['processed_count'] += 1

            # Save progress to file
            with open(PROGRESS_FILE, "w") as f:
                json.dump(progress, f, indent=4)
        else:
            logger.info(f"❌ Failed to create page for {city_name}. {response.status_code} - {response.text}")
            logger.info(f"Response: {response.text}")

# Summary after processing document
logger.info(f"📊 =========================Summary for Document: {doc_id}================")
logger.info(f"📄 This document has {total_tab_count} tabs")
logger.info(f"✅ Processed new tabs: {counter['processed_count']}")
logger.info(f"📄 Subtabs processed (not counted as new): {counter['subtab_count']}")
logger.info(f"⏩ Skipped already processed: {counter['skipped_count']}")
if counter['wrong_city_name_count'] > 0:
    logger.info(f"⚠️ Tabs with wrong city names: {counter['wrong_city_name_count']}")
if counter['empty_tab_count'] > 0:
    logger.info(f"⚠️ Empty tabs skipped: {counter['empty_tab_count']}")
if counter['wrong_internal_link_content_count'] > 0:
    logger.info(f"⚠️ Tabs with wrong internal links: {counter['wrong_internal_link_content_count']}")


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
