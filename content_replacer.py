from urllib.parse import urlparse

page_url = 'https://www.satheesseo.com/seo-consultant-in-mumbai-india/'

slug = urlparse(page_url).path.strip("/")

if not slug:
    print(ValueError("Invalid page URL — cannot extract slug."))
          
print(slug)  