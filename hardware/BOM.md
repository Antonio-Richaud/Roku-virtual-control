# Hardware bill of materials

## Required

| Item | Purpose | Notes |
|---|---|---|
| Roku Streaming Stick / Roku device | Target device | Procedure validated on Streaming Stick+ 3810X / 3810CA |
| Raspberry Pi 4 | Emulates the Roku Wi-Fi remote | Other Linux SBCs may work if their Wi-Fi stack supports the required operations |
| microSD card | Raspberry Pi OS | 8 GB minimum; 16 GB+ recommended |
| Raspberry Pi power supply | Stable SBC power | Use a reliable supply |
| micro-HDMI / HDMI connection for the Pi | Optional visual/debug path | Not required for the successful control method itself |
| Mac, PC, or another SSH client | Administration | Used to prepare and control the Raspberry Pi |
| Existing Wi-Fi network | Administration path | Useful so the Pi can restore normal SSH connectivity after each Roku session |

## Optional

| Item | Why it may help |
|---|---|
| Ethernet adapter | Gives the Pi a management path while Wi-Fi is dedicated to Roku |
| Second Wi-Fi adapter | Makes simultaneous home-network + Roku-network control much easier |
| HDMI capture device | Useful for remote visual monitoring, but not needed for pairing/control |
| USB serial adapter | Useful for SBC debugging only |

## What was not required

The successful method did **not** require:

- a genuine Roku remote,
- HDMI-CEC control,
- an IR blaster,
- Bluetooth,
- a Wi-Fi password for the Roku private network ahead of time,
- a factory reset after the pairing experiments.

## Wi-Fi requirements

The Linux Wi-Fi adapter must support normal managed mode and allow `wpa_supplicant` / `wpa_cli` control. The Raspberry Pi 4 built-in radio was sufficient in the validated setup.

The Roku private AP was observed on 5 GHz channel 36. Your device may choose a different channel, so discover it dynamically with `iw` / `wpa_cli scan_results` rather than hard-coding it.
