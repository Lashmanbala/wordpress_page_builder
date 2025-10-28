from bs4 import BeautifulSoup
import requests
from requests.auth import HTTPBasicAuth


def post_to_wp(html_content, featured_img_url, page_title, key_phrase, description, social_image, WP_URL, USERNAME, APP_PASSWORD):

    # Content to post (HTML)
    soup = BeautifulSoup(html_content, "html.parser")
    first_p = soup.find("p").get_text(" ", strip=True)

    # additional_description = first_p[:85]

    additional_description = first_p[:100]
    
    last_space = additional_description.rfind(" ")  # Find the last space before the cutoff

    if last_space != -1:
        additional_description = additional_description[:last_space]

    full_description = f"{description} {additional_description}"

    # Prepend featured image to content
    page_content = f'<img src="{featured_img_url}" alt="Featured Image" style="width:100%; height:auto;"/>\n' + html_content

    page_data = {
        "title": page_title,
        "content": page_content,
        "status": "publish",
        # "featured_media": 9,  Id of the featured image in WordPress media library
        "meta": {
            "_yoast_wpseo_focuskw": f"{key_phrase}",
            "_yoast_wpseo_title": f"{page_title}",
            "_yoast_wpseo_metadesc": f"{full_description}",
            "_yoast_wpseo_opengraph-image": social_image,
            "_yoast_wpseo_opengraph-title": f"{page_title}",
            "_yoast_wpseo_opengraph-description": f"{full_description}",
            "_yoast_wpseo_twitter-image": social_image,
            "_yoast_wpseo_twitter-title": f"{page_title}",
            "_yoast_wpseo_twitter-description": f"{full_description}"
        }
    }

    response = requests.post(
        WP_URL,
        auth=HTTPBasicAuth(USERNAME, APP_PASSWORD),
        json=page_data
    )

    return response
