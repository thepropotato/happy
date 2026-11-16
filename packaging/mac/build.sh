#!/bin/sh
# Builds dist/Happy-<version>.dmg: a small Happy.app carrying Happy's committed code, which sets itself up on first open.
set -eu

cd "$(dirname "$0")/../.."
version=$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -1)
out="dist"
stage="$out/mac"
app="$stage/Happy.app"

rm -rf "$stage" "$out/Happy-$version.dmg"
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources/app"

# ONLY WHAT IS COMMITTED GOES IN, SO NOTHING LOCAL OR SECRET RIDES ALONG.
git archive HEAD happy whatsapp_server pyproject.toml uv.lock setup.sh README.md LICENSE | tar -x -C "$app/Contents/Resources/app"
printf '%s\n' "$version" > "$app/Contents/Resources/app/.app-version"

cp packaging/mac/launch.sh "$app/Contents/MacOS/Happy"
chmod +x "$app/Contents/MacOS/Happy"
cp packaging/mac/Happy.icns "$app/Contents/Resources/Happy.icns"

cat > "$app/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Happy</string>
  <key>CFBundleDisplayName</key><string>Happy</string>
  <key>CFBundleIdentifier</key><string>com.thepropotato.happy</string>
  <key>CFBundleExecutable</key><string>Happy</string>
  <key>CFBundleIconFile</key><string>Happy</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>$version</string>
  <key>CFBundleVersion</key><string>$version</string>
  <key>LSMinimumSystemVersion</key><string>13.0</string>
  <key>LSUIElement</key><true/>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSMicrophoneUsageDescription</key><string>Happy listens when you talk to it, and turns your speech into text on this Mac.</string>
  <key>NSAppleEventsUsageDescription</key><string>Happy controls the apps you ask it to, like pausing music or switching a tab.</string>
</dict>
</plist>
PLIST

# AN AD-HOC SIGNATURE GIVES THE APP A STABLE IDENTITY, SO MACOS ASKS FOR THE MICROPHONE AS "HAPPY".
codesign --force --deep --sign - "$app"

ln -s /Applications "$stage/Applications"
hdiutil create -quiet -volname "Happy" -srcfolder "$stage" -format UDZO -ov "$out/Happy-$version.dmg"
rm -rf "$stage"
echo "$out/Happy-$version.dmg"
