[app]

# (str) Title of your application
title = Mines Casino

# (str) Package name
package.name = mines

# (str) Package domain (needed for Android)
package.domain = com.minescasino

# (str) Source code where main.py lives
source.dir = .

# (str) Main entry point
source.main = mines.py

# (str) Application version
version = 1.0

# (str) Supported orientation
orientation = landscape

# (list) Source files to include
source.include_exts = py,json,png,jpg,jpeg,gif,ttf,ogg,wav

# (list) Python requirements
requirements = python3,pygame,kivy

# (str) Android API level
android.api = 35

# (str) Android minimum API level
android.minapi = 23

# (str) Android NDK version
android.ndk = 27c

# (str) Android architecture
android.arch = arm64-v8a

# (bool) Fullscreen
fullscreen = 1

# (bool) Don't show Android app title bar
android.presplash_color = #0f1223

# (str) Presplash image
# presplash.filename = %(source.dir)s/presplash.png

# (str) Icon
# icon.filename = %(source.dir)s/icon.png

# (list) Android permissions
android.permissions =

# (bool) Copy Python source into APK
android.add_src = 1

# (str) Python-for-Android bootstrap
p4a.bootstrap = sdl2

# (str) Android entry activity
android.entrypoint = org.kivy.android.PythonActivity

# (bool) Enable logcat
log_level = 2

[buildozer]

# (str) Build directory
build_dir = .buildozer

# (str) Output directory
bin_dir = bin

# (str) Warn if buildozer is old
warn_on_root = 1

# (str) Build verbosity
log_level = 2
