# teamc-node: the Raspberry Pi 3 transceiver program (D-H1)

One program runs the whole box: setup from the USB stick, the round (SRI, MRM or NM), STOP, saving to the
stick, and resuming by itself after a reboot. It links the same protocol code the simulator tests
(`src/link.c`, `src/nm_gossip.c`, `src/codec.c`, `src/usb_msc.c`) and the radio driver (`radio/fw/nrf24.c` with
the Linux HAL in `radio/fw/linux/`).
Its C sources use the C++17 file/Unicode layer through `test_encoding_text/encoding_stream_c.h`.
Setup and sender reads verify the SD caches. At STOP, complete streams are checked before saving;
optional strict decoding writes separate UTF-8 views to the SD card. The LaTeX/PDF guide in
`proto/test_encoding_text/guide/` documents policies, cache files and CLI options.

| File | Job |
|---|---|
| `node.c` | The program: SETUP → GO → round → STOP → save → SETUP; round.state for resume; systemd notify + watchdog |
| `radio.c` | Radio layer: TX queue, `proto_env_t`, hop clock and **hop acquisition** for TEAM_FHSS (master/slave, beacon on hop 0), CCA per hop |
| `phy_nrf24.c` | Radio backend on the E01-ML01SP4 (driver + HAL; IRQ edge timestamps for the hop sync) |
| `phy_udp.c` | Emulated radio over UDP on 127.0.0.1: airtime, half-duplex, channels, loss, busy CCAs (the e2e tests) |
| `store.c` | SD card: received bytes + a CRC-checked two-slot progress record (resume), sender's file, NM copy, round state |
| `stick.c` | The USB stick as a raw block device (`/dev/sda`) or an image file, O_DIRECT, write-protect |
| `ui.c` | Button, role switch, mode switch (SRI/MRM/NM), LEDs on GPIO; MAX17048 battery gauge; simulated UI for tests |
| `mkstick.c` | FAT/exFAT stick images for the tests (also reads a real stick without mounting it) |
| `e2e.sh` | Whole nodes against each other over the UDP radio: `make -C proto e2e` |
| `teamc-node.service`, `install.sh` | systemd unit and installer for the Pi |

## How a round runs

- **SETUP.** Plug in the stick: the largest `.txt` in the root is loaded (`usb_msc`), deflated (level 9; raw if
  that saves < 5 %), and both copies are kept on the SD card. Status LED on = a file is loaded. Both boxes load the
  file, since the professor picks the sender afterwards.
- **GO** (Tx/Rx button). The role switch (closed = TX) and the mode switch are read once:
  - SRI: link on `--sri-profile` (default TEAM_250K, 10 mW on RF_CH 74);
  - MRM: link on `--mrm-profile` (default TEAM_FHSS: 20 dBm hopping with LBT; the sender's clock leads);
  - NM: gossip on NM_COMMON (RF_CH 77, `radio/NM_SPEC.md`); role TX = the origin, which holds the NM-file.
  The activity LED blinks while in Tx/Rx; the status LED comes on when the round is complete.
- **STOP** (the button again). The receiver writes `RX_<name>` (inflated; only the in-order prefix exists, which is
  what scores) to the stick; in NM every box writes `NM_FILE.TXT` (if complete) and `NM_LOG.TXT`. Status LED fast
  blink = plug in the stick; on = saved (read-back CRC checked). Output names: Atenea Q9 is open; `--out-name` sets one.
- **Reboot in a round** (watchdog, brown-out, an "attack"): `round.state` says a round is running, so the program
  resumes it without GO. The sender re-reads its stored file and HELLOs; the receiver resumes from the last length
  the sync thread recorded (every 200 ms; anything after it is simply sent again).

## Hop sync (TEAM_FHSS) on real radios

The simulator copies the master's clock; real radios cannot. Here the slave parks on the first hop channel until
it hears the master, then estimates the master's slot start from frame timing only (`radio.h` explains the rules):
earlier frames correct at once, a late arrival halves the error, later moves only by what every frame of the last
8 slots allows. The master opens hop 0 of every cycle with a 1-byte beacon (PLL + CCA after the slot start), so a
parked or rebooted slave locks within one cycle (1.1 s). A slave changes channel 1 ms early. One silent cycle and
the slave parks again (a rebooted sender comes back on a new phase).

## Tests on a PC (no radio)

`make -C proto e2e` (~3 min) runs real nodes as processes against each other over the UDP radio, with stick images
from `mkstick`, and checks that the receiver's stick holds a byte-identical file. 18-Oct results (1500 lines,
150 kB → 60 kB deflated, two runs):

| Scenario | Receiver done after |
|---|---|
| SRI, TEAM_250K, 5 % loss | 3.7 s |
| MRM, TEAM_FHSS, 5 % loss, 10 % busy CCAs | 7.4–9.1 s |
| SRI, receiver killed (kill -9) at 3 s and restarted | 1.4–1.5 s after the restart |
| MRM, receiver killed at 5 s | 4.3–4.6 s after the restart |
| MRM, sender killed at 5 s | 8.3–9.5 s in total |
| NM, 3 nodes in a line, 10 % loss | 3.2–3.4 s at the far end |

The emulator has no per-frame gap beyond PLL settling, so its SRI rate is above what the bench will show; the
hopping rate (~60 kbps of compressed payload) is below the model's 96 kbps, because bursts that do not fit wait
for the next hop. Measure both on the Pi (T2) before trusting either.

## Pi setup

1. Pi OS Lite (64-bit). `/boot/firmware/config.txt`: `dtparam=spi=on`, `dtparam=i2c_arm=on`,
   `dtoverlay=disable-wifi`, `dtoverlay=disable-bt`, `core_freq=250`. Kernel command line: add `isolcpus=3`.
   `sudo systemctl disable --now hciuart bluetooth wpa_supplicant`.
2. A small ext4 **data partition** mounted at `/data` (e.g. `/dev/mmcblk0p3 /data ext4 defaults,noatime 0 2` in
   `/etc/fstab`). Then make the root read-only: `sudo raspi-config nonint enable_overlayfs`. The overlay covers only
   the root partition, so `/data` stays writable and survives reboots; a power cut cannot corrupt the root.
3. Hardware watchdog: `RuntimeWatchdogSec=10` in `/etc/systemd/system.conf`.
4. Wiring and the radio bench tool: `radio/fw/linux/README.md` (`nrf24_probe init` first).
5. `sh proto/port/linux/install.sh` from the repo root (edit `--box` in the unit first), then
   `journalctl -u teamc-node -f` to watch it. To test without the service: `sudo systemctl stop teamc-node` and
   run `/opt/teamc/teamc-node --data /tmp/t` by hand.

## Still to do on hardware

- Bench: `nrf24_probe` T0/T2 on two Pis, then two boxes with teamc-node; tune `RADIO_GUARD_US` and the link timers
  from measured turnaround and jitter (`nrf24_probe timing --rt 3`).
- The 3-position mode switch (GPIO 23 + 16) and the MAX17048 are on the HAT design (KiCad brief), not yet built.
