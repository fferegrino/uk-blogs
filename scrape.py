import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
import json


def get_scraped_urls():
    """Gets a list of the previously scraped urls from the index file"""
    scraped_urls = []
    if os.path.exists("scraped_urls.txt"):
        with open("scraped_urls.txt") as url_file:
            for line in url_file:
                scraped_urls.append(line.strip())
    return scraped_urls


def append_scrapped_urls(urls):
    """Appends newly scraped urls to the index file"""
    with open("scraped_urls.txt", "a") as url_file:
        for url in urls:
            url_file.write(url)
            url_file.write("\n")


def get_urls(page):
    """Fetches a list of urls scraped from the page number received as an argument"""
    final_url = f"https://www.blog.gov.uk/all-posts/page/{page}"
    page_response = requests.get(final_url)

    soup = BeautifulSoup(page_response.text)
    blog_list = soup.find("ul", {"class": "blogs-list"})
    entries = blog_list.find_all("li")

    if entries[0].get("class") != ["noresults"]:
        anchors = [entry.select_one("h3 > a") for entry in entries]
        hrefs = [a["href"] for a in anchors]
        return hrefs
    else:
        return None


existing_urls = set(get_scraped_urls())

urls_to_scrape = []
# From one to one million
for current_page in range(1, 1_000_000):
    urls = get_urls(current_page)

    # Until we no longer have urls
    if not urls:
        break

    for url in urls:
        # Or we find an url that we already processed
        if url in existing_urls:
            break
        urls_to_scrape.append(url)


def process_header(header):
    """Process the header of the post, returning a dictionary of the relevant information"""
    title = header.find("h1").text
    authors = [span.text for span in header.find("div").find_all("a", {"rel": "author"})]
    categories = [span.text for span in header.find("div").find_all("a", {"rel": "category tag"})]
    time = header.find("div").find("time")["datetime"]
    header_content = {
        "title": title,
        "authors": authors,
        "categories": categories,
        "pub_date": time,
    }
    return header_content


def process_content(content):
    """Process the content of the post, returning a dictionary of the relevant information"""
    content_breakdown = []
    for child in content.find_all(recursive=False):
        if not child.text:
            continue
        if child.name == "p":
            content_breakdown.append({"text": child.text})
        elif child.name.startswith("h"):
            content_breakdown.append({"heading": int(child.name[1:]), "text": child.text})
    article_content = {"content": content_breakdown}
    return article_content


def get_article(url):
    """Scrapes the article returning a dictionary of result of processing"""
    article_response = requests.get(url)
    article_soup = BeautifulSoup(article_response.text)
    article = article_soup.find("article")

    header = article.find("header")
    content = article.find("div", {"class": "entry-content"})

    header_content = process_header(header)
    article_content = process_content(content)

    return {"url": url, **header_content, **article_content}


def get_local_path(processed_article):
    """Creates a path from the date and url of a given article"""
    pub_date = datetime.fromisoformat(processed_article["pub_date"])
    _, _, file_name = processed_article["url"].strip("/").rpartition("/")
    return Path(pub_date.strftime("%Y/%m/%d"), file_name + ".json")


def save_json(processed_article, local_path):
    """Saves the article as a json file, using `local_path` as a suggestion of where to store it"""
    final_path = Path("data", local_path)
    final_path.parent.mkdir(exist_ok=True, parents=True)
    with open(final_path, "w", encoding="utf8") as w:
        json.dump(processed_article, w, indent=4)


for post_url in urls_to_scrape:
    processed = get_article(post_url)
    local_path = get_local_path(processed)
    save_json(processed, local_path)


append_scrapped_urls(reversed(urls_to_scrape))
