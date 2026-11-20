"""Select verified assets for the rolling and numbered channels."""

import argparse
import json
import re
from pathlib import Path

REPOSITORY = "SpeedeMiner/Geosite-ru-light"
SERVER = "SpeedeMiner/Geosite-ru-server"
ROLLING = "latest-optimized"
DAT = "geosite_RU.dat"
CHECKSUM = DAT + ".sha256sum"
TAG = re.compile(r"v(0|[1-9][0-9]*)(?:\.(0|[1-9][0-9]*))?(?:\.(0|[1-9][0-9]*))?")
SHA256 = re.compile(r"[0-9a-f]{64}")


def version(tag):
    match = TAG.fullmatch(tag)
    return tuple(int(value or 0) for value in match.groups()) if match else None


def published(release):
    return release["draft"] is False and release["prerelease"] is False


def select_release(releases, repo=REPOSITORY):
    candidates = [(version(release["tag_name"]), release) for release in releases
                  if published(release)]
    numbered = [(key, release) for key, release in candidates if key is not None]
    if not numbered:
        raise ValueError("no published numbered Light releases")
    latest = max(key for key, _ in numbered)
    matches = [release for key, release in numbered if key == latest]
    if len(matches) != 1:
        raise ValueError("ambiguous latest Light version")
    return checked_assets(matches[0], repo)


def checked_assets(release, repo):
    tag = release["tag_name"]
    assets = {}
    for name in (DAT, CHECKSUM):
        found = [item for item in release["assets"] if item["name"] == name]
        if len(found) != 1 or found[0]["state"] != "uploaded":
            raise ValueError(f"{repo} {tag} does not have one uploaded {name} asset")
        asset = found[0]
        digest = (asset.get("digest") or "").removeprefix("sha256:")
        url = f"https://github.com/{repo}/releases/download/{tag}/{name}"
        if (not SHA256.fullmatch(digest) or asset["digest"] != f"sha256:{digest}"
                or asset["browser_download_url"] != url):
            raise ValueError(f"invalid {repo} {tag} asset metadata for {name}")
        assets[name] = {"url": url, "sha256": digest}
    return {"repository": repo, "tag": tag, "assets": assets}


def select_rolling_release(release, repo=REPOSITORY):
    if release["tag_name"] != ROLLING or not published(release):
        raise ValueError(f"expected published {repo} {ROLLING}")
    return checked_assets(release, repo)


def numbered_plan(light_releases, server_releases):
    source = select_release(light_releases)
    previous = select_release(server_releases, SERVER)
    if version(source["tag"]) <= version(previous["tag"]):
        return {"skip": True, "reason": f'No newer numbered release than Server {previous["tag"]}'}
    return {"skip": False, "source": source, "previous": previous}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_list", type=Path)
    parser.add_argument("--channel", choices=("rolling", "numbered"), default="numbered")
    parser.add_argument("--repository", choices=(REPOSITORY, SERVER), default=REPOSITORY)
    parser.add_argument("--plan-against", type=Path)
    args = parser.parse_args()
    try:
        rows = json.loads(args.release_list.read_text())
        if args.plan_against:
            if args.channel != "numbered" or args.repository != REPOSITORY:
                parser.error("a numbered plan requires Light numbered input")
            result = numbered_plan(rows, json.loads(args.plan_against.read_text()))
        elif args.channel == "rolling":
            result = select_rolling_release(rows, args.repository)
        else:
            result = select_release(rows, args.repository)
    except (ValueError, TypeError, KeyError) as error:
        parser.exit(1, f"Release selection failed: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
