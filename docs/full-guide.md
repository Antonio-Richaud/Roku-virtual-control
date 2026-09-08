# Full recovery guide

This guide documents the complete workflow that succeeded in controlling and onboarding a factory-reset Roku Streaming Stick+ without a physical Roku remote.

## 1. Goal

The target condition is a Roku stuck at first-boot onboarding, for example the language-selection screen, with no working physical remote and therefore no way to join the Roku to the user's normal Wi-Fi.

The solution is to make a Linux Wi-Fi station behave closely enough like a Roku Wi-Fi remote that the Roku provisions it, accepts a WPA2 association, and then accepts remote-key events through the device's port-8080 debug input path.

## 2. Tested platform

Validated with:

- Roku Streaming Stick+ 3810X / 3810CA
- Roku OS 14.1.4.7709
- Raspberry Pi 4
- Raspberry Pi OS Lite 64-bit / Debian Trixie
- built-in Raspberry Pi Wi-Fi

The exact SSID, BSSID, channel, private IP addresses, and WPS credential are device/session-specific. Discover them dynamically.

## 3. Install software

```bash
sudo apt-get update
sudo apt-get install -y \
  wpasupplicant \
  wireless-tools \
  iw \
  iproute2 \
  busybox \
  tcpdump \
  curl \
  python3
```

See `scripts/install-deps.sh` for the repository version.

## 4. Preserve a recovery path

The successful workflow temporarily takes control of `wlan0` away from NetworkManager and the system `wpa_supplicant`. If you administer the Pi over Wi-Fi, SSH will disconnect while the Pi is attached to the Roku.

Before experimenting:

- confirm the Pi can automatically reconnect to your normal Wi-Fi,
- preferably assign it a known DHCP reservation,
- verify SSH keys work,
- consider Ethernet or a second Wi-Fi adapter for uninterrupted management.

A robust experiment script should always use a cleanup trap that restarts NetworkManager and reconnects the management profile.

## 5. Discover the Roku private AP

During remote-pairing mode, Roku advertises a private AP with a name similar to:

```text
DIRECT-roku-XXX-XXXXXX
```

The public Roku LT SDK explicitly uses `DIRECT-roku-` as the default host-SSID prefix for its box + remote WPS pairing test.

Typical discovery commands:

```bash
sudo iw dev wlan0 scan | less
```

or with a temporary `wpa_supplicant` control interface:

```bash
wpa_cli -i wlan0 scan
sleep 2
wpa_cli -i wlan0 scan_results
```

Record, but do not commit:

- Roku SSID
- Roku BSSID
- frequency/channel

## 6. Why ordinary WPS is not enough

A generic WPS-PBC enrollee is not sufficient.

Roku's own LT SDK test shows two Roku-specific pieces of data:

### WPS M1 vendor extension

The payload is:

```text
C8 3A 6B 01 <chip-id little-endian, 4 bytes>
```

Meaning:

- Roku OUI: `C8:3A:6B`
- message type: `01`
- 32-bit chip ID, little-endian

### Association-request vendor IE

The full information element is:

```text
DD 05 C8 3A 6B 00 00
```

In `wpa_cli`, this is added to association-request frame type 13:

```bash
wpa_cli -i wlan0 vendor_elem_add 13 dd05c83a6b0000
```

This was essential. Without the Roku association IE, the Roku behaved like the station was a generic WPA2 client and the expected remote WPS path did not complete correctly.

## 7. Build a stable chip ID

The Roku M1 vendor extension requires a 32-bit chip ID. On a Raspberry Pi, one practical approach is deriving a stable 32-bit value from hardware identity such as the Pi serial number.

Example concept:

```python
chip_id = int(pi_serial[-8:], 16) & 0xffffffff
chip_le = chip_id.to_bytes(4, "little").hex()
m1_vendor = "c83a6b01" + chip_le
```

The exact value is not a secret, but keep it stable for repeatability.

## 8. Important `wpa_supplicant` behavior

