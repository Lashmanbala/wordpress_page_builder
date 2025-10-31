from urllib.parse import urlparse
import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv

load_dotenv()  # loads .env into environment

wp_username = os.getenv("WP_USERNAME")
wp_app_pasword = os.getenv("WP_APP_PASSWORD")
WP_BASE = os.getenv("WP_URL")

page_url = 'https://www.loclite.co.uk/top-rated-electricians-in-aberdeen/'

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