#!/usr/bin/env bash
# Each channel uses a verified Light source and its own Server baseline.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
mode="${1:?build or publish required}"
channel="${2:?rolling or numbered required}"
[[ "$channel" == rolling || "$channel" == numbered ]]
light=SpeedeMiner/Geosite-ru-light
server=SpeedeMiner/Geosite-ru-server
[[ "$GITHUB_REPOSITORY" == "$server" ]]
rolling=latest-optimized
dat=geosite_RU.dat
files=("$dat" "$dat.sha256sum" geosite_RU_categories.txt)
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

tag_commit() {
  local ref="refs/tags/$2" refs
  refs="$(git ls-remote --exit-code --tags "https://github.com/$1.git" "$ref" "$ref^{}")"
  awk -v ref="$ref" '$2==ref { tag=$1 } $2==ref "^{}" { commit=$1 } END { print (commit ? commit : tag) }' <<< "$refs"
}

select_rolling() {
  gh api "repos/$1/releases/tags/$rolling" > "$work/api-$2.json"
  python3 tools/select_light_release.py "$work/api-$2.json" --channel rolling --repository "$1"
}

plan_numbered() {
  gh api --paginate "repos/$light/releases?per_page=100" | jq -s add > "$work/light.json"
  gh api --paginate "repos/$server/releases?per_page=100" | jq -s add > "$work/server.json"
  python3 tools/select_light_release.py "$work/light.json" --plan-against "$work/server.json"
}

dat_sha() { jq -er '.assets["geosite_RU.dat"].sha256' "$1"; }
file_sha() { sha256sum "$1" | cut -d' ' -f1; }

fetch_pair() {
  local spec="$1" dest="$2" name url sha
  mkdir -p "$dest"
  for name in "$dat" "$dat.sha256sum"; do
    url="$(jq -er --arg n "$name" '.assets[$n].url' "$spec")"
    sha="$(jq -er --arg n "$name" '.assets[$n].sha256' "$spec")"
    curl -fsSL --retry 3 --connect-timeout 15 --max-time 90 "$url" -o "$dest/$name"
    printf '%s  %s\n' "$sha" "$dest/$name" | sha256sum --check --strict
  done
  printf '%s  %s\n' "$(dat_sha "$spec")" "$dat" | cmp - "$dest/$dat.sha256sum"
}

verify_bundle() {
  local expected
  expected="$(jq -er '.result_sha' dist/snapshot.json)"
  [[ "$expected" =~ ^[0-9a-f]{64}$ && "$(file_sha "dist/$dat")" == "$expected" ]]
  printf '%s  %s\n' "$expected" "$dat" | cmp - "dist/$dat.sha256sum"
  printf 'RU\n' | cmp - dist/geosite_RU_categories.txt
}

if [[ "$mode" == build ]]; then
  if [[ "$channel" == rolling ]]; then
    select_rolling "$light" light > "$work/source.json"
    select_rolling "$server" server > "$work/previous.json"
  else
    plan_numbered > "$work/plan.json"
    if jq -e '.skip' "$work/plan.json" >/dev/null; then
      jq -r '.reason' "$work/plan.json"
      mkdir dist
      jq --arg channel "$channel" '. + {channel:$channel}' "$work/plan.json" > dist/snapshot.json
      echo "snapshot_sha=$(file_sha dist/snapshot.json)" >> "$GITHUB_OUTPUT"
      exit 0
    fi
    jq '.source' "$work/plan.json" > "$work/source.json"
    jq '.previous' "$work/plan.json" > "$work/previous.json"
  fi
  tag="$(jq -er '.tag' "$work/source.json")"
  commit="$(tag_commit "$light" "$tag")"
  [[ "$commit" =~ ^[0-9a-f]{40}$ ]]
  fetch_pair "$work/source.json" "$work/input"
  fetch_pair "$work/previous.json" "$work/previous"
  [[ "$commit" == "$(tag_commit "$light" "$tag")" ]]
  python3 tools/project_geosite.py "$work/input/$dat" dist --source-sha256 "$(dat_sha "$work/source.json")" \
    --previous-server "$work/previous/$dat"
  result_sha="$(file_sha "dist/$dat")"
  if [[ "$channel" == rolling ]]; then
    raw_commit="$(git ls-remote --exit-code "https://github.com/$server.git" refs/heads/release | awk '{print $1}')"
    [[ "$raw_commit" =~ ^[0-9a-f]{40}$ ]]
    curl -fsSL --retry 3 --connect-timeout 15 --max-time 90 \
      "https://raw.githubusercontent.com/$server/$raw_commit/$dat" -o "$work/raw.dat"
    raw_sha="$(file_sha "$work/raw.dat")"
    # The candidate may already be in raw if a previous publish was interrupted.
    [[ "$raw_sha" == "$(dat_sha "$work/previous.json")" || "$raw_sha" == "$result_sha" ]]
  fi
  jq -n --arg channel "$channel" --arg commit "$commit" --arg result_sha "$result_sha" \
    --slurpfile source "$work/source.json" --slurpfile previous "$work/previous.json" \
    '{channel:$channel,skip:false,commit:$commit,result_sha:$result_sha,source:$source[0],previous:$previous[0]}' \
    > dist/snapshot.json
  verify_bundle
  echo "snapshot_sha=$(file_sha dist/snapshot.json)" >> "$GITHUB_OUTPUT"
  exit 0
fi

