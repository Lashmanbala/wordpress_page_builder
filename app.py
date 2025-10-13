import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import os

load_dotenv()  # loads .env into environment

USERNAME = os.getenv("USERNAME")
APP_PASSWORD = os.getenv("APP_PASSWORD")
WP_URL = "http://my-site.local/wp-json/wp/v2/pages"


response = requests.get(
    WP_URL,
    auth=HTTPBasicAuth(USERNAME, APP_PASSWORD)
)

try:
    print('Testing1...')
    response = requests.get(WP_URL, timeout=10)
    print('Testing2...')
    if response.status_code == 200:
        print("WordPress REST API is reachable")
        print(response.json())  # prints available routes
    else:
        print(f"Failed: {response.status_code}", response.text)
except Exception as e:
    print("Connection error:", e)

# if response.status_code == 200:
#     media_list = response.json()
#     for media in media_list:
#         print(f"ID: {media['id']} | Title: {media['title']['rendered']} | URL: {media['source_url']}")
# else:
#     print("Error:", response.status_code, response.text)