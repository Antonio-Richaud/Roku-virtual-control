#!/usr/bin/env python3
"""Minimal Roku port-8080 controller for an already-paired private Roku WLAN.

This does not perform WPS or WPA setup. Run it only after the Linux station is
already associated to the Roku private network and can reach the Roku IP.
"""

import socket
import sys
import time

if len(sys.argv) < 4:
    raise SystemExit(
        "usage: roku-8080-controller.py <LOCAL_IP> <ROKU_IP> <command> [command...]"
    )

LOCAL_IP = sys.argv[1]
ROKU_IP = sys.argv[2]
COMMANDS = sys.argv[3:]

KEYS = {
    "w": "u",
    "up": "u",
    "s": "d",
    "down": "d",
    "a": "l",
    "left": "l",
    "d": "r",
    "right": "r",
    "e": "s",
    "ok": "s",
    "select": "s",
    "enter": "s",
    "q": "k",
    "back": "k",
    "h": "h",
    "home": "h",
    "p": "p",
    "play": "p",
    "pause": "v",
    "replay": "y",
    "info": "i",
    "ff": "f",
    "rew": "b",
    "backspace": "=",
    "bs": "=",
}


def recv_prompt(sock: socket.socket, timeout: float = 0.6) -> str:
    sock.settimeout(timeout)
    data = bytearray()

    while True:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data.extend(chunk)
            if data.endswith(b">"):
                break
        except socket.timeout:
            break

    return data.decode("utf-8", errors="replace")


def send_command(sock: socket.socket, command: str, display: str | None = None) -> None:
    if display is None:
        display = command

    print(f">>> {display}")
    sock.sendall((command + "\r\n").encode("utf-8"))
    time.sleep(0.25)

    reply = recv_prompt(sock)
    cleaned = reply.strip()
    if cleaned and cleaned != ">":
        print(reply)


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(3)

if hasattr(socket, "SO_BINDTODEVICE"):
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, b"wlan0\0")
    except OSError:
        pass

sock.bind((LOCAL_IP, 0))
sock.connect((ROKU_IP, 8080))
time.sleep(0.3)
recv_prompt(sock, 1)

# The successful onboarding path configured these as separate state changes.
send_command(sock, "press .r", "source = IR_RF / Alice")
send_command(sock, "press .0", "remote-id = 0")

for raw in COMMANDS:
    token = raw.rstrip("\r\n")
    if not token:
        continue

    low = token.lower().strip()

    if low.startswith("text:"):
        text = token[5:]
        if "\n" in text or "\r" in text:
            raise SystemExit("text: does not allow embedded newlines")
        send_command(sock, "type " + text, f"type <{len(text)} chars>")
        time.sleep(0.4)
        continue

    if low.startswith("wait:"):
        try:
            delay = float(token.split(":", 1)[1])
        except ValueError as exc:
            raise SystemExit(f"invalid wait value: {token}") from exc
        time.sleep(delay)
        continue

    if low not in KEYS:
        raise SystemExit(f"unknown command: {token}")

    send_command(sock, f"press .h120 {KEYS[low]}", token)
    time.sleep(0.45)

sock.close()
