UK Blogs Web Scraper
====================

## Set up your environment

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
