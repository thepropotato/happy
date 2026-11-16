#!/bin/sh
# Publishes happy-v<version> to github.com/thepropotato/releases: the Mac DMG built here, the Windows installer from the
# newest successful "Windows installer" run when there is one, then points the website and README at them.
set -eu

cd "$(dirname "$0")/.."
version=$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -1)
tag="happy-v$version"
base="https://github.com/thepropotato/releases/releases"

packaging/mac/build.sh
files="dist/Happy-$version.dmg"

run=$(gh run list -R thepropotato/happy -w windows.yml -s success -L 1 --json databaseId --jq '.[0].databaseId' || true)
if [ -n "$run" ]; then
  rm -f dist/Happy-Setup-*.exe
  gh run download "$run" -R thepropotato/happy -n happy-windows -D dist
  [ -f "dist/Happy-Setup-$version.exe" ] && files="$files dist/Happy-Setup-$version.exe"
fi

if gh release view "$tag" -R thepropotato/releases >/dev/null 2>&1; then
  # shellcheck disable=SC2086
  gh release upload "$tag" $files -R thepropotato/releases --clobber
else
  # shellcheck disable=SC2086
  gh release create "$tag" $files -R thepropotato/releases --title "Happy $version" --notes "Happy $version. Mac: macOS 13 or later. Windows: 10 or 11."
fi

# THE MAC BUTTONS DOWNLOAD THE DMG; THE WINDOWS ONES DOWNLOAD THE INSTALLER ONCE IT EXISTS, AND OPEN THE RELEASE UNTIL THEN.
windows="$base/tag/$tag"
case "$files" in *.exe) windows="$base/download/$tag/Happy-Setup-$version.exe" ;; esac
sed -i '' -E \
  -e "s#data-os=\"mac\" href=\"[^\"]*\"#data-os=\"mac\" href=\"$base/download/$tag/Happy-$version.dmg\"#g" \
  -e "s#data-os=\"windows\" href=\"[^\"]*\"#data-os=\"windows\" href=\"$windows\"#g" \
  website/index.html
sed -i '' -E -e "s#releases/download/happy-v[^/]+/Happy-[0-9.]+\.dmg#releases/download/$tag/Happy-$version.dmg#g" \
  -e "s#Happy-[0-9.]+\.dmg\]#Happy-$version.dmg]#g" -e "s#releases/tag/happy-v[0-9.]+#releases/tag/$tag#g" README.md

echo "Released $tag with: $files"
echo "website/index.html and README.md now point at it; commit and push them."
