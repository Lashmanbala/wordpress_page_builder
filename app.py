import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import os

from read import read_all_tabs

# load_dotenv()  # loads .env into environment

# USERNAME = os.getenv("USERNAME")
# APP_PASSWORD = os.getenv("APP_PASSWORD")
# WP_URL = "http://my-site.local/wp-json/wp/v2/pages"

# response = requests.get(
#     WP_URL,
#     auth=HTTPBasicAuth(USERNAME, APP_PASSWORD)
# )

# try:
#     print('Testing1...')
#     response = requests.get(WP_URL, timeout=10)
#     print('Testing2...')
#     if response.status_code == 200:
#         print("WordPress REST API is reachable")
#         print(response.json())  
#     else:
#         print(f"Failed: {response.status_code}", response.text)
# except Exception as e:
#     print("Connection error:", e)

doc_id = "1ADZc32YGPNHNYerCxwiRdZYEPOLJ8IXtqS-NLgxf9qo"
google_credentisals_file = "wp_page_builder/doc-reader.json"

html_content = read_all_tabs(doc_id, google_credentisals_file)
print(html_content)