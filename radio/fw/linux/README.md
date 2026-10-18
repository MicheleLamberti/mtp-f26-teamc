# nRF24 Linux HAL and bench tool (Raspberry Pi 3)

`nrf24_hal_linux.c` implements `nrf24_hal_t` (`../nrf24.h`) on Linux: SPI through spidev, one ioctl per radio
command (`xfer`, the kernel drives CSN = CE0), CE and IRQ through the GPIO character device (uAPI v2, no
libgpiod), `CLOCK_MONOTONIC` microseconds and busy-wait delays. `nrf24_probe` is the bench tool built on it.
Started 18-Oct-26 (D-H1). The protocol's environment (`proto/src/proto_env.h` on timerfd/epoll) is the next step.

## Pi setup (Pi OS Lite)

`/boot/firmware/config.txt`:

```
dtparam=spi=on
dtoverlay=disable-wifi
dtoverlay=disable-bt
core_freq=250        # the Pi 3 SPI clock follows the core clock: fix it (8 MHz asked -> 7.8 MHz)
```

Then `sudo systemctl disable --now hciuart bluetooth wpa_supplicant` and `sudo rfkill block all`, and reboot.
Check: `ls /dev/spidev0.0 /dev/gpiochip0`. The user needs the `spi` and `gpio` groups (the default `pi`-style user
has them). For `--rt`: run as root, or `sudo setcap cap_sys_nice,cap_ipc_lock+ep radio/fw/build/nrf24_probe`, and
reserve a core with `isolcpus=3` at the end of `/boot/firmware/cmdline.txt`.

Build on the Pi: `sudo apt install build-essential python3`, then `make -C radio/fw linux` (and `make -C radio/fw test`).

## Wiring (SP4 on its breakout)

| SP4 pad | Signal | Pi 3 header pin (BCM GPIO) |
|---|---|---|
| 1 | VCC | **not the Pi's 3V3**: the radio LDO (or a bench supply) at 3.3 V, ≥ 100 µF at the module |
| 2 | CE | 15 (GPIO 22) |
| 3 | CSN | 24 (GPIO 8, SPI0 CE0) |
| 4 | SCK | 23 (GPIO 11) |
| 5 | MOSI | 19 (GPIO 10) |
| 6 | MISO | 21 (GPIO 9) |
| 7 | IRQ | 18 (GPIO 24), optional (`--irq -1` polls) |
| 8–10 | GND | 6 (any GND), common with the radio supply |

## Commands and the tests they serve (`radio/TEST_PLAN.md`)

| Command | Test |
|---|---|
| `nrf24_probe init` | T0 step 1: `nrf24_init` returns OK, register dump. `ERR_SPI` = wiring/CSN/VCC/SPI off; `ERR_NOT_PLUS` = an old nRF24L01, return it |
| `nrf24_probe tx --count 1000` on one box, `nrf24_probe rx --seconds 20` on the other | T0 step 4 (≥ 999 of 1000 at 1 m) and T2 PER steps through the attenuator |
| `tx` output "period between frames" and "per-frame gap" | T2 on the Pi: the gap the link model assumes (300 µs); 500 µs would mean ~97 kbps |
| `nrf24_probe survey --hopset --samples 1000`, Pi idle and then loaded | T0 step 5: the Pi's own noise per hop channel (load: `stress-ng --cpu 4`, an SD write, a stick copy) |
| `nrf24_probe survey --samples 500` | T14: campus channel survey, RF_CH 0–83 |
| `nrf24_probe timing`, then `nrf24_probe timing --rt 3` | Linux scheduling: worst wake-up lateness against the link's ~2.4 ms mid-burst and ~3.8 ms TX_DS budgets |

`tx` and `rx` use the 10 mW profiles only (TEAM_250K, TEAM_1M, NM_COMMON). The 20 dBm hopping profiles need a
clear-channel check per hop and go through the protocol, not this tool. Lab-only CW tests (T13) need the
`NRF24_LAB_TESTS` build of the driver.

## Not done yet

- `proto_env_t` on Linux (timerfd + epoll, `getrandom`), the radio thread loop calling `link_*_on_frame`,
  `*_on_tx_idle` and the timers; hop clock and acquisition with IRQ timestamps.
- `usbm_disk_t` on the raw stick block device; the SD-card store with `fdatasync`; systemd unit + watchdog.
- Not yet run on a Pi: no Pi or ARM compiler on the development machine. The code builds with the
  repo's strict flags (`-Wall -Wextra -Werror -Wconversion`) on x86 Linux against the same kernel headers.
