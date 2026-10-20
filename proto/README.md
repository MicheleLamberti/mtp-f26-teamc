# Team C protocol code + PC simulator

The protocol code that runs on the Raspberry Pi 3 (`port/linux/teamc-node`, Linux; the Pico 2 until 18-Oct), plus a laptop simulator that runs that
same code against a modelled radio channel in simulated time. A 2-minute round takes
milliseconds, so protocols & software can develop, measure and break the protocol
before any hardware exists. Proposal it implements:
https://claude.ai/artifact/6g1P41SGs1eGf9Jme8YsAK

```
make test                     # build, generate sample files, run the simulator suite and the usb_msc tests (~2 s)
make linux                    # the Pi 3 program build/teamc-node + build/mkstick (port/linux/README.md)
make e2e                      # whole nodes against each other over the emulated UDP radio (~3 min)
make encoding-e2e             # node file/Unicode integration, corruption checks and partial STOP
make usb-xcheck PYTHON=...    # usb_msc vs pyfatfs on FAT16/FAT32 images (pip install pyfatfs "setuptools<81")
./build/sim sri --loss 0.1 --blackout 20:30 --rx-reboot 40
./build/sim sri --codec none --profile 1m --file my_file.txt
./build/sim sri --fhss 0.25 --loss 0.05       # SRI/MRM baseline (D-R6): adaptive FHSS + LBT, 25 % busy
./build/sim sri --rx-reboot 15 --reboot-down 30   # a Pi 3 (Linux) box is down 10-30 s per reboot, the Pico 0.3 s
./build/sim nm --nodes 12 --p1 0.2 --p2 0.8 --seed 7
```
Needs gcc, make, zlib (`libz-dev`) and Python 3 with `pypdf` (sample generator only).
The Linux node also needs a C++17 compiler and libstdc++; `build-essential` supplies both on Raspberry Pi OS.

## Layout

