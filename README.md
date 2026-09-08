# Roku Virtual Control

A documented, reproducible workflow for regaining control of a factory-reset Roku Streaming Stick when no physical Roku remote is available.

This repository captures the full path that worked on a **Roku Streaming Stick+ 3810X / 3810CA running Roku OS 14.1.4.7709**, using a **Raspberry Pi 4** as a software-emulated Roku remote.

## What was discovered

The key finding is that a factory-reset Roku can be controlled without a physical remote by reproducing the behavior of a Roku Wi-Fi remote:

1. Pair to the Roku's private `DIRECT-roku-*` Wi-Fi network using WPS PBC.
2. Include Roku-specific WPS vendor data so the Roku treats the station as a remote instead of a generic WPA2 client.
3. Capture the WPS credential externally instead of letting `wpa_supplicant` auto-apply it.
4. Reconnect manually with the harvested WPA2 credential and the Roku association vendor IE.
5. Obtain an IP address from the Roku's private DHCP server.
6. Connect to TCP port **8080**.
7. Configure the debug input source as **IR_RF / Alice** and the remote ID separately.
8. Send keypresses such as `press .h120 d`.

The working input sequence was:

```text
press .r
press .0
press .h120 d
```

Where:

- `.r` selects `IR_RF`, which Roku identifies as the source type used by T3 / Alice / Elk remotes.
- `.0` selects remote ID 0.
- `.h120 d` sends a 120 ms Down press.

Sending these modifiers together in a single command did **not** work reliably. Sending them as separate state-setting commands did.

## Repository map

- [`docs/full-guide.md`](docs/full-guide.md) - complete start-to-finish procedure.
- [`docs/architecture.md`](docs/architecture.md) - how the Roku remote path works.
- [`docs/discoveries.md`](docs/discoveries.md) - what worked, what failed, and why.
- [`docs/troubleshooting.md`](docs/troubleshooting.md) - recovery and diagnostics.
- [`hardware/BOM.md`](hardware/BOM.md) - required and optional hardware.
- [`scripts/roku-8080-controller.py`](scripts/roku-8080-controller.py) - software remote client for port 8080.
- [`scripts/roku-send`](scripts/roku-send) - simple WASD-style wrapper.
- [`scripts/install-deps.sh`](scripts/install-deps.sh) - Raspberry Pi dependency installer.
- [`config/roku-remote.env.example`](config/roku-remote.env.example) - non-secret configuration template.

## Tested environment

The successful setup used:

- Roku Streaming Stick+ 3810X / 3810CA
- Roku OS 14.1.4.7709
- Raspberry Pi 4
- Raspberry Pi OS Lite 64-bit / Debian Trixie
- Linux kernel 6.18.x
- `wpa_supplicant`
- `wpa_cli`
- `iw`
- `iproute2`
- BusyBox `udhcpc`
- Python 3
- `tcpdump`

The Roku private network observed during the successful session was in the `172.29.243.0/24` range, but **do not hard-code those addresses**. Let DHCP determine them.

## Security warning

Never commit or paste any of the following:

- WPS credentials
- Roku private WPA PSK / PMK
- `/etc/roku-remote-wpa.conf`
- `/run/*cred*`
- packet captures that contain credentials
- home Wi-Fi SSIDs or passwords
- SSH private keys

The provided `.gitignore` blocks the common local files generated during the process.

## Scope and compatibility

This was validated on the hardware and Roku OS version listed above. Roku may change pairing, authentication, debugging, or input behavior in other models or software versions.

The public Roku LT SDK confirms that Roku hosts use a `DIRECT-roku-` SSID during pairing and require Roku-specific WPS vendor data for a remote-style enrollee. This repository documents the Linux implementation and the additional post-pairing steps discovered experimentally.

## Responsible use

Use this only with Roku devices you own or are authorized to service. The project is intended for recovery, interoperability research, diagnostics, and documentation.
