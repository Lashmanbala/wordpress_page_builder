import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from read import read_tab

# load_dotenv()  # loads .env into environment

# USERNAME = os.getenv("USERNAME")
# APP_PASSWORD = os.getenv("APP_PASSWORD")
# WP_URL = "http://my-site.local/wp-json/wp/v2/pages"



doc_id = "1ADZc32YGPNHNYerCxwiRdZYEPOLJ8IXtqS-NLgxf9qo"
google_credentisals_file = "doc-reader.json"

SCOPES = ["https://www.googleapis.com/auth/documents.readonly"]

creds = service_account.Credentials.from_service_account_file(google_credentisals_file, scopes=SCOPES)

service = build("docs", "v1", credentials=creds)

doc = service.documents().get(documentId=doc_id, includeTabsContent=True).execute()

# Loop through all tabs
for tab in doc.get("tabs", []):
    tab_title = tab["tabProperties"]["title"]
    tab_content = tab["documentTab"]["body"]["content"]
    html_content = read_tab()
    print(html_content)
