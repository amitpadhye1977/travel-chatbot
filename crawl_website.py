import requests
from bs4 import BeautifulSoup
from xml.etree import ElementTree as ET

SITEMAP_URL = "https://www.ashtavinayak.net/sitemap.xml"


def get_urls():
    response = requests.get(SITEMAP_URL, timeout=30)
    response.raise_for_status()

    root = ET.fromstring(response.content)

    urls = []

    for element in root.iter():
        if element.tag.endswith("loc"):
            url = element.text.strip()

            if url.startswith("http"):
                urls.append(url)

    return urls


def extract_text(url):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        for tag in soup([
            "script",
            "style",
            "noscript",
            "header",
            "footer"
        ]):
            tag.decompose()

        text = soup.get_text(
            separator=" ",
            strip=True
        )

        return text

    except Exception as e:
        print(f"Error processing {url}: {e}")
        return ""


def build_knowledge_file():
    urls = get_urls()

    print(f"Found {len(urls)} URLs")

    knowledge = []

    for url in urls:
        print(f"Processing: {url}")

        content = extract_text(url)

        if len(content) > 500:
            knowledge.append(
                "\n\n========================\n"
                f"URL: {url}\n"
                "========================\n\n"
                + content
            )

    with open(
        "knowledge.txt",
        "w",
        encoding="utf-8"
    ) as f:
        f.write("\n".join(knowledge))

    print("knowledge.txt generated successfully")


if __name__ == "__main__":
    build_knowledge_file()
