import requests
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup
from logging_config import logger

def post_to_wp(html_content, featured_img_url, page_title, brand_name, key_phrase, description, social_image, WP_URL, USERNAME, APP_PASSWORD):
    """Create a new WordPress post using REST API."""

    try:
                            
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
                "_yoast_wpseo_title": f"{page_title} | {brand_name}",
                "_yoast_wpseo_metadesc": f"{full_description}",
                "_yoast_wpseo_opengraph-image": social_image,
                "_yoast_wpseo_opengraph-title": f"{page_title} | {brand_name}",
                "_yoast_wpseo_opengraph-description": f"{full_description}",
                "_yoast_wpseo_twitter-image": social_image,
                "_yoast_wpseo_twitter-title": f"{page_title} | {brand_name}",
                "_yoast_wpseo_twitter-description": f"{full_description}"
            }
        }

        response = requests.post(
            WP_URL,
            auth=HTTPBasicAuth(USERNAME, APP_PASSWORD),
            json=page_data,
            timeout=30
        )

        return response
    
    except requests.exceptions.Timeout:
        logger.error(f"⏰ Timeout while posting '{page_title}' to WordPress.")
    except requests.exceptions.RequestException as re:
        logger.error(f"🌐 Request error during post_to_wp for '{page_title}': {re}")
    except Exception as e:
        logger.error(f"❌ Unexpected error in post_to_wp: {e}")

    return None


def update_new_content(city_name, html_content, WP_BASE, page_id, wp_username, wp_app_password, featured_img_url):
    """Update an existing WordPress post with new HTML content."""

    try:
        if not page_id:
            raise ValueError("Missing page_id for update request.")
        
        # Prepend featured image to content
        page_content = f'<img src="{featured_img_url}" alt="Featured Image" style="width:100%; height:auto;"/>\n' + html_content
        
        endpoint = f"{WP_BASE}/{page_id}"
        update_response = requests.post(
                            endpoint,
                            auth=HTTPBasicAuth(wp_username, wp_app_password),
                            json={"content": page_content},
                            timeout=30
                            )
        # if update_response.status_code == 200:
        #     logger.info(f"✅ Successfully updated '{city_name}' with page ID {page_id}.")
        # else:
        #     logger.error(
        #         f"❌ Failed to update {city_name} with page ID {page_id}: "
        #         f"{update_response.status_code} - {update_response.text}"
        #     )

        return update_response

    except requests.exceptions.Timeout:
        logger.error(f"⏰ Timeout while updating '{city_name}' with page ID {page_id}.")
    except requests.exceptions.RequestException as re:
        logger.error(f"🌐 Request error while updating '{city_name}' with page ID {page_id}: {re}")
    except Exception as e:
        logger.error(f"❌ Unexpected error in update_new_content: {e}")

    return None

'''
from bs4 import BeautifulSoup 
import requests 
from requests.auth import HTTPBasicAuth 

def post_to_wp(html_content, featured_img_url, page_title, brand_name, key_phrase, description, social_image, WP_URL, USERNAME, APP_PASSWORD): 
    # Content to post (HTML) 
    soup = BeautifulSoup(html_content, "html.parser") 
    first_p = soup.find("p").get_text(" ", strip=True) 
    # additional_description = first_p[:85] 
    additional_description = first_p[:100] 
    last_space = additional_description.rfind(" ") 
    
    # Find the last space before the cutoff 
    if last_space != -1: 
        additional_description = additional_description[:last_space] 
        full_description = f"{description} {additional_description}" 
        # Prepend featured image to content 
        page_content = f'<img src="{featured_img_url}" alt="Featured Image" style="width:100%; height:auto;"/>\n' + html_content 
        
        page_data = { 
            "title": page_title, 
            "content": page_content, 
            "status": "publish", 
            # "featured_media": 9, Id of the featured image in WordPress media library 
            "meta": { "_yoast_wpseo_focuskw": f"{key_phrase}", 
                        "_yoast_wpseo_title": f"{page_title} | {brand_name}", 
                        "_yoast_wpseo_metadesc": f"{full_description}", 
                        "_yoast_wpseo_opengraph-image": social_image, 
                        "_yoast_wpseo_opengraph-title": f"{page_title} | {brand_name}", 
                        "_yoast_wpseo_opengraph-description": f"{full_description}", 
                        "_yoast_wpseo_twitter-image": social_image, 
                        "_yoast_wpseo_twitter-title": f"{page_title} | {brand_name}", 
                        "_yoast_wpseo_twitter-description": f"{full_description}" } 
                        } 
        response = requests.post( WP_URL, auth=HTTPBasicAuth(USERNAME, APP_PASSWORD), json=page_data ) 
        return response 

def update_new_content(html_content, WP_BASE, page_id, wp_username, wp_app_password, featured_img_url): 
    # Prepend featured image to content 
    page_content = f'<img src="{featured_img_url}" alt="Featured Image" style="width:100%; height:auto;"/>\n' + html_content 

    update_res = requests.post( f"{WP_BASE}/{page_id}", 
                               auth=HTTPBasicAuth(wp_username, wp_app_password), 
                               json={ "content": page_content } 
                               ) 
    return update_res
'''