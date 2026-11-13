import unittest

from select_light_release import CHECKSUM, DAT, REPOSITORY, select_release, version


def release(tag, draft=False, prerelease=False):
    return {
        "tag_name": tag, "draft": draft, "prerelease": prerelease,
        "assets": [
            {"name": name, "state": "uploaded", "digest": "sha256:" + "a" * 64,
             "browser_download_url": f"https://github.com/{REPOSITORY}/releases/download/{tag}/{name}"}
            for name in (DAT, CHECKSUM)
        ],
    }


class SelectReleaseTest(unittest.TestCase):
    def test_uses_highest_numbered_stable_version_not_list_order(self):
        releases = [release("latest-optimized"), release("v11.3"), release("v11.10"),
                    release("v12", prerelease=True), release("v13", draft=True)]
        self.assertEqual(select_release(releases)["tag"], "v11.10")

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
