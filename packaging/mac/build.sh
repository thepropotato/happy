#!/bin/sh
# Builds dist/Happy.dmg: a small Happy.app carrying Happy's committed code, which sets itself up on first open
# in a window that shows what is being installed. Needs the Xcode command line tools for swiftc.
set -eu

cd "$(dirname "$0")/../.."
version=$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -1)
out="dist"
stage="$out/mac"
app="$stage/Happy.app"

rm -rf "$stage" "$out/Happy.dmg"
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources/app"

# ONLY WHAT IS COMMITTED GOES IN, SO NOTHING LOCAL OR SECRET RIDES ALONG.
git archive HEAD happy whatsapp_server pyproject.toml uv.lock setup.sh README.md LICENSE | tar -x -C "$app/Contents/Resources/app"
printf '%s\n' "$version" > "$app/Contents/Resources/app/.app-version"

# ONE BINARY FOR BOTH KINDS OF MAC, SO THE SETUP WINDOW OPENS ON INTEL TOO.
for arch in arm64 x86_64; do
  swiftc -O -target "$arch-apple-macos13.0" -framework AppKit packaging/mac/Happy.swift -o "$stage/Happy-$arch"
done
lipo -create "$stage/Happy-arm64" "$stage/Happy-x86_64" -output "$app/Contents/MacOS/Happy"
rm -f "$stage/Happy-arm64" "$stage/Happy-x86_64"
cp packaging/mac/launch.sh "$app/Contents/Resources/launch.sh"
chmod +x "$app/Contents/Resources/launch.sh"
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
mkdir "$stage/.background"
cp packaging/mac/dmg-background.tiff "$stage/.background/background.tiff"

# THE WINDOW THE DMG OPENS IN IS LAID OUT BY FINDER ON A WRITABLE COPY, THEN THAT COPY IS COMPRESSED READ-ONLY.
rw="$out/Happy-rw.dmg"
rm -f "$rw"
hdiutil create -quiet -volname "Happy" -srcfolder "$stage" -fs HFS+ -format UDRW -ov "$rw"
mount=$(hdiutil attach -readwrite -noverify -noautoopen "$rw" | sed -n 's|^/dev/[^[:space:]]*[[:space:]]*Apple_HFS[[:space:]]*||p' | tail -1)
[ -d "$mount" ] || { echo "The DMG could not be mounted to lay it out." >&2; exit 1; }
/usr/bin/osascript <<APPLESCRIPT
tell application "Finder"
  set dmg to (POSIX file "$mount" as alias)
  open dmg
  set win to container window of dmg
  set current view of win to icon view
  set toolbar visible of win to false
  set statusbar visible of win to false
  set sidebar width of win to 0
  set the bounds of win to {200, 120, 840, 548}
  set opts to the icon view options of win
  set arrangement of opts to not arranged
  set icon size of opts to 128
  set text size of opts to 13
  set background picture of opts to file ".background:background.tiff" of dmg
  set position of item "Happy.app" of dmg to {170, 190}
  set position of item "Applications" of dmg to {470, 190}
  close win
  open dmg
  update dmg without registering applications
  delay 2
  close container window of dmg
end tell
APPLESCRIPT
# THE VOLUME'S OWN ICON SHOWS ON THE DESKTOP AND IN THE SIDEBAR WHILE THE DMG IS OPEN. THE FINDER FLAG THAT SAYS
# "USE IT" IS SET DIRECTLY, SINCE SetFile ONLY COMES WITH XCODE.
# IT GOES IN AFTER FINDER'S LAYOUT, WHICH REMOVES BOTH WHEN IT SAVES THE WINDOW.
cp packaging/mac/Happy.icns "$mount/.VolumeIcon.icns"
xattr -wx com.apple.FinderInfo 0000000000000000040000000000000000000000000000000000000000000000 "$mount"
chmod -Rf go-w "$mount" || true
sync
hdiutil detach -quiet "$mount" || hdiutil detach -force -quiet "$mount"
hdiutil convert -quiet "$rw" -format UDZO -imagekey zlib-level=9 -ov -o "$out/Happy.dmg"
rm -f "$rw"
rm -rf "$stage"
echo "$out/Happy.dmg"