The turning point was using:

```text
wps_cred_processing=1
```

This tells `wpa_supplicant` to emit the WPS credential to an external controller instead of automatically installing it.

Why this mattered:

- WPS itself completed successfully.
- the automatic post-WPS WPA2 reconnect repeatedly failed on the tested Roku.
- when the freshly received credential was captured externally and a new WPA2 network was created manually, the WPA2 four-way handshake completed immediately.

Do not assume a `WPS-SUCCESS` event means the final remote WPA2 connection is ready.

## 9. Minimal standalone WPS configuration

Create a runtime-only configuration. Never put the harvested credential in the repository.

```text
ctrl_interface=/run/wpa_supplicant-roku
update_config=0
country=<YOUR_COUNTRY_CODE>
device_name=Roku Remote
manufacturer=Roku
model_name=RC-AL2
model_number=RC-AL2
config_methods=physical_push_button
wps_cred_processing=1
wps_vendor_ext_m1=<M1_VENDOR_HEX>
```

Then:

```bash
sudo systemctl stop NetworkManager
sudo systemctl stop wpa_supplicant
sudo ip link set wlan0 up

sudo wpa_supplicant \
  -B \
  -D nl80211 \
  -i wlan0 \
  -c /run/roku-wps.conf
```

Add the association IE before WPS:

```bash
wpa_cli \
  -i wlan0 \
  vendor_elem_add 13 dd05c83a6b0000
```

Start WPS against the Roku BSSID:

```bash
wpa_cli \
  -i wlan0 \
  wps_pbc <ROKU_BSSID>
```

## 10. Capture the WPS credential safely

With `wps_cred_processing=1`, monitor the control socket for:

```text
WPS-CRED-RECEIVED <hex-encoded WPS Credential attribute block>
```

Parse the WPS TLVs and extract:

- SSID
- authentication type
- encryption type
- network key
- credential MAC address

In the successful test, the credential MAC matched the Raspberry Pi `wlan0` MAC, which is expected for a credential issued to that enrollee.

The observed network key was represented as 64 hexadecimal characters, i.e. a raw 256-bit WPA PMK rather than a human-readable passphrase.

Never print the key to a terminal transcript or commit it.

## 11. Cancel WPS and reconnect manually

Once the credential has been captured:

```bash
wpa_cli -i wlan0 wps_cancel
```

Create a new WPA2 network using the fresh credential.

For a raw 64-hex PMK:

```text
network={
    ssid="<DIRECT-roku-...>"
    bssid=<ROKU_BSSID>
    psk=<64_HEX_RAW_PMK>
    proto=RSN
    key_mgmt=WPA-PSK
    pairwise=CCMP
    auth_alg=OPEN
    scan_ssid=1
}
```

Critical detail: keep the Roku association vendor IE active before enabling/selecting the network:

```bash
wpa_cli -i wlan0 vendor_elem_add 13 dd05c83a6b0000
```

Then enable/select/reassociate.

Success looks like:

```text
wpa_state=COMPLETED
```

and in the log:

```text
WPA: Key negotiation completed
CTRL-EVENT-CONNECTED
```

## 12. Persist the successful credential securely

After a proven connection, save the private network configuration in a root-only file such as:

```text
/etc/roku-remote-wpa.conf
```

Set permissions:

```bash
sudo chmod 600 /etc/roku-remote-wpa.conf
sudo chown root:root /etc/roku-remote-wpa.conf
```

Do not commit this file.

Once this credential is preserved, later control sessions do not need WPS again.

## 13. Obtain an IP from the Roku

The Roku runs DHCP on the private remote network.

Use:

```bash
sudo busybox udhcpc \
  -i wlan0 \
  -n \
  -q \
  -t 5 \
  -T 2
```

The tested device issued a private address in `172.29.243.x`, but the actual subnet must be learned at runtime.

Verify:

