Scraping the government
=======================

Web scraping is a good way to build a dataset of something you are interested in analysing, but not only that, creating your own dataset allows you to customise it in such a way that better serves your purposes.

Python allows you to scrape websites *for free* and on your own with a few commonly used packages supported by the community, and we can leverage GitHub's *free* automation and storage capabilities to execute web the scraping and persist the results in a public git repository.

In this post I will tell you how to do it.

## Set up your environment

Let's begin by setting up the groundwork for this project, we will need:

### Aa git repository (hosted on GitHub)

Since we are going to use GitHub Actions it is necessary to create a repository there. Then clone it in your local machine where all the magic will happen.

 > 🤔 There are alternatives if you don't want to use GitHub, GitLab offers CI pipelines that are a replacement for GH Actions

### A Python virtual environment

This is not a requirement, but I highly encourage you to create an environment for each one of your Python projects. I usually go for Poetry or Pipenv, but vanilla Python will be enough for us this time:

```shell
python -m venv .venv
```

Since you are doing web scraping, you will need to add some basic dependencies: 
 - `requests` to perform HTTP queries and retrieve their responses, and
 - `beautifulsoup4` to parse and interact with HTML documents

Just add the following lines to a file named `requirements.txt`:

```
beautifulsoup4
requests
```

 > ⚠️ Add a `.gitignore` file, if you have your virtual environment in the same folder as the rest of your code, make sure you ignore its contents.

## Identify your (first) target

This one is the crucial step, and one I strongly recommend you check first. What web page are you going to scrape?

You want a web page that is static, meaning that it does not require JavaScript to display the content you want to get from it. While it is possible to work with single page apps, those with infinite scroll or any other interactivity-rich pages, I will leave that discussion for a future post.

When coosing a website to scrape, it is also important to keep in mind that you also want a one that offers an index-like page, since this will be the indicator that will tell you if there is anything new to scrape.

