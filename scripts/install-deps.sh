#!/usr/bin/env bash
set -Eeuo pipefail

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

echo "Dependencies installed."
