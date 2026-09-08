# References

## Roku LT SDK

Roku's public LT SDK contains a dedicated box + remote WPS PBC pairing unit test:

- Repository: `rokudev/lt-sdk`
- File: `lt/lt/source/unittest/lt/device/wifi/UnitTestLTDeviceWiFiWpsPbc.c`

Relevant documented behavior includes:

- default host SSID prefix `DIRECT-roku-`,
- Roku WPS OUI `C8:3A:6B`,
- WPS M1 vendor payload containing message type `0x01` plus a 32-bit chip ID,
- association-request vendor IE `DD 05 C8 3A 6B 00 00`,
- WPS as a credential-provisioning phase followed by a separate WPA2 reconnect.

Source:

https://github.com/rokudev/lt-sdk/blob/main/lt/lt/source/unittest/lt/device/wifi/UnitTestLTDeviceWiFiWpsPbc.c

## Roam reverse-engineering notes

The open-source Roam project contains research notes about Roku Voice Remote Pro pairing and independently records use of:

```text
wpa_cli ... vendor_elem_add 13 dd05c83a6b0000
```

It also documents the need to reason separately about WPS provisioning and the resulting WPA credential.

Sources:

https://github.com/msdrigg/roam/tree/main/docs/notes/voice-search/VoiceRemotePro

https://github.com/msdrigg/roam/blob/main/docs/notes/voice-search/VoiceRemotePro/wps.sh

## Local experimental evidence represented in this repository

The remaining findings were established directly during testing on a Roku Streaming Stick+ 3810X / 3810CA running Roku OS 14.1.4.7709, including:

- automatic post-WPS reconnect failure vs. manual fresh-credential reconnect success,
- successful DHCP on the private remote network,
- 8060 connection resets on the private remote interface,
- port 8080 `press` command behavior,
- input-source selection exposing `IR_RF (T3, Alice, Elk)`,
- successful onboarding navigation after issuing `.r`, `.0`, and then the keypress separately.

These device-specific findings should be treated as validated observations for the tested firmware, not as a guarantee for every Roku model or future Roku OS release.
