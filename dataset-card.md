---
license: other
license_name: ogl-uk-3.0
license_link: https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
pretty_name: UK Government Blogs
language:
- en
tags:
- government
- politics
- united-kingdom
- text
size_categories:
- 10K<n<100K
# One pretty-printed JSON object per file, which the viewer cannot load as rows.
viewer: false
---

# UK Government Blogs

Every post listed on the [UK Government Blogs](https://www.blog.gov.uk) index, which aggregates the blogs of UK government departments and agencies. Scraped daily since August 2022, with posts going back to 2015.

There is one JSON file per post, `YYYY/MM/DD/slug.json`, dated by publication and named after the last part of the post's URL:

| Field | Contents |
| --- | --- |
| `url` | The post's URL |
| `title`, `authors`, `categories` | As shown in the post's header |
| `pub_date` | Publication time, ISO 8601 with offset |
| `content` | The paragraphs and headings of the post in order, each `{"text": ...}` or `{"heading": level, "text": ...}`. Lists, tables and images are not kept |

When a blog is renamed its posts move to a new URL; the file keeps its path and its `url` is updated.

Also available on [Kaggle](https://www.kaggle.com/datasets/ioexception/uk-government-blogs). The code that builds it lives at [fferegrino/uk-blogs](https://github.com/fferegrino/uk-blogs).

The posts are Crown copyright, published under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) except where otherwise stated.
