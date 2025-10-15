from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/documents.readonly"]

creds = service_account.Credentials.from_service_account_file(
            "/home/bala/wp_page_builder/doc-reader.json", scopes=SCOPES
        )

service = build("docs", "v1", credentials=creds)

DOCUMENT_ID = "1ADZc32YGPNHNYerCxwiRdZYEPOLJ8IXtqS-NLgxf9qo"

doc = service.documents().get(documentId=DOCUMENT_ID, includeTabsContent=True).execute()

# HELPER FUNCTION: Convert Paragraphs to HTML
def get_text_with_formatting_html(paragraph):
    text_parts = []
    for element in paragraph.get("elements", []):
        if "textRun" in element:
            txt = element["textRun"]["content"]
            style = element["textRun"].get("textStyle", {})

            # Handle hyperlinks
            if "link" in style and style["link"].get("url"):
                url = style["link"]["url"]
                txt = f'<a href="{url}">{txt.strip()}</a>'

            # Apply bold/italic
            if style.get("bold"):
                txt = f"<strong>{txt}</strong>"
            if style.get("italic"):
                txt = f"<em>{txt}</em>"

            text_parts.append(txt)
    return "".join(text_parts).strip()


# Loop through all tabs
for tab in doc.get("tabs", []):
    tab_title = tab["tabProperties"]["title"]
    print(f"\n=== {tab_title} ===\n")

    tab_content = tab["documentTab"]["body"]["content"]
    html_lines = []

    for content in tab_content:
        if "paragraph" not in content:
            continue
        paragraph = content["paragraph"]
        text = get_text_with_formatting_html(paragraph)
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

    # Combine list items into <ul> if needed
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
    print(html_content)