| Path | What |
|---|---|
| `src/proto_env.h` | Platform interface: `send`, `now_us`, `set_timer`, `rand32`. The protocol never touches hardware directly. |
| `src/frames.h` | Frame formats (DATA, ACK, HELLO, HELLO_ACK, END, POLL, NM_DATA), all ≤ 32 B (nRF24 payload). |
| `src/link.c` | SRI/MRM link: selective-repeat ARQ, 16-frame bursts, bitmap ACK, HELLO resume, timeouts scaled to the bit rate. |
| `src/nm_gossip.c` | Network Mode: Trickle gossip (RFC 6206), software CRC-16, no routing; keeps a relay trace (times, broadcasts). Implements the inter-team spec `../radio/NM_SPEC.md` (sim T18 checks its test vector). |
| `src/nm_log.c` | NM relay log: plain-text evidence written next to the NM-file copy on the USB stick (file id, CRC-32, when it arrived, what we rebroadcast). |
| `src/usb_msc.c` | USB stick file I/O over FatFs (FAT12/16/32, exFAT): pick the input `.txt`, load it in 4 KB chunks to flash, save the received file + log (`.part`, read-back CRC, rename). |
| `src/usb_diskio.c` | FatFs disk layer → `usbm_disk_t` (the stick's raw block device on the Pi 3, a RAM disk in the tests). |
| `third_party/fatfs/` | ChaN FatFs R0.15a (BSD-style licence in `ff.c`); `ffconf.h` is ours: LFN, exFAT, code page 850, no RTC. |
| `port/linux/` | **The Raspberry Pi 3 program `teamc-node`** (18-Oct): radio layer with the hop sync, nRF24 and UDP-emulated radios, SD-card store, stick as a raw block device, GPIO UI, systemd unit; `make linux`, `make e2e`. See `port/linux/README.md`. (The Pico 2 glue `port/pico/` was removed, in git history.) |
| `tests/test_usb.c` | `usb_msc` host tests on FAT16/FAT32/exFAT RAM disks, a Windows-style MBR stick, UTF-8 names and a write-protected stick (116 checks); `--image` mode for `tools/fat_xcheck.py`. |
| `src/codec.c` | deflate/inflate via the zlib API (the system zlib on the Pi 3 and in the simulator). |
| `sim/sim.c` | Discrete-event channel: half-duplex radios, airtime from `radio/fw` (nRF24), collisions, loss, bursts, blackout, reboots; FHSS + LBT radio layer (D-R6, the SRI/MRM baseline). |
| `sim/main.c` | Scenarios, competition-style scoring, CLI, test suite. |
| `tools/make_sample.py` | 10 000 × 100 B test file from the course PDFs (UTF-8 or UTF-16). |
| `test_encoding_text/` | Python/C++ file/Unicode layer and C bridge linked into `teamc-node`: verified SD caches, sender reads, BOM inspection and separate UTF-8 views. Run `make -C test_encoding_text test` and `make encoding-e2e`; usage is in `test_encoding_text/guide/main.pdf` (LaTeX source alongside). |

Scoring follows the rules: at STOP the receiver's bytes are decompressed and compared with
the original, and only the first continuous run of identical lines counts.

## Results (9-Oct-26, nRF24 at 250 kbps, 32 B frames, seed 1)

Band switch to 2.4 GHz (radio/DECISIONS.md D-R1b): frames shrank from 64 B to 32 B (DATA payload
60 → 28 B, HELLO name ≤ 21, NM chunk 25 B) and the air rate rose from 100 to 250 kbps. Without
docs/ the sample generator falls back to repo text (2.62× deflate instead of 3.38×).

| Scenario | Lines | Whole file in |
|---|---|---|
| Clean channel | 10 000 | 23.9 s |
| 5 % random loss | 10 000 | 28.0 s |
| **No compression**, 5 % loss | **10 000** | 73.5 s (was 9 643 lines at 868 MHz) |
| Bursty fades (~6 % loss) | 10 000 | 29.7 s |
| 10 s jamming attack + 5 % loss | 10 000 | 38.1 s (link back 0.09 s after the attack) |
| Receiver / sender reboot at 15 s | 10 000 | 28.3 s |
| 1 Mbps profile (TEAM_1M), 5 % loss | 10 000 | 12.6 s |
| UTF-16 file (2 MB, 4.23×), 5 % loss | 10 000 | 34.9 s |
| NM, 10 nodes, 10 % / 70 % loss (1 / 2 hops) | all nodes | 12.0 s |
| NM, 10 nodes, 30 % / 95 % loss | all nodes | 42.9 s |
| **FHSS + LBT** (D-R6, MRM baseline), 5 % loss, 10 % of hops busy | 10 000 | 37.9 s |
| **FHSS + LBT**, 25 % of hops busy, receiver reboot at 15 s | 10 000 | 57.2 s |
| **MRM, all four teams hopping at 20 dBm**: 30 % loss both ways, 10 % busy | 10 000 | 83.4 s |
| MRM as T14 (5 % data / 30 % ACK loss), receiver (Pi 3) down 30 s after a reboot at 15 s (T19, 18-Oct) | 10 000 | 90.8 s |

FHSS (16-Oct-26, `--fhss BUSY`, profile `TEAM_FHSS`): the protocol does not change; the simulated radio
hops every 30 ms over the 40-channel hop order from `nrf24_config.h`, spends 300 µs per hop on PLL settling
+ CCA, never lets a frame cross a hop, skips hops whose CCA is busy (drawn per node and hop), and a node
that starts or reboots cannot receive until it has re-found the hop timing (worst case one 1.2 s cycle). The simulated link does not align its bursts with the hops (the Pico
design will: one 16-frame burst + ACK per 30 ms hop), so these times are slightly pessimistic.
Higher power is not modelled here: the +10.5 dB shows up as lower loss on the real link.

The 7-Oct RFM69 results (100 kbps, 64 B frames) are in git history. The simulator once caught a
real bug there: with fixed timeouts the 38.4 kbps fallback delivered 883 lines, because one frame
outlasted the receiver's idle-ACK timer. Timeouts still derive from the bit rate (T8 checks it).

## Model assumptions (replace with bench measurements)

- Turnaround RX↔TX 1 ms, 0.3 ms gap between frames in a burst (130 µs nRF24 PLL settling + FIFO load)
  (`sim.c`, `link.c`).
- Loss is a fixed probability per link (plus optional Gilbert-Elliott fades). It is not yet
  derived from the link budget or from measured PER (test T2/T4).
- Collisions destroy both frames (no capture effect). Range for hearing = range for interfering.
- Not modelled: CPU time for compression, Linux scheduling jitter (up to ~1.1 ms on a stock kernel), SD-card sync
  time, USB copy time. Reboot downtime is set with `--reboot-down` (T19: 30 s).

## Not done yet

- MRM scenario with the 4 teams' hopping boxes modelled explicitly (today their effect is a loss rate, T14).
- The Linux program (`port/linux/`, 18-Oct) is complete and tested node-to-node over the emulated radio
  (`make e2e`), but not yet run on a Pi with real radios: bench T0/T2 with `radio/fw/linux/nrf24_probe`, then two
  boxes; tune the hop guard (`RADIO_GUARD_US`) and the link timers from measured turnaround and jitter.
- The simulator still copies the master's hop clock exactly; the real acquisition (beacon + timing estimate,
  `port/linux/radio.h`) is only exercised by the e2e tests.
- Output file name and encoding on the stick: Atenea Q9 (today `RX_<name>`, `NM_FILE.TXT`, `NM_LOG.TXT`).
- USB sticks: FAT12/16/32 and exFAT, MBR or GPT (macOS) tables, UTF-8 names all work; NTFS/APFS/HFS+ sticks do not.
  The team brings its own FAT32/exFAT sticks.