[[ "$mode" == publish && "$GITHUB_REF" == refs/heads/main && "$GITHUB_EVENT_NAME" != pull_request ]]
[[ "$SNAPSHOT_SHA" =~ ^[0-9a-f]{64}$ && "$(file_sha dist/snapshot.json)" == "$SNAPSHOT_SHA" ]]
[[ "$(jq -er '.channel' dist/snapshot.json)" == "$channel" ]]
if jq -e '.skip' dist/snapshot.json >/dev/null; then
  [[ "$channel" == numbered ]]
  jq -r '.reason' dist/snapshot.json
  exit 0
fi
verify_bundle
[[ "$(gh api "repos/$server/git/ref/heads/main" --jq '.object.sha')" == "$GITHUB_SHA" ]]
tag="$(jq -er '.source.tag' dist/snapshot.json)"
commit="$(jq -er '.commit' dist/snapshot.json)"
source_sha="$(jq -er '.source.assets["geosite_RU.dat"].sha256' dist/snapshot.json)"
previous_sha="$(jq -er '.previous.assets["geosite_RU.dat"].sha256' dist/snapshot.json)"
result_sha="$(jq -er '.result_sha' dist/snapshot.json)"
notes="Based on GeoSite RU Light $tag ($commit, input SHA-256 $source_sha). The DAT contains exactly one category, RU. Source: https://github.com/$light/releases/tag/$tag"

if [[ "$channel" == numbered ]]; then
  # Recheck both snapshots before writing. Never modify an existing release.
  plan_numbered > "$work/plan.json"
  if jq -e '.skip' "$work/plan.json" >/dev/null; then
    jq -r '.reason' "$work/plan.json"
    exit 0
  fi
  jq -S '{source,previous}' "$work/plan.json" > "$work/live.json"
  jq -S '{source,previous}' dist/snapshot.json | cmp - "$work/live.json"
  [[ "$commit" == "$(tag_commit "$light" "$tag")" ]]
  (
    cd dist
    gh release create "$tag" "${files[@]}" --repo "$server" --target "$GITHUB_SHA" \
      --title "GeoSite RU Server $tag (RU only)" --notes "$notes" --latest=false
  )
  exit 0
fi

[[ "$tag" == "$rolling" ]]
select_rolling "$light" light | jq -S . > "$work/live.json"
jq -S '.source' dist/snapshot.json | cmp - "$work/live.json"
[[ "$commit" == "$(tag_commit "$light" "$tag")" ]]
select_rolling "$server" server > "$work/current.json"
current_sha="$(dat_sha "$work/current.json")"
[[ "$current_sha" == "$previous_sha" || "$current_sha" == "$result_sha" ]]

# Write raw first, so a failed rolling upload can be resumed from verified bytes.
gh auth setup-git --hostname github.com
git clone -q --depth=1 --single-branch --branch release "https://github.com/$server.git" "$work/raw"
raw_sha="$(file_sha "$work/raw/$dat")"
[[ "$raw_sha" == "$previous_sha" || "$raw_sha" == "$result_sha" ]]
cp "dist/$dat" "$work/raw/$dat"
git -C "$work/raw" add -- "$dat"
printf '%s\n' "$dat" | cmp - <(git -C "$work/raw" ls-files)
if ! git -C "$work/raw" diff --cached --quiet; then
  git -C "$work/raw" -c user.name='github-actions[bot]' \
    -c user.email='41898282+github-actions[bot]@users.noreply.github.com' \
    commit -m "Publish GeoSite RU Server from Light $commit"
  git -C "$work/raw" push origin HEAD:release
fi
raw_commit="$(git -C "$work/raw" rev-parse HEAD)"
[[ "$(git -C "$work/raw" ls-remote origin refs/heads/release | cut -f1)" == "$raw_commit" ]]
curl -fsSL --retry 2 --connect-timeout 10 --max-time 25 \
  "https://raw.githubusercontent.com/$server/$raw_commit/$dat" -o "$work/published.dat"
cmp "dist/$dat" "$work/published.dat"

changed=()
for f in "${files[@]}"; do
  want="sha256:$(file_sha "dist/$f")"
  have="$(jq -r --arg n "$f" '.assets[] | select(.name==$n) | .digest' "$work/api-server.json")"
  if [[ "$want" != "$have" ]]; then changed+=("$f"); fi
done
if (( ${#changed[@]} )); then
  (cd dist && gh release upload "$rolling" "${changed[@]}" --clobber --repo "$server")
fi
rolling_meta="$(gh api "repos/$server/releases/tags/$rolling")"
for f in "${files[@]}"; do
  want="sha256:$(file_sha "dist/$f")"
  [[ "$(jq -er --arg n "$f" '.assets[] | select(.name==$n) | .digest' <<< "$rolling_meta")" == "$want" ]]
done
title="GeoSite RU Server (RU only, rolling)"
if [[ "$(jq -r '.name' <<< "$rolling_meta")" != "$title" || "$(jq -r '.body' <<< "$rolling_meta")" != "$notes" ]]; then
  gh release edit "$rolling" --repo "$server" --title "$title" --notes "$notes" --latest
fi
if [[ "$(tag_commit "$server" "$rolling")" != "$GITHUB_SHA" ]]; then
  gh api --method PATCH "repos/$server/git/refs/tags/$rolling" -f sha="$GITHUB_SHA" -F force=true >/dev/null
fi
if [[ "$raw_sha" != "$result_sha" || "$current_sha" != "$result_sha" ]]; then
  curl -fsS --connect-timeout 5 --max-time 15 "https://purge.jsdelivr.net/gh/$server@release/$dat" >/dev/null || true
fi
printf '### GeoSite RU Server rolling sync\n\n- Light commit: `%s`\n- Light DAT SHA-256: `%s`\n- Server DAT SHA-256: `%s`\n- Raw commit: `%s`\n' \
  "$commit" "$source_sha" "$result_sha" "$raw_commit" >> "$GITHUB_STEP_SUMMARY"
