#!/bin/sh
# Publishes v<version> on github.com/thepropotato/happy: the Mac DMG built here and the Windows installer from the newest
# successful "Windows installer" run. The files keep one name, so the website's /releases/latest/download links never change.
set -eu

cd "$(dirname "$0")/.."
version=$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -1)
tag="v$version"
repo="thepropotato/happy"

packaging/mac/build.sh
files="dist/Happy.dmg"

run=$(gh run list -R "$repo" -w windows.yml -s success -L 1 --json databaseId,headSha --jq '.[0].databaseId' || true)
if [ -n "$run" ]; then
  rm -f dist/Happy-Setup*.exe
  gh run download "$run" -R "$repo" -n happy-windows -D dist
  # AN INSTALLER BUILT BEFORE THE NAMES WERE FIXED CARRIES ITS VERSION; IT IS PUBLISHED UNDER THE ONE NAME ALL THE SAME.
  for each in dist/Happy-Setup-*.exe; do [ -f "$each" ] && mv "$each" dist/Happy-Setup.exe; done
  [ -f dist/Happy-Setup.exe ] && files="$files dist/Happy-Setup.exe"
fi

# THE BUILDS ARE NOT SIGNED YET, SO THESE SUMS ARE HOW ANYONE CAN CHECK A DOWNLOAD IS THE ONE PUBLISHED HERE.
# shellcheck disable=SC2086
(cd dist && shasum -a 256 $(for each in $files; do basename "$each"; done) > SHA256SUMS.txt)
files="$files dist/SHA256SUMS.txt"

if gh release view "$tag" -R "$repo" >/dev/null 2>&1; then
  # shellcheck disable=SC2086
  gh release upload "$tag" $files -R "$repo" --clobber
else
  # shellcheck disable=SC2086
  gh release create "$tag" $files -R "$repo" --title "Happy $version" --notes-file packaging/release-notes.md
fi
echo "Released $tag with: $files"
