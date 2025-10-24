import re

# Convert Paragraphs to HTML
def text_to_html(paragraph, valid_urls):
    text_parts = []
    for element in paragraph.get("elements", []):
        if "textRun" in element:
            txt = element["textRun"]["content"]
            # re.sub(r'[\x00-\x1F\x7F-\x9F]', '', txt)   # Remove control characters except newlines
            # txt = txt.replace("\u2028", " ")  # Line separator
            # txt = txt.replace("\u2029", " ")  # Paragraph separator
            # txt = txt.replace("\u00A0", " ")  # Non-breaking space
            # txt = txt.replace("\u200B", "")   # Zero-width space
            # txt = txt.replace("\r", " ")      # Carriage return
            # txt = txt.replace("\n", " ")      # Line feed
            # txt = txt.replace("\v", " ")      # Vertical tab (“” issue)
            # txt = txt.replace("\f", " ")      # Form feed
            txt = re.sub(r"[\u2028\u2029\u00A0\r\n\v\f]", " ", txt)
            
            style = element["textRun"].get("textStyle", {})

            # Handle hyperlinks
            if "link" in style and style["link"].get("url"):
                url = style["link"]["url"]

                if url not in valid_urls:      # stops processing the tab bcz of invalid url
                    raise ValueError(f'{url}')
                    
                txt = f'<a href="{url}">{txt.strip()}</a>'

            # Apply bold/italic
            if style.get("bold"):
                txt = f"<strong>{txt}</strong>"
            if style.get("italic"):
                txt = f"<em>{txt}</em>"

            text_parts.append(txt)
    return "".join(text_parts).strip()



def read_tab(tab_content, valid_urls):
  
    html_lines = []

    for content in tab_content:
        if "paragraph" not in content:
            continue
        paragraph = content["paragraph"]
        text = text_to_html(paragraph, valid_urls)
        if not text:
            continue

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