```bash
ip -br addr show wlan0
ip route show dev wlan0
ip neigh show dev wlan0
ping -I wlan0 -c 2 <ROKU_IP>
```

A successful session should show:

- a local IPv4 address,
- a Roku peer/DHCP-server address,
- ARP `REACHABLE`,
- successful ICMP replies.

## 14. What did not control onboarding

Several plausible routes were tested and ruled out for this device/firmware:

### HDMI-CEC

CEC frames were transmitted successfully to the Roku playback logical address, but the onboarding UI ignored them.

### ECP on TCP 8060

TCP 8060 accepted the connection, but `/query/device-info` and ECP2 WebSocket upgrade attempts were reset by the Roku on the private remote interface.

### Port 8080 with default source

`press d` was accepted by the debug console but did not move the onboarding UI because the default source was `SIM`.

### Port 8080 with combined modifiers

This form did not work as expected:

```text
press .r .0 .h120 d
```

The successful form configured state separately.

## 15. Discovering the working input path

Connecting to TCP 8080 returned a Roku debug prompt. Running:

```text
press
```

showed the input map and, crucially, the source selector:

```text
.ibmfwrecsu  Change source type
...
r = IR_RF (T3, Alice, Elk)
w = WD (Wifi)
e = ECP
c = CEC
s = SIM(ulated)
u = IR_RF_UNPAIRED
(default is SIM)
```

The tested Wi-Fi remote family is Alice / RC-AL2, so the working sequence became:

```text
press .r
press .0
press .h120 d
```

The first real test both woke the Roku from inactivity/power-saving mode and moved the selection from English to Deutsch.

That proved the remote event path was working.

## 16. Button map

The Roku 8080 prompt reported these useful mappings:

| Action | 8080 key |
|---|---|
| Home | `h` |
| Up | `u` |
| Down | `d` |
| Right | `r` |
| Left | `l` |
| Select | `s` |
| Fast-forward | `f` or `>` |
| Reverse | `b` or `<` |
| Play | `p` |
| Instant Replay | `y` |
| Info | `i` |
| Back | `k` |
| Backspace | `=` |
| Enter | `e` |
| Pause | `v` |

Use a normal press duration, for example:

```text
press .h120 u
press .h120 d
press .h120 l
press .h120 r
press .h120 s
press .h120 k
```

Configure source and remote ID once per 8080 session:

```text
press .r
press .0
```

## 17. Text input

The 8080 console also exposes:

```text
type <literal text>
```

This can dramatically simplify SSID/password entry compared with navigating the on-screen keyboard.

For secrets, do not put the password directly in shell history. Read it silently and pass it through a protected runtime file or process stdin.

## 18. Finishing onboarding

Once software keypresses work, onboarding becomes ordinary remote control:

1. select language,
2. join the desired Wi-Fi network,
3. enter password,
4. complete Roku setup.

After the Roku joins the normal LAN, standard Roku control mechanisms may become available depending on Roku OS settings and version.

## 19. Recovery after each experiment

If the Pi uses the same Wi-Fi interface for administration and Roku control, restore normal networking after every session:

```bash
sudo systemctl start wpa_supplicant
sudo systemctl start NetworkManager
sudo nmcli connection up <NORMAL_WIFI_PROFILE>
```

If SSH does not return, rebooting the Pi clears temporary runtime state and normally restores NetworkManager-managed Wi-Fi.

## 20. Final architecture

The proven chain is:

```text
Raspberry Pi
    |
    | WPS PBC + Roku M1 vendor extension
    | Association IE dd05c83a6b0000
    v
Roku private DIRECT-roku-* AP
    |
    | fresh credential captured externally
    v
Manual WPA2 reconnect
    |
    | WPA four-way handshake
    v
DHCP on Roku private network
    |
    | TCP 8080
    v
Roku debug input service
    |
    | press .r
    | press .0
    | press .h120 <key>
    v
Onboarding UI controlled as Alice / IR_RF remote
```

That is the core discovery documented by this repository.
