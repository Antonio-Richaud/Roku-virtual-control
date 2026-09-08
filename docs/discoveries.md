# Discoveries and dead ends

This document records the experimental path so future work does not repeat the same dead ends.

## Confirmed findings

### Roku-specific WPS data is required

The successful pairing path required:

```text
M1 vendor payload: C8 3A 6B 01 <chip-id little-endian>
Association IE:    DD 05 C8 3A 6B 00 00
```

The public Roku LT SDK documents the same Roku OUI and association element in its box + remote WPS PBC unit test.

### WPS success and WPA success are separate events

WPS reached `WPS-SUCCESS`, but the automatic post-WPS reconnect failed.

Using `wps_cred_processing=1`, capturing the fresh credential externally, cancelling WPS, and then manually creating the WPA2 network resulted in a successful four-way handshake.

### The credential is enrollee-specific

The WPS credential contained the enrollee MAC address. Treat the resulting network key as device-specific pairing material and never publish it.

### The Roku private AP provides DHCP

After successful WPA2 association the Roku served DHCP to the emulated remote. IP connectivity and ping worked normally.

### Port 8080 is the useful input path on the tested firmware

The service identified itself as the Roku debug terminal and exposed a `press` command.

The help output also exposed input-source metadata:

```text
r = IR_RF (T3, Alice, Elk)
w = WD (Wifi)
e = ECP
c = CEC
s = SIM(ulated)
u = IR_RF_UNPAIRED
```

The default source was `SIM`.

### Onboarding ignores the default simulated source

A plain:

```text
press d
```

returned a prompt but did not move the UI.

### Alice / IR_RF works

This sequence succeeded:

```text
press .r
press .0
press .h120 d
```

It woke the Roku from inactivity mode and moved the language selector.

### Stateful configuration matters

This combined form did not work reliably:

```text
press .r .0 .h120 d
```

Configuring source and remote ID as separate commands before the keypress did work.

## Tested approaches that did not solve onboarding

### HDMI-CEC

CEC transmission itself worked at the bus level, including directed user-control frames to the Roku playback device, but the onboarding UI did not react.

Conclusion: do not assume a factory-reset Roku will accept CEC navigation during onboarding.

### Generic Wi-Fi Direct / P2P association

A generic P2P client could associate and even receive private-network addressing, but that alone did not make it an accepted Roku remote.

The Roku-specific WPS path and vendor metadata were necessary.

### ECP over 8060

TCP 8060 accepted a connection but reset HTTP requests on the private remote interface.

The same happened when attempting a WebSocket upgrade for ECP2.

Conclusion: on the tested Roku OS 14.1.4 onboarding/private-remote state, 8060 was not a useful navigation path.

### Port 8080 with default source

The console accepted `press d`, but because the default source is `SIM`, onboarding did not move.

This was the final obstacle before success.

## Important diagnostic principle

At each layer, prove one thing at a time:

```text
WPS credential received
        ↓
WPA2 COMPLETED
        ↓
DHCP lease obtained
        ↓
ARP / ping works
        ↓
TCP service reachable
        ↓
input metadata correct
        ↓
UI moves
```

Do not jump to a higher layer while a lower one is still unproven.
