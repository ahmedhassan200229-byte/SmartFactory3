[app]
title = Smart Factory
package.name = smartfactory
package.domain = org.smartfactory
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt
version = 1.0
requirements = python3,kivy==2.2.1,pyserial,requests,urllib3,certifi,charset-normalizer,idna
orientation = portrait
fullscreen = 0
presplash.filename =
icon.filename =
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE
android.api = 33
android.minapi = 21
android.ndk_api = 21
android.archs = arm64-v8a
android.accept_sdk_license = True
android.logcat_filters = *:S python:D

[buildozer]
log_level = 2
warn_on_root = 1
