import re
from logging_config import logger

def validate_meta_details(doc_title, country_name, category_name):
    """Check if both country and category names exist in the document title."""
    try:   
        cleaned_title = re.sub(r"[^a-zA-Z0-9]+", " ", doc_title) 
        title_words_set = set(cleaned_title.lower().split())
        country_name_set = set(country_name.lower().split())
        category_name_set = set(category_name.lower().split())
        
        is_valid = country_name_set.issubset(title_words_set) and category_name_set.issubset(title_words_set)
        return is_valid
    
    except Exception as e:
        logger.error(f"❌ Error during meta details validation: {e}")
        return False


def remove_emojis_and_symbols(text):
    """Remove emojis, logos, and symbol-like characters safely."""

    try:  
        emoji_pattern = re.compile(     # Pattern to remove emojis, pictographs, flags, and symbols
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002700-\U000027BF"  # Dingbats
            "\U000024C2-\U0001F251"  # Enclosed characters
            "\U0001F900-\U0001F9FF"  # Supplemental Symbols
            "\U0001FA70-\U0001FAFF"  # Symbols & pictographs extended
            "]+",
            flags=re.UNICODE
        )
        
        logo_symbols_pattern = re.compile(r"[™©®℠]+", flags=re.UNICODE)  # Pattern to remove special logo-like symbols (™️, ©, ®, ℠)

        # Remove both emojis and logo symbols
        text = emoji_pattern.sub("", text)
        text = logo_symbols_pattern.sub("", text)

        return text.strip()
    
    except re.error as regex_err:
        logger.error(f"❌ Regex failure in remove_emojis_and_symbols: {regex_err}")
        return text
    except Exception as e:
        logger.error(f"❌ Unexpected error in remove_emojis_and_symbols: {e}")
        return text


def fix_url(url):
    """Normalize URLs to a standard https://www. format."""
    try:  
#         url = re.sub(r"(https://)+", "https://", url)   # Remove all extra https:// and www.
#         url = re.sub(r"(www\.)+", "www.", url)

#         if not url.startswith("https://www."):      # Ensure it starts correctly
#             url = re.sub(r"^(https://)?(www\.)?", "", url)   # Remove stray prefixes if present
#             url = "https://www." + url

        if not url.endswith("/"):       # Ensure it ends with /
            url += "/"

        return url.strip()
    except Exception as e:
        logger.error(f"❌ Error in fix_url for '{url}': {e}")


def text_to_html(paragraph, valid_urls):
    """Convert paragraph elements into valid HTML."""

    text_parts = []
    try:
        for element in paragraph.get("elements", []):
            if "textRun" in element:
                txt = element["textRun"]["content"]

                txt = re.sub(r"[\u2028\u2029\u00A0\r\n\v\f]", " ", txt)   # removes invisible charecters
                txt = re.sub(r':(?!\s)', ': ', txt)    # add space after colon if not present
                
                style = element["textRun"].get("textStyle", {})

                # Handle hyperlinks
                if "link" in style and style["link"].get("url"):
                    url = style["link"]["url"]
                    url = fix_url(url)

                    if url not in valid_urls:      # stops processing the tab bcz of invalid url
                        raise ValueError(f'{url}')
                        
                    txt = f' <a href="{url}">{txt.strip()}</a>'   # Prepended a space to keep normal text and the internal link seperated in a line.

                # Apply bold/italic
                if style.get("bold"):
                    txt = f"<strong>{txt}</strong>"
                if style.get("italic"):
                    txt = f"<em>{txt}</em>"

                text_parts.append(txt)
        return "".join(text_parts).strip()
    
    except ValueError:
        # Let invalid internal-link errors pass through to caller (so the tab gets skipped)
        raise
    except Exception as e:
        # Log unexpected exceptions and re-raise so they don't get silently ignored.
        logger.error(f"❌ Unexpected error in text_to_html: {e}")
        raise

def read_tab(tab_content, valid_urls):
    """Convert all paragraphs in a tab into clean HTML."""
    html_lines = []

    try:  
        for content in tab_content:
            if "paragraph" not in content:
                continue

            paragraph = content["paragraph"]
            text = text_to_html(paragraph, valid_urls)

            if not text:
                continue

            text = remove_emojis_and_symbols(text)

            # Headings
            style = paragraph.get("paragraphStyle", {}).get("namedStyleType", "")
            if style.startswith("HEADING_"):
                level = int(style.split("_")[1])
                html_lines.append(f"<h{level}>{text}</h{level}>")
                continue

            # Bullets / Numbered Lists
            if "bullet" in paragraph:
                html_lines.append(f"<li>{text}</li>")
                continue

            # Normal paragraph
            html_lines.append(f"<p>{text}</p>")

        # Combine list items into <ul> tags
        html_output = []
        inside_list = False
        for line in html_lines:
            if line.startswith("<li>") and not inside_list:
                html_output.append("<ul>")
                inside_list = True
            elif not line.startswith("<li>") and inside_list:
                html_output.append("</ul>")
                inside_list = False
            html_output.append(line)
        if inside_list:
            html_output.append("</ul>")

        html_content = "\n".join(html_output)
        
        return html_content
    except ValueError:
        # Let invalid internal link errors bubble up to process_tab_and_child_tabs
        raise


def process_tab_and_child_tabs(tab, progress, flat_cities_list, valid_urls, doc_id, logger, counter):
   
    global skipped_count, wrong_city_name_count, empty_tab_count, wrong_internal_link_content_count

    city_name = tab["tabProperties"]["title"].capitalize().strip()
        
    if city_name in progress[doc_id]:
        logger.info(f"⏩ Skipping already processed tab: '{city_name}'")
        counter['skipped_count'] += 1
        return {}

    if city_name not in flat_cities_list:
        logger.info(f"⚠️ City '{city_name}' not found in sheet. Skipping tab.")
        counter['wrong_city_name_count'] += 1
        return {}

    try:
        logger.info(f"Reading '{city_name}' tab content...")
        tab_content = tab["documentTab"]["body"]["content"]

        html_content = read_tab(tab_content, valid_urls)

        html_content_dict = {}
        html_content_dict.update({city_name: html_content})

        if not html_content.strip():     # checks if the content is empty. If so skipping the tab
            logger.warning(f"🈳 Tab '{city_name}' is empty. Skipping...")
            counter['empty_tab_count'] += 1
            return {}
    
        subtabs_list = tab.get("childTabs")

        if subtabs_list:
            logger.info(f"Found {len(subtabs_list)} child tab/tabs in '{city_name}'. Recursing...")

            for subtab in subtabs_list:
               subtab_html_dict = process_tab_and_child_tabs(subtab, progress, flat_cities_list, valid_urls, doc_id, logger, counter)
               html_content_dict.update(subtab_html_dict)
               counter['subtab_count'] += 1
               
        return html_content_dict

    except ValueError as ve:
        logger.warning(f"🚫 Skipping tab '{city_name}' due to invalid internal link: {ve}. Check all the internal links.")
        counter['wrong_internal_link_content_count'] += 1
        return {}