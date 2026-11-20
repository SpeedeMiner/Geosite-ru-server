import unittest

from select_light_release import (
    CHECKSUM, DAT, REPOSITORY, ROLLING, SERVER, numbered_plan,
    select_release, select_rolling_release, version,
)


def release(tag, draft=False, prerelease=False, repo=REPOSITORY):
    return {
        "tag_name": tag, "draft": draft, "prerelease": prerelease,
        "assets": [
            {"name": name, "state": "uploaded", "digest": "sha256:" + "a" * 64,
             "browser_download_url": f"https://github.com/{repo}/releases/download/{tag}/{name}"}
            for name in (DAT, CHECKSUM)
        ],
    }


class SelectReleaseTest(unittest.TestCase):
    def test_uses_highest_numbered_stable_version_not_list_order(self):
        releases = [release("latest-optimized"), release("v11.3"), release("v11.10"),
                    release("v12", prerelease=True), release("v13", draft=True)]
        self.assertEqual(select_release(releases)["tag"], "v11.10")

    def test_rolling_uses_its_tag_and_digests_even_without_new_version(self):
        rolling = release(ROLLING)
        rolling["assets"][0]["digest"] = "sha256:" + "b" * 64
        numbered = release("v11.21")
        server = release("v11.21", repo=SERVER)
        self.assertEqual(select_rolling_release(rolling)["assets"][DAT]["sha256"], "b" * 64)
        self.assertEqual(select_release([numbered, rolling])["tag"], "v11.21")
        self.assertTrue(numbered_plan([numbered, rolling], [server])["skip"])

    def test_rolling_rejects_wrong_tag_draft_prerelease_or_corrupt_assets(self):
        with self.assertRaisesRegex(ValueError, "expected published"):
            select_rolling_release(release("v11.21"))
        for kwargs in ({"draft": True}, {"prerelease": True}):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, "expected published"):
                select_rolling_release(release(ROLLING, **kwargs))
        bad = release(ROLLING)
        bad["assets"][0]["digest"] = "sha256:bad"
        with self.assertRaisesRegex(ValueError, "metadata"):
            select_rolling_release(bad)

    def test_new_numbered_plan_uses_only_numbered_server_baseline(self):
        plan = numbered_plan([release("v11.22"), release(ROLLING)],
                             [release("v11.21", repo=SERVER), release(ROLLING, repo=SERVER)])
        self.assertFalse(plan["skip"])
        self.assertEqual(plan["source"]["tag"], "v11.22")
        self.assertEqual(plan["previous"]["tag"], "v11.21")
        self.assertTrue(numbered_plan([release("v11.20")], [release("v11.21", repo=SERVER)])["skip"])

    def test_supports_major_minor_and_patch(self):
        self.assertEqual(version("v11"), (11, 0, 0))
        self.assertEqual(version("v11.3.1"), (11, 3, 1))
        self.assertIsNone(version("v11.3-rc1"))

    def test_fails_closed_if_newest_version_is_incomplete(self):
        newest = release("v11.10")
        newest["assets"].pop()
        with self.assertRaisesRegex(ValueError, "uploaded"):
            select_release([newest, release("v11.3")])

    def test_rejects_invalid_asset_metadata(self):
        for field, value in (("digest", None), ("digest", "sha512:" + "a" * 64),
                             ("browser_download_url", "https://example.com/asset")):
            latest = release("v11.3")
            latest["assets"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                select_release([latest])

    def test_rejects_ambiguous_release(self):
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            select_release([release("v11.0"), release("v11")])


if __name__ == "__main__":
    unittest.main()
