[app]
title = Magisk Manager
package.name = magiskmanager
package.domain = it.lollo
source.dir = .
source.include_exts = py,png
source.exclude_dirs = .github,icone,bin,.buildozer
version = 1.4
requirements = python3,kivy==2.3.0,openssl,certifi
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/icon.png
android.permissions = INTERNET
android.api = 33
android.ndk = 25b
p4a.branch = v2024.01.21
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = False

[buildozer]
log_level = 2
warn_on_root = 1
