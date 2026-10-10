"""Keep the Hugging Face copy of the dataset up to date without downloading all of it.

`fetch` downloads only the posts of the current and previous month: the crawl stops at the first index page with
nothing new, so recent posts are all scrape.py needs to know where to stop. `upload` commits the posts that are new or
changed since. Neither touches older posts, so a run can add and update posts but never delete one.
"""
import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import CommitOperationAdd, HfApi

DATASET = "feregrino/uk-government-blogs"
DATA = Path("data")
CARD = Path("dataset-card.md")
# What fetch saw, kept outside data/ so it never ends up in the dataset.
STATE = Path(".fetched.json")
MONTHS = 2


def recent_months(today, count=MONTHS):
    """The YYYY/MM directories of the last `count` months, newest first"""
    year, month = today.year, today.month
    months = []
    for _ in range(count):
        months.append(f"{year:04d}/{month:02d}")
        year, month = (year, month - 1) if month > 1 else (year - 1, 12)
    return months


def digests(directory):
    return {
        path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*.json"))
    }


def fetch(api, today):
    if DATA.exists() and any(DATA.iterdir()):
        raise SystemExit(f"{DATA} is not empty; refusing to mix it with the {DATASET} posts")
    # Pinning the revision lets upload refuse to commit on top of a change made after this fetch.
    revision = api.dataset_info(DATASET).sha
    months = recent_months(today)
    api.snapshot_download(repo_id=DATASET, repo_type="dataset", revision=revision, local_dir=DATA,
                          allow_patterns=[f"{month}/*" for month in months])
    shutil.rmtree(DATA / ".cache", ignore_errors=True)
    fetched = digests(DATA)
    # With no recent posts to compare against, the crawl would walk the whole index and download every post again.
    if not fetched:
        raise SystemExit(f"{DATASET} has no posts in {', '.join(months)}; refusing to scrape without a cursor")
    STATE.write_text(json.dumps({"revision": revision, "posts": fetched}))
    print(f"Fetched {len(fetched)} posts from {', '.join(months)} of {DATASET} at {revision}")


def upload(api, today):
    if not STATE.exists():
        raise SystemExit(f"No {STATE}; run fetch first")
    state = json.loads(STATE.read_text())
    changed = sorted(name for name, digest in digests(DATA).items() if state["posts"].get(name) != digest)
    if not changed:
        print("No new posts")
        return []
    print("New or changed:\n  " + "\n  ".join(changed))
    operations = [CommitOperationAdd(path_in_repo=name, path_or_fileobj=str(DATA / name)) for name in changed]
    operations.append(CommitOperationAdd(path_in_repo="README.md", path_or_fileobj=str(CARD)))
    api.create_commit(repo_id=DATASET, repo_type="dataset", operations=operations,
                      commit_message=f"{today} update", parent_commit=state["revision"])
    print(f"Uploaded {len(changed)} posts to {DATASET}")
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("fetch", "upload"))
    args = parser.parse_args()
    # HfApi reads HF_TOKEN from the environment; fetch works anonymously since the dataset is public.
    command = fetch if args.command == "fetch" else upload
    command(HfApi(), datetime.now(timezone.utc).date())


if __name__ == "__main__":
    main()
