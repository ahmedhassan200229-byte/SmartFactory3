[app]
title = Smart Factory
package.name = smartfactory
package.domain = org.smartfactory
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt
version = 1.0
requirements = python3,kivy==2.3.0,requests,urllib3,certifi,charset-normalizer,idna
orientation = portrait
fullscreen = 0
presplash.filename =
icon.filename =
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,USB_PERMISSION
android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.arch = arm64-v8a
android.accept_sdk_license = True
android.logcat_filters = *:S python:D
android.add_aars =
android.gradle_dependencies =

[buildozer]
log_level = 2
warn_on_root = 1
