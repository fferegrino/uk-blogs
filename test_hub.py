import fnmatch
import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from huggingface_hub import HfApi

import hub

POSTS = {
    "2026/08/31/august.json": b'{"url": "https://a.blog.gov.uk/2026/08/31/august/"}',
    "2026/09/01/september.json": b'{"url": "https://a.blog.gov.uk/2026/09/01/september/"}',
    "2026/10/09/october.json": b'{"url": "https://a.blog.gov.uk/2026/10/09/october/"}',
}


class FakeHfApi:
    def __init__(self, files):
        self.files = dict(files)
        self.commits = []

    def dataset_info(self, repo_id):
        return SimpleNamespace(sha="rev1")

    def snapshot_download(self, repo_id, repo_type, revision, local_dir, allow_patterns):
        for name, content in self.files.items():
            if any(fnmatch.fnmatch(name, pattern) for pattern in allow_patterns):
                target = Path(local_dir) / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
        (Path(local_dir) / ".cache").mkdir(parents=True, exist_ok=True)

    def create_commit(self, repo_id, repo_type, operations, commit_message, parent_commit):
        self.commits.append((commit_message, parent_commit, sorted(op.path_in_repo for op in operations)))


class HubTest(unittest.TestCase):
    def setUp(self):
        self.previous = os.getcwd()
        os.chdir(tempfile.mkdtemp())
        Path("dataset-card.md").write_text("# card")
        self.api = FakeHfApi(POSTS)
        self.today = date(2026, 10, 10)

    def tearDown(self):
        os.chdir(self.previous)

    def test_recent_months_cross_the_year(self):
        self.assertEqual(hub.recent_months(date(2026, 1, 5)), ["2026/01", "2025/12"])

    def test_fetch_only_downloads_recent_months(self):
        hub.fetch(self.api, self.today)
        self.assertEqual(sorted(hub.digests(hub.DATA)), ["2026/09/01/september.json", "2026/10/09/october.json"])
        self.assertFalse((hub.DATA / ".cache").exists())

    def test_fetch_refuses_without_recent_posts(self):
        self.api.files = {"2026/08/31/august.json": POSTS["2026/08/31/august.json"]}
        with self.assertRaisesRegex(SystemExit, "refusing to scrape without a cursor"):
            hub.fetch(self.api, self.today)

    def test_fetch_refuses_non_empty_directory(self):
        hub.DATA.mkdir()
        (hub.DATA / "stray.json").write_text("{}")
        with self.assertRaisesRegex(SystemExit, "not empty"):
            hub.fetch(self.api, self.today)

    def test_upload_commits_only_new_and_changed_posts(self):
        hub.fetch(self.api, self.today)
        (hub.DATA / "2026/10/09/october.json").write_bytes(b'{"url": "https://renamed.blog.gov.uk/x/"}')
        new_post = hub.DATA / "2026/10/10/new.json"
        new_post.parent.mkdir(parents=True)
        new_post.write_bytes(b"{}")
        # A post older than the fetched months, scraped again because its blog was renamed.
        old_post = hub.DATA / "2026/08/31/august.json"
        old_post.parent.mkdir(parents=True)
        old_post.write_bytes(b"{}")
        hub.upload(self.api, self.today)
        self.assertEqual(self.api.commits, [("2026-10-10 update", "rev1", [
            "2026/08/31/august.json", "2026/10/09/october.json", "2026/10/10/new.json", "README.md"])])

    def test_upload_without_changes_does_not_commit(self):
        hub.fetch(self.api, self.today)
        self.assertEqual(hub.upload(self.api, self.today), [])
        self.assertEqual(self.api.commits, [])

    def test_upload_needs_fetch(self):
        with self.assertRaisesRegex(SystemExit, "run fetch first"):
            hub.upload(self.api, self.today)

    def test_state_stays_outside_data(self):
        hub.fetch(self.api, self.today)
        self.assertEqual(json.loads(hub.STATE.read_text())["revision"], "rev1")
        self.assertNotIn(hub.STATE.name, hub.digests(hub.DATA))

    def test_calls_match_the_real_client(self):
        api = mock.create_autospec(HfApi, instance=True)
        api.dataset_info.return_value = SimpleNamespace(sha="rev1")
        api.snapshot_download.side_effect = lambda **kwargs: self.api.snapshot_download(
            kwargs["repo_id"], kwargs["repo_type"], kwargs["revision"], kwargs["local_dir"], kwargs["allow_patterns"])
        hub.fetch(api, self.today)
        (hub.DATA / "2026/10/09/october.json").write_bytes(b"{}")
        hub.upload(api, self.today)
        api.create_commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
