UK Blogs Web Scraper
====================

## Set up your environment

### Git

Since this post talks about GitHub, navigate to a new folder and initialise a Git repository in it. This is a crucial 
part of our work since both our code and dataset will live in a git repo, in the cloud thanks to GitHub.

### Python

You obviously want to use a virtual environment, create one using your favourite tool, I usually go for Poetry or 
Pipenv, but for this tutorial I will use vanilla Python:

```shell
python -m venv .venv
```

Since you are doing web scraping, you will need to add some basic dependencies. My suggestion would be to have
something to make http requests, and something to parse those requests:

```
beautifulsoup4
requests
```

Finally add a `.gitignore` file, this one is entirely up to you but make sure you don't commit any user-specific info 
or any virtual environment files.

## Identify your (first) target

You want a web page that is static, does not require JavaScript to execute any logic. Single Page Apps, those with 
infinite scroll are difficult to scrape using the methods I will discuss here.

The first thing to keep in mind is that you want a website that offers an index since this is the entrypoint to scrape
the website, and is the page that will tell you if there is anything new to scrape.

In my case, I put my crosshairs on the [UK Government Blogs index](https://www.blog.gov.uk) a page that aggregates all
content posted across all blogs related to the UK government, from now on I will refer to this page as _"the index"_. 

### URL

Look at the address bar, the best URLs to crawl are those that follow a pattern and are "deterministic" in nature.

For example, all of these:

 - https://www.blog.gov.uk/all-posts/page/1
 - https://www.blog.gov.uk/all-posts/page/2
 - https://www.blog.gov.uk/all-posts/page/1000

Work and direct to a valid website. The URL remains largely the same, only an integer changes from one to the other.

### Inspect is your friend

In most modern browsers you can right click anywhere on the page and select the option _Inspect_. This will allow you 
to interact with the source code of the web page. When web scraping content it is a crucial step to identify where the
interesting content is.

### Identify how the index looks on a page with content

Inspecting the first page of the index, you can start to unravel the structure of the page. It has many entries, where 
each entry is contained within a `li` html tag, these `li` elements are wrapped in a `ul` element that has 
`class="blogs-list"` as an attribute. This is great news, we will be able to scrape these very easily.

If you check further, inside every `li` there is an `a` with the url pointing to the full post, we need that url to scrape
its contents. And that is our goal for this first target.

### Identify how the index looks when there is no content

Another key part is to identify how a page with no content looks like, since a page with no content will be useful to 
identify when we have reached the end of the index. 

Change the url to a page that is unlikely to exist, for example the 1 millionth page:www.blog.gov.uk/all-posts/page/1000000 
from there, inspect the page as we did previously and you will notice that while the `<ul class="blogs-list">` is still 
there, now it contains a single `li` element with `"noresults"` as `class` attribute. More great news! it will be easy 
to know when to stop crawling.

## A slight detour (do not repeat yourself!)

Before moving on, we need to make sure we do not keep scraping the same URLs over and over again, so we need a way to 
keep track of which one we have already processed. 

In a larger system we could use a proper database, but for our small-scale project, we will have a single text file (I 
named ours `scraped_urls.txt`), where each line is a processed url, for example:

```
https://food.blog.gov.uk/2022/08/04/chairs-stakeholder-update-how-the-fsa-is-supporting-free-trade-agreements/
https://space.blog.gov.uk/2022/08/04/how-i-made-it-to-mission-control/
https://ruralpayments.blog.gov.uk/2022/08/04/rpa-is-supporting-farm-24/
https://forestrycommission.blog.gov.uk/2022/08/04/reducing-the-impact-of-deer-on-the-natural-environment-consultation-opens/
https://companieshouse.blog.gov.uk/2022/08/04/our-new-powers-a-milestone-year-at-companies-house/
```

We need a couple of methods to interact with this file, one to get the urls that already exist in the file:

```python
import os

def get_scraped_urls():
    urls = []
    if os.path.exists("scraped_urls.txt"):
        with open("scraped_urls.txt") as url_file:
            for line in url_file:
                urls.append(line.strip())
    return urls
```

And another one to append urls to the file:

```python
def append_scrapped_urls(urls):
    with open("scraped_urls.txt", "a") url_file:
        url_file
```


## Scrape your first target

The goal of scraping our first target is to build an index of pages that we need to scrape in detail. Think of it as a 
list of pending jobs.

Let's create a function that takes in a page number and returns the urls of the article that page displays:

```python
def get_urls(page):
    final_url = f"https://www.blog.gov.uk/all-posts/page/{page}"
    page_response = requests.get(final_url)    

    soup = BeautifulSoup(page_response.text)
    blog_list = soup.find("ul", {"class": "blogs-list"})
    entries = blog_list.find_all('li')

    if entries[0].get('class') != ['noresults']:
        anchors = [entry.select_one("h3 > a") for entry in entries ]
        hrefs = [a['href'] for a in anchors]
        return hrefs
    else:
        return None
```

Keep in mind that this function will return the urls as they appear on the webpage, which most lilely will be from the 
newest to the oldest, so you may want to reverse the result to process the oldest urls first.

Then we can use this function to crawl across pages from page 1 in a for loop until one of two conditions are met: 
 
 - There are no more articles available, or
 - we get a url that we have already crawled


```python
existing_urls = set(get_scraped_urls())

new_urls = []
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
        new_urls.append(url)
```

By this point, we should have a list (above named `new_urls`) that contains a list of urls that we have not scraped yet.
This list is sorted from newest to oldest.

## Identify your second target

The urls above point to the full article, which is the actual content we are after with our tiny scraping project. The 
next step is to investigate the contents of each article, remember to use the _Inspect tool_ to find the structure of 
the page.

An initial look shows us that the article contains basic details such as title, author, published date, categories, 
followed by the actual content. 

_Inspecting_ the file reveals that every interesting bit we care about exists within an `article` tag, and from there we
can navigate to the `header` tag to get the "metadata" for the post, while the content exists in a `div` classed as 
`entry-content`, sometimes in `p` tags others in `h*` tags. 

Websites that are properly structured are a bliss to work with, this is one of them, still make sure you review a few 
different urls to account for every possible variation:

For example, there are articles with [multiple authors](https://nationalscreening.blog.gov.uk/2022/08/01/guidance-on-evaluating-ai-for-use-in-breast-screening/), there are some with [multiple tags](https://civilservice.blog.gov.uk/2022/07/28/top-tips-on-delivering-digital-projects-with-global-partners/). I came across some that had lists and tables in the [article body](https://homeofficemedia.blog.gov.uk/2022/07/28/windrush-compensation-scheme-factsheet-july-2022/). For now, Let's just follow a simplistic approach of dealing with articles, only text will be preserved.

### Division of concerns

We could create a mega-function that takes care of the article on its own, but I always find it better to create small 
functions that can tackle specific sections of the page's content at the time. For example, we can have a couple of 
functions: one for the header and another for the content:

```python
def process_header(header):
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
```

```python
def process_content(content):
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
```

### Putting everything together

```python
def get_article(url):
    article_response = requests.get(url)
    article_soup = BeautifulSoup(article_response.text)
    article = article_soup.find("article")

    header = article.find("header")
    content = article.find("div", {"class": "entry-content"})

    header_content = process_header(header)
    article_content = process_content(content)

    return {"url": url, **header_content, **article_content}
```

By the end, for each url, there will be a dictionary more or less like this:

```json
{
    "url": "https://naturalengland.blog.gov.uk/...",
    "title": "Natural England's ...",
    "authors": ["Ginny Swaile"],
    "categories": ["Biodiversity", "Wildlife"],
    "pub_date": "2022-08-04T16:22:57+01:00",
    "content": [
        {
            "text": "By Ginny Swaile, Deputy Director Science - Sustainable land and sea use"
        }
    ]
}
```

### Saving an article

We need to store this file locally, to do this, we should come up with a file structure that makes sense for our use 
case. My initial suggestion would be to include the date of the post somewhere in the local path for improved 
organisation. We can come up with something like the following:

```python
def get_local_path(processed_article):
    pub_date = datetime.fromisoformat(processed_article['pub_date'])
    _, _, file_name = processed_article['url'].strip("/").rpartition("/")
    return Path(date.strftime("%Y/%m/%d"), file_name + ".json")
```

It takes a parsed post and creates a unique name for it containing the date it was published on.

Last thing we need to do is create a method that saves a json file to a local directory. In this case, I am saving 
everything inside a folder called `data` as an indented JSON file:

```python
def save_json(processed_article, local_path):
    final_path = Path('data', local_path)
    final_path.parent.mkdir(exist_ok=True, parents=True)
    with open(final_path, "w", encoding='utf8') as w:
        json.dump(processed_article, w, indent=4)
```

### Crawling and storing

Now almost all the pieces are in place, we can start scrapping each individual post using a simple for loop:

```python
for post_url in new_urls:
    processed = get_article(post_url)
    local_path = get_local_path(processed)
    save_json(processed, local_path)
```

Finally, we need to keep track of the articles we already scraped. At the beginning of the article we created a function
named `append_scrapped_urls`, that updates the `scraped_urls.txt` file with the newly scrapped urls. Just remember to 
reverse the list since the urls we just scraped are sorted from new to old, but the index file is stored from old to new:

```python
append_scrapped_urls(reversed(new_urls))
```

After this, we are done with Python, but we are not done yet, we need to actually start running the scraping, initially
manual and locally just so that we can process all the historical data only to then leave it to GitHub Actions to scrape
data incrementally on a daily basis.

```shell
python scrape.py
```

Then add all your code and data files to a commit and push it to your repository. You will probably have a gigantic commit, 
mine contained about 2700 new files. It may seem like a lot, but they're plain text files, so it is not a massive problem.

## Automate everything everywhere all at once with GitHub Actions

The next stop in this journey is to automate all we just did, and it is achievable using Actions.

### Cron

Think about the schedule you want the scraping to happen, the rule here is do not overdo it. The blog posts across all 
government websites are a daily ocurrence, so to me, it makes sense to scrape the website once a day. But some other tasks
may be better served by scraping every hour, or every week. Whatever you decide, you need to codify the schedule using a cron
expression.

I want the scraping to happen at 7 PM once a day, so the expression is `0 19 * * *`. Check [crontab gury](crontab.guru) for 
more info on cron expression and an interactive way to create yours.

### Actions

GitHub actions allows us to execute workflows that run in virtual servers, the execution of these workflows can be triggered by
a number of conditions: on a schedule, as a response to an event (like a pull request) or even by a request from a user.

The workflows are defined via _YAML_ files inside a special folder (`.github/workflows`) at the root of your repository, the
workflows follow a schema that is very complex since they allow for complex configurations; but for our purposes, we do not need 
such complexity. 

The beginning of our workflow ( appropiately named `scrape.yml`), begins with basic info about the name and schedule of when it 
should be executed:

```yaml
name: "Daily scrape"

on:
  schedule:
  - cron: "0 19 * * *"
```

Then we need to define the jobs that will be part of it. We will have a single job called `scrape` that will run on a virtual machine
using a fairly recent Ubuntu distribution:


```yaml
jobs:
  scrape:
    runs-on: ubuntu-latest
```

Each job is formed of several steps, each step specify what commands will be executed on the virtual machine. But not every
step has to be programmed by us, there are some useful shorthands that people have already made for us known as _actions_. 

In fact, first we need two _actions_: `checkout@v2` y `setup-python@v2`, to create a copy of our repo and install Python, 
respectively:

```yaml
    steps:
    - uses: actions/checkout@v2

    - name: Set up Python 3.9
      uses: actions/setup-python@v2
      with:
        python-version: "3.9"
```

Then we move on to the steps that we actually programmed, each step has its own name wich is descriptive on its own: 

```yaml
    - name: Install dependencies
      run: |
        pip install --upgrade pip
        pip install -r requirements.txt

    - name: Execute scrape.py
      run: python scrape.py

    - name: Commit changes
      run: |
        git config --global user.email "antonio.feregrino+datasets@gmail.com"
        git config --global user.name "Antonio Feregrino"
        git add data/ scraped_urls.txt
        git diff --staged --quiet || git commit -m 'New blog posts'
        git push
```

That one last step requires more explanation, since we are making a commit to our own repo! yes, it is possible and needed
when you want to save information generated during the workflow execution. Let me dissect the command:

**`git config` × 2**

It configures git with the email and name of the commiiting user, this is necessary as otherwise git will not allow us
to create commits. My recomendation is that you do not use your normal email, as this will blow up artificially your commit
count.

**`git add`**

We obviously need to add the data we just generated. Both the `data` folder and the `scraped_urls.txt` file should contain new 
information so we need to stage them before making a commit.

**`git dif ...`**

The chained commands `git diff --staged --quiet || git commit -m 'New blog posts'` will generate a new git commit if, and 
only if there are changes staged for commit. With the previous `git add` we are staged any changes, so if there were new
blog posts, they should be ready to be commited.

**`git push`**

Finally we push the changes to the repo and that is all we need.
