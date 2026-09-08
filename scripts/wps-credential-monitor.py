#!/usr/bin/env python3
"""Capture a WPS-CRED-RECEIVED event from a wpa_supplicant control socket.

The secret credential is written to a root-only JSON file and is never printed.
This helper is intended to be launched by a root-run pairing script using
wps_cred_processing=1.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import socket
import tempfile
import time
from pathlib import Path

ATTR_CREDENTIAL = 0x100E
ATTR_NETWORK_INDEX = 0x1026
ATTR_SSID = 0x1045
ATTR_AUTH_TYPE = 0x1003
ATTR_ENCR_TYPE = 0x100F
ATTR_NETWORK_KEY = 0x1027
ATTR_MAC_ADDR = 0x1020


def tlvs(data: bytes):
    pos = 0
    while pos + 4 <= len(data):
        attr = int.from_bytes(data[pos : pos + 2], "big")
        length = int.from_bytes(data[pos + 2 : pos + 4], "big")
        pos += 4
        if pos + length > len(data):
            raise ValueError("truncated WPS TLV")
        value = data[pos : pos + length]
        pos += length
        yield attr, value


def parse_credential(raw: bytes) -> dict:
    outer = list(tlvs(raw))

    # Some control events contain the full Credential attribute; others expose
    # the inner attribute sequence. Support both forms.
    if len(outer) == 1 and outer[0][0] == ATTR_CREDENTIAL:
        attrs = dict(tlvs(outer[0][1]))
    else:
        attrs = dict(outer)

    ssid = attrs.get(ATTR_SSID, b"")
    key = attrs.get(ATTR_NETWORK_KEY, b"")
    mac = attrs.get(ATTR_MAC_ADDR, b"")

    if not ssid or not key:
        raise ValueError("credential is missing SSID or network key")

    key_mode: str
    pmk_hex: str | None = None
    pass_b64: str | None = None

    try:
        key_ascii = key.decode("ascii")
    except UnicodeDecodeError:
        key_ascii = ""

    if len(key) == 32:
        key_mode = "raw-pmk-binary"
        pmk_hex = key.hex()
    elif len(key_ascii) == 64 and all(c in "0123456789abcdefABCDEF" for c in key_ascii):
        key_mode = "raw-pmk-hex"
        pmk_hex = key_ascii.lower()
    else:
        key_mode = "passphrase"
        pass_b64 = base64.b64encode(key).decode("ascii")

    result = {
        "ssid_b64": base64.b64encode(ssid).decode("ascii"),
        "key_mode": key_mode,
        "key_length": len(key),
        "key_sha256": hashlib.sha256(key).hexdigest(),
        "auth_type": attrs.get(ATTR_AUTH_TYPE, b"").hex(),
        "encr_type": attrs.get(ATTR_ENCR_TYPE, b"").hex(),
        "cred_mac": ":".join(f"{b:02x}" for b in mac) if len(mac) == 6 else None,
    }

    if pmk_hex is not None:
        result["pmk_hex"] = pmk_hex
    if pass_b64 is not None:
        result["pass_b64"] = pass_b64

    return result


def atomic_write_secret(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
        path.chmod(0o600)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ctrl-dir", required=True, help="wpa_supplicant ctrl_interface directory")
    parser.add_argument("--interface", default="wlan0")
    parser.add_argument("--output", default="/run/roku-fresh-cred.json")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    server = os.path.join(args.ctrl_dir, args.interface)
    local = f"/run/roku-wps-monitor-{os.getpid()}.sock"

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        try:
            os.unlink(local)
        except FileNotFoundError:
            pass

        sock.bind(local)
        os.chmod(local, 0o600)
        sock.connect(server)
        sock.settimeout(2.0)
        sock.send(b"ATTACH")
        reply = sock.recv(4096)
        if not reply.startswith(b"OK"):
            raise RuntimeError(f"ATTACH failed: {reply!r}")

        deadline = time.monotonic() + args.timeout

        while time.monotonic() < deadline:
            try:
                msg = sock.recv(65535).decode("utf-8", errors="replace")
            except socket.timeout:
                continue

            marker = "WPS-CRED-RECEIVED "
            pos = msg.find(marker)
            if pos < 0:
                continue

            cred_hex = msg[pos + len(marker) :].strip().split()[0]
            credential = parse_credential(bytes.fromhex(cred_hex))
            atomic_write_secret(Path(args.output), credential)

            # Safe metadata only. Never print the key itself.
            ssid = base64.b64decode(credential["ssid_b64"]).decode("utf-8", errors="replace")
            print("CREDENTIAL RECEIVED")
            print(f"SSID={ssid}")
            print(f"CRED_MAC={credential.get('cred_mac')}")
            print(f"KEY_MODE={credential['key_mode']}")
            print(f"KEY_LENGTH={credential['key_length']}")
            print(f"KEY_SHA256={credential['key_sha256']}")
            return 0

        raise TimeoutError("timed out waiting for WPS-CRED-RECEIVED")
    finally:
        try:
            sock.close()
        finally:
            try:
                os.unlink(local)
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
