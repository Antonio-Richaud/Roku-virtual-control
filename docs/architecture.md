# Architecture

## Overview

A Roku Wi-Fi remote is not just a generic client on the user's LAN. During pairing, the Roku creates a private Wi-Fi network and provisions the remote with credentials.

The working path observed in this project is:

```text
Linux SBC / Raspberry Pi
    |
    | 1. Discover DIRECT-roku-* AP
    | 2. WPS PBC with Roku vendor data
    v
Roku WPS registrar
    |
    | 3. Issues device-specific credential
    v
External credential capture
    |
    | 4. Manual WPA2 reconnect
    v
Private Roku WLAN
    |
    | 5. DHCP
    v
Private IP connectivity
    |
    | 6. TCP 8080
    v
Roku debug/input service
    |
    | 7. Select IR_RF / Alice source
    | 8. Send keypresses
    v
Onboarding UI
```

## WPS layer

The Roku public LT SDK includes a box + remote WPS PBC test that documents Roku-specific vendor data.

The WPS M1 vendor extension is:

```text
OUI      C8:3A:6B
Type     0x01
Chip ID  32-bit little-endian
```

The association request also carries:

```text
DD 05 C8 3A 6B 00 00
```

This second element was critical in practice.

## Credential layer

The Roku issues a credential to the WPS enrollee. In the validated setup the key arrived as 64 hexadecimal characters, representing a raw 256-bit WPA PMK.

The credential should be treated as a secret equivalent to a Wi-Fi password.

A major implementation detail is that `wpa_supplicant` automatic credential processing did not produce a stable post-WPS reconnect on the tested device. Using external credential processing and manually creating the WPA2 network solved this.

## WPA2 layer

Once the fresh credential was applied manually, the station reached:

```text
wpa_state=COMPLETED
```

The Roku association IE still needed to be present when reconnecting.

## IP layer

After WPA2 association, the Roku acts as a DHCP server on its private network. The Pi obtains a private IPv4 address and can ping the Roku peer.

The exact subnet is implementation-dependent and should not be hard-coded.

## Application/input layer

Two interesting TCP services were visible:

- `8060` - Roku ECP-related service, but requests on the private remote interface were reset in the tested environment.
- `8080` - Roku debug/input console.

The port-8080 `press` help exposed internal source types. The default was `SIM`, but onboarding ignored simulated input.

Selecting:

```text
press .r
```

changed the source to:

```text
IR_RF (T3, Alice, Elk)
```

Then:

```text
press .0
press .h120 d
```

produced a real Down event accepted by onboarding.

## Why source identity matters

The same logical key (`Down`) can be injected with different source metadata. The tested onboarding screen ignored `SIM` but accepted `IR_RF` / Alice.

That means successful control depended not only on sending a key code but on making the event look as though it originated from the class of physical Roku remote expected by the input subsystem.

## Management-plane limitation

With only one Wi-Fi adapter, the Raspberry Pi cannot remain on the home WLAN while simultaneously using that same interface for the Roku private AP. SSH therefore drops during control sessions.

Two clean solutions are:

- Ethernet for management + built-in Wi-Fi for Roku.
- A second Wi-Fi adapter for management or Roku.

That separation is recommended for a permanent implementation.
