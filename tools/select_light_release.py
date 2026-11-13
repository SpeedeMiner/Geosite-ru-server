"""Select the highest published, numbered Light release from GitHub's API."""

import argparse
import json
import re
from pathlib import Path

REPOSITORY = "SpeedeMiner/Geosite-ru-light"
DAT = "geosite_RU.dat"
CHECKSUM = DAT + ".sha256sum"
TAG = re.compile(r"v(0|[1-9][0-9]*)(?:\.(0|[1-9][0-9]*))?(?:\.(0|[1-9][0-9]*))?")
SHA256 = re.compile(r"[0-9a-f]{64}")


def version(tag):
    match = TAG.fullmatch(tag)
    return tuple(int(value or 0) for value in match.groups()) if match else None


def select_release(releases):
    candidates = [(version(release["tag_name"]), release) for release in releases
                  if not release["draft"] and not release["prerelease"]]
    numbered = [(key, release) for key, release in candidates if key is not None]
    if not numbered:
        raise ValueError("no published numbered Light releases")
    latest = max(key for key, _ in numbered)
    matches = [release for key, release in numbered if key == latest]
    if len(matches) != 1:
        raise ValueError("ambiguous latest Light version")
    release = matches[0]
    tag = release["tag_name"]
    assets = {}
    for name in (DAT, CHECKSUM):
        found = [item for item in release["assets"] if item["name"] == name]
        if len(found) != 1 or found[0]["state"] != "uploaded":
            raise ValueError(f"Light {tag} does not have one uploaded {name} asset")
        asset = found[0]
        digest = (asset.get("digest") or "").removeprefix("sha256:")
        url = f"https://github.com/{REPOSITORY}/releases/download/{tag}/{name}"
        if (not SHA256.fullmatch(digest) or asset["digest"] != f"sha256:{digest}"
                or asset["browser_download_url"] != url):
            raise ValueError(f"invalid Light {tag} asset metadata for {name}")
        assets[name] = {"url": url, "sha256": digest}
    return {"repository": REPOSITORY, "tag": tag, "assets": assets}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_list", type=Path)
    args = parser.parse_args()
    print(json.dumps(select_release(json.loads(args.release_list.read_text())), indent=2))


if __name__ == "__main__":
    main()
