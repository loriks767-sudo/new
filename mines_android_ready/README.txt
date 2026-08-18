MINES ANDROID BUILD
===================

Files:
- mines.py          Android-ready version of the uploaded Mines game
- buildozer.spec    Buildozer configuration

IMPORTANT:
Build the APK in Linux/WSL, not directly with normal Windows PyInstaller.

Commands:
1. Install Buildozer and Android dependencies.
2. Open this folder.
3. Run:
   buildozer android debug

The APK will be created in:
   bin/

For a release build:
   buildozer android release

The game remains landscape/fullscreen.
Touch input is supported through FINGERDOWN in addition to mouse input.
balances.json is stored in the app's writable Android storage.
