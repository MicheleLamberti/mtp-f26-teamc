#!/bin/sh
# MTP-F26 Team C - install teamc-node on the Raspberry Pi 3 (run from the repo root, with sudo rights).
# It builds, copies the binary and the systemd unit, and enables the service. It does not touch
# /boot/firmware/config.txt or the partitions: do those by hand (proto/port/linux/README.md, "Pi setup").
set -eu
make -C radio/fw linux
make -C proto linux
sudo install -d /opt/teamc /data/teamc
sudo install -m 755 proto/build/teamc-node proto/build/mkstick radio/fw/build/nrf24_probe /opt/teamc/
sudo install -m 644 proto/port/linux/teamc-node.service /etc/systemd/system/teamc-node.service
sudo systemctl daemon-reload
sudo systemctl enable teamc-node.service
echo "installed. Start it now with: sudo systemctl start teamc-node   (logs: journalctl -u teamc-node -f)"
