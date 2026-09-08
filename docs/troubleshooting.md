# Troubleshooting

## `wpa_state` never reaches `COMPLETED`

Check these in order:

1. The Roku is still advertising a `DIRECT-roku-*` SSID.
2. The station is using the correct BSSID and channel.
3. The association vendor IE is loaded before association:

```bash
wpa_cli -i wlan0 vendor_elem_add 13 dd05c83a6b0000
```

4. The credential being used is the freshly harvested credential for this enrollee.
5. The raw 64-hex credential is written as an unquoted `psk=` value.
6. NetworkManager is not racing with the standalone `wpa_supplicant`.

Useful commands:

```bash
wpa_cli -i wlan0 status
iw dev wlan0 link
journalctl -u wpa_supplicant --no-pager -n 100
```

## WPS succeeds but WPA2 fails with `WRONG_KEY`

This was the exact failure that led to the external-credential solution.

Do not immediately assume the WPS credential is invalid.

Try:

- `wps_cred_processing=1`,
- capture `WPS-CRED-RECEIVED`,
- cancel WPS,
- create the WPA2 network manually,
- retain the Roku association vendor IE,
- reconnect immediately.

That sequence converted the tested setup from repeated handshake failure to `COMPLETED`.

## WPA2 works but DHCP does not appear on the interface

`udhcpc` can successfully obtain a lease while a custom callback fails to apply it.

Look at the raw DHCP output first:

```text
lease of <LOCAL_IP> obtained from <ROKU_IP>
```

Then apply the address/routing manually if needed:

```bash
sudo ip addr add <LOCAL_IP>/<PREFIX> dev wlan0
sudo ip route replace <ROKU_IP>/32 dev wlan0 scope link src <LOCAL_IP>
```

Prefer learning the actual subnet mask from DHCP instead of assuming `/24` in production tooling.

Verify:

```bash
ip -br addr show wlan0
ip route show dev wlan0
ip neigh show dev wlan0
```

## Ping works but ECP 8060 resets

That is not a Wi-Fi failure.

In the validated setup:

- WPA2 was complete,
- DHCP worked,
- ARP was reachable,
- ping succeeded,
- TCP 8060 accepted SYN/SYN-ACK,
- the Roku reset the application request.

Move on to the 8080 input/debug path rather than repeatedly debugging lower network layers.

## Port 8080 is open but `press d` does nothing

Run:

```text
press
```

and inspect the source types.

The tested firmware defaults to `SIM`, which onboarding ignored.

Set the source and remote ID separately:

```text
press .r
press .0
```

Then send:

```text
press .h120 d
```

## `press .r .0 .h120 d` does nothing

Do not combine the state modifiers.

Use separate commands:

```text
press .r
press .0
press .h120 d
```

This distinction was critical in the successful test.

## Roku is in inactivity / power-saving mode

A valid remote keypress should wake it.

That makes power-saving mode a useful diagnostic: if a command wakes the screen, the input path is working even before you verify UI navigation.

## SSH disconnects during every test

Expected when the Pi has one Wi-Fi interface and that interface is moved from the home WLAN to the Roku private WLAN.

For a permanent setup, use:

- Ethernet for management, or
- a second Wi-Fi adapter.

Otherwise make sure every control script has a cleanup trap that restores NetworkManager and the normal Wi-Fi profile.

## Pi does not return to the home network

Try locally or after reboot:

```bash
sudo systemctl start wpa_supplicant
sudo systemctl start NetworkManager
sudo nmcli radio wifi on
sudo nmcli connection up <HOME_PROFILE>
```

Also remove stale temporary P2P interfaces if they exist:

```bash
for IF in $(iw dev | awk '$1=="Interface" && $2 ~ /^p2p-wlan0-/ {print $2}'); do
  sudo iw dev "$IF" del 2>/dev/null || true
done
```

## `cat` on generated capture/log says permission denied

Some files created by root-run scripts remain root-owned.

Either inspect them with `sudo` or explicitly hand ownership back at cleanup:

```bash
sudo chown $USER:$USER /path/to/file
```

Never change ownership of the persisted Roku credential file; keep that root-only.

## Need to start over

Avoid factory-resetting the Roku unless absolutely necessary. If the private `DIRECT-roku-*` AP still advertises WPS PBC, pairing can often be repeated without another reset.

If the Pi is in a confused state, rebooting the Pi is safer than resetting the Roku.