In my case, I put my crosshairs on the [UK Government Blogs index](https://www.blog.gov.uk) a page that aggregates all content posted across all blogs related to the UK government, from now on I will refer to this page as _"the index"_. 

### URLs

URLs play an important role in web scraping, looking at the URLs that can be used to access the different index pages, it is possible to identify a pattern:

 - https://www.blog.gov.uk/all-posts/page/1
 - https://www.blog.gov.uk/all-posts/page/2
 - https://www.blog.gov.uk/all-posts/page/1000

The only change is that the last part of the address is an integer that indicates which page of the index is being requested. More over, all addreses work and direct to a valid website. We will use this information to our advantage.

### Inspect is your friend

Once you identified some patterns in the website addresses, it is time to find patterns in the website contents. In most modern browsers you can _right_ click anywhere on the page and select the option _Inspect_. This will allow you to interact with the source code of the web page. 

### Identify how the index looks on a page with content

![Article](https://ik.imagekit.io/thatcsharpguy/posts/web-scraping/article.gif?ik-sdk-version=javascript-1.4.3&updatedAt=1660194036264)

Inspecting the first page of the index, you can start to unravel the structure of the page. It has many entries, all of them wrapped in an unordered list (`ul`) with the class `blogs-list`. Then, each entry is contained within a `li` html tag. 

If you check further, inside every `li` there is a nested `a` (did you know that _a_ means anchor?) with the an address pointing to the full post, we need that URL to direct us to the full blog post.

The structure is pretty easy to navigate, this is great news, we will be able to scrape these quickly.

### Identify how the index looks when there is no content

It is also crucial to identify how a page with no content looks like, since a page with no content will be useful to identify when we have reached the end of the index and there is nothing else for us to scrape. 

To view a page without content, change the url to a page that is unlikely to exist, for example the 1 millionth page: www.blog.gov.uk/all-posts/page/1000000 from there, inspect the page as we did previously and you will notice that while the `<ul class="blogs-list">` is still there, now it contains a single `li` element with `"noresults"` as `class` attribute. 

```html
<ul class="blogs-list">
    <li class="noresults">
      <h3 class="govuk-heading-m">No posts found</h3>
      <p class="govuk-body">Please try:</p>
      <ul class="govuk-list govuk-list--bullet">
        <li>searching again using different words</li>
      </ul>
    </li>
</ul>
```

More great news! it will be easy to know when to stop crawling, all we have to do is look for that particular `li` element.

 > ⚠️ Keep in mind that some other websites may give you a 404 error code when trying to access a non-existent index page, a 404 error is pretty good news too, since you can check for that status code and stop scraping

## A slight detour (do not repeat yourself!)

Before moving on, we need to make sure we do not keep scraping the same URLs over and over again, so we need a way to keep track of which ones we have already processed. 

In a larger system we could use a proper database, but for our small-scale project, we will have a single text file (I named ours `scraped_urls.txt`), where each line is a processed url, for example:

```
https://food.blog.gov.uk/2022/08/04/chairs-stakeholder-update-how-the-fsa-is-supporting/
https://space.blog.gov.uk/2022/08/04/how-i-made-it-to-mission-control/
https://ruralpayments.blog.gov.uk/2022/08/04/rpa-is-supporting-farm-24/
https://forestrycommission.blog.gov.uk/2022/08/04/reducing-the-impact-of-deer/
https://companieshouse.blog.gov.uk/2022/08/04/our-new-powers-a-milestone/
```

We need a couple of methods to interact with this file, one to get the urls that already exist in the file:

```python
import os

def get_scraped_urls():
    scraped_urls = []
    if os.path.exists("scraped_urls.txt"):
        with open("scraped_urls.txt") as url_file:
            for line in url_file:
                scraped_urls.append(line.strip())
    return scraped_urls
```

And another one to append urls to the file:

```python
def append_scrapped_urls(urls):
    with open("scraped_urls.txt", "a") as url_file:
        for url in urls:
            url_file.write(url)
            url_file.write("\n")
```

## Scrape your first target

Once we have identified our target and have a method to keep track of which URLs are processed, we can start the actual scraping.

The goal of scraping our first target is to build an index of pages that we need to scrape in detail. Think of it as a 
list of pending jobs.

Let's create a function that takes in a page number and returns the urls of the article that page displays:

```python
def get_urls(page):
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
```

Keep in mind that this function will return the urls as they appear on the webpage, which most lilely will be from the  newest to the oldest, so you may want to reverse the result to process the oldest urls first.

Then we can use this function to crawl across pages from page 1 in a for loop until one of two conditions are met: 
 
 - There are no more articles available, or
 - we get a url that we have already crawled

```python
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
```

By this point, we should have a list (above named `new_urls`) that contains a list of urls that we have not scraped yet. This list is sorted from newest to oldest.

## Identify your second target

The URLs we have gathered so far point to the full articles, which contain the actual information we are after in our tiny scraping project. 

Our next step is to analyse the contents of each article, remember to use the _Inspect tool_ to find the structure of the articles page.

An initial look shows us that the article contains basic details such as title, author, published date, categories, followed by the actual content. 

![](https://ik.imagekit.io/thatcsharpguy/posts/web-scraping/article.png?ik-sdk-version=javascript-1.4.3&updatedAt=1660195990995)

_Inspecting_ the file reveals that every interesting bit we care about exists within an `article` tag, and from there we can navigate to the `header` tag to get the "metadata" for the post, while the content exists in a `div` classed as `entry-content`, sometimes in `p` tags others in `h*` tags. 

```html
<article>
   <header>
      <h1 class="govuk-heading-xl">How we developed the ‘Ready to Pass?’ campaign</h1>
      <div class="govuk-body-s">
         <a href="https://despatch.blog.gov.uk/author/abigail-britten/" title="Posts by Abigail Britten" class="author url fn" rel="author">Abigail Britten</a>, 
         <time class="updated" datetime="2022-08-10T16:07:46+01:00" pubdate="">10 August 2022</time>
         <a href="https://despatch.blog.gov.uk/category/driving-instructors/" rel="category tag">Driving instructors</a>, <a href="https://despatch.blog.gov.uk/category/ready-to-pass/" rel="category tag">Ready to Pass?</a>
      </div>
   </header>
   <div class="entry-content">
      <p>We launched our ‘Ready to Pass?’ campaign a few weeks ago now. ...</p>
      <p>In this blog post, I want to tell you more about: ...</p>
   </div>
</article>
```

Websites that are properly structured are a bliss to work with, this is one of them, still make sure you review a few  different urls to account for every possible variation:

For example, there are articles with [multiple authors](https://nationalscreening.blog.gov.uk/2022/08/01/guidance-on-evaluating-ai-for-use-in-breast-screening/), there are some with [multiple tags](https://civilservice.blog.gov.uk/2022/07/28/top-tips-on-delivering-digital-projects-with-global-partners/). I came across some that had lists and tables in the [article body](https://homeofficemedia.blog.gov.uk/2022/07/28/windrush-compensation-scheme-factsheet-july-2022/). For now, Let's just follow a simplistic approach of dealing with articles, only text will be preserved.

### Division of concerns (when scraping)

We could create a mega-function that takes care of the article on its own, but I always find it better to create small functions that can tackle specific sections of the page's content at the time. 


We can have a couple of functions: one for the header and another for the content:

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
