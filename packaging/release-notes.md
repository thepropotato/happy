A voice for your computer: say what you want, and Happy does it, out loud and on screen.

**Mac** (macOS 13 or later): download `Happy.dmg`, drag Happy into Applications, and open it.

- Happy isn't signed by Apple yet, so the first time macOS says it can't check the app. Open **System Settings → Privacy & Security**, scroll down, and click **Open Anyway**.

**Windows** (10 or 11): download `Happy-Setup.exe` and run it. It installs for you only, so it needs no admin rights.

- Windows may show "Windows protected your PC" the first time, because the installer isn't signed yet. Click **More info**, then **Run anyway**.

On either computer, the first launch shows a window with what it's installing: Python packages, speech models and the voice (about 3 GB, a few minutes, needs the internet). Happy opens by himself when it's done, ready to listen and talk. After that he starts straight away.

Happy keeps himself up to date: a new version downloads in the background and installs when he has been quiet for a few minutes. You can turn this off in Settings, under Updates.

To check a download, compare `shasum -a 256 Happy.dmg` on a Mac, or `Get-FileHash Happy-Setup.exe` on Windows, with the line for it in `SHA256SUMS.txt`. Only download Happy from this page or its website.

Free and open source under the MIT license. Privacy policy and terms: see the website, or `website/privacy.html` and `website/terms.html` in the repo.
