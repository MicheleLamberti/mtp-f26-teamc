# MTP F26 · Team C workspace

Santiago's working repository for the **MTP F26** course project at UPC (Network Upgrade III +
Sustainability competition), shared with Team C. It holds the radio team's analysis and
firmware, plus the starting protocol code and simulator handed to protocols & software.

> **Status (17-Oct-26):**
> - **Band and hardware.** All four teams use **2.4 GHz** (9-Oct). Each box has one **Ebyte E01-ML01SP4**
>   (nRF24L01+ with PA/LNA) and one **flex omni** at 250 kbps (13-Oct). See [`radio/DECISIONS.md`](radio/DECISIONS.md).
> - **MRM at 20 dBm (D-R6).** A professor approved 20 dBm e.i.r.p., confirmed on Atenea. MRM therefore runs as a
>   hopping radio with listen-before-talk (CNAF UN-85 a), EN 300 328 adaptive FHSS) on 37 channels in 30 ms hops,
>   gaining +10.5 dB on every link.
> - **10 mW modes.** SRI, Quick Mode and the fallback use one fixed channel at 10 mW. NM is also at 10 mW, on
>   RF_CH 77, under the inter-team spec [`radio/NM_SPEC.md`](radio/NM_SPEC.md).
> - **Margins.** On datasheet numbers, MRM 260 m has +13.9 dB and NM +9.9 dB. In the conservative planning case
>   (receiver 3 dB worse, worst antenna direction, −6 dB fade) they fall to +0.9 and −3.1 dB, so the field tests
>   decide.
> - **Controller (18-Oct).** The team wants a Raspberry Pi 3 (WiFi/BT chip disabled or desoldered, Atenea Q22). The
>   radio does not change; power and the Linux software port do ([Pi 3 switch page](briefs/)).
> - **Still to prove on hardware.** Hop sync between boxes and the Linux port exist only in the simulator and
>   in host tests.
> - **Ownership.** The hardware and protocol pages are **suggestions** to the electronics and protocols teams,
>   who own those decisions.

## Read first

| Document | For |
|---|---|
| [`radio/NM_SPEC.md`](radio/NM_SPEC.md) · [`briefs/MTP NM Interop Spec v1.0.pdf`](briefs/) | **Network Mode interop spec for all teams** (draft v1.0): nRF24 registers, frame, gossip rules, CRC, test vector, interop test |
| [`briefs/TeamC Radio Brief v0.11.pdf`](briefs/) | 2.4 GHz band, module (E01-ML01SP4), one omni, 20 dBm hopping (D-R6, all teams hop), link budget incl. the conservative planning case, test plan |
| [`briefs/TeamC Pi 3 Switch v0.1.pdf`](briefs/) | What moving from the Pico 2 to a Raspberry Pi 3 changes: power, software, timing, reboot cost, BoM |
| [`briefs/TeamC Hardware Proposal v0.5.pdf`](briefs/) | Suggested board for electronics: Raspberry Pi 3 + E01-ML01SP4 HAT + flex omni, BoM, power, role switch |
| [`briefs/TeamC Protocol Proposal v0.4.1.pdf`](briefs/) | Suggested protocol for protocols & software, **where each protocol spec lives**, simulator results |
| [`CLAUDE.md`](CLAUDE.md) | Team, calendar, status, next steps and session log (kept up to date each session) |

## Specs: where each interface is defined

| Spec | File | Audience |
|---|---|---|
| NM interop (radio + frame + gossip) | [`radio/NM_SPEC.md`](radio/NM_SPEC.md) | all teams |
| SRI/MRM link frames, ARQ, resume, POLL | [`proto/src/frames.h`](proto/src/frames.h), [`proto/src/link.h`](proto/src/link.h) | Team C |
| Radio register profiles | [`radio/phy_config.py`](radio/phy_config.py) → [`radio/fw/nrf24_config.h`](radio/fw/nrf24_config.h) | Team C |
| Radio driver API + HAL | [`radio/fw/nrf24.h`](radio/fw/nrf24.h) | Team C |
| Compression (one deflate stream, 4 KB buffers) | [`proto/src/codec.h`](proto/src/codec.h) | Team C |
| USB stick I/O (FAT/exFAT, MBR/GPT) | [`proto/src/usb_msc.h`](proto/src/usb_msc.h) | Team C |
| NM relay log | [`proto/src/nm_log.h`](proto/src/nm_log.h) | Team C (others may copy) |

## Layout

| Path | What |
|---|---|
| `radio/linkbudget.py` | Course-corrected AN5142 link budget, throughput model, near-far and planning case (`python3 radio/linkbudget.py`) |
| `radio/MTP-F26_TeamC_Radio_LinkBudget.xlsx` | The same model as a workbook with live formulas (built by `build_workbook.py`; formulas match Python to 0 dB) |
| `radio/AN5142_course_layout_869MHz.xlsx` | The **course** AN5142 sheet rebuilt in its own layout (course 2.4 GHz example + our old 869 MHz baseline; built by `build_course_sheet.py`) |
| `radio/phy_config.py` | nRF24 radio profiles, CNAF UN-85 and datasheet checks, e.i.r.p. per antenna, EN 300 328 checks for the hopping profile (D-R6) and option B; generates `radio/fw/nrf24_config.h` |
| `radio/fw/` | Portable C99 nRF24L01+ driver (power cap per profile, LBT/CCA, hop order, COT/idle), CRC-16, mock radio and host tests |
| `radio/*.md` | Decisions, electronics handoff, NM interop spec, test plan, Atenea questions |
| `radio/*.html` | Sources of the four published pages (PDF exports in `briefs/`) |
| `proto/` | Protocol code (link with resume, NM gossip + relay log, compression, USB stick I/O over FatFs) and the PC simulator. See [`proto/README.md`](proto/README.md) |
| `hw/` | Carrier PCB (KiCad), starting with [`hw/KICAD_SESSION_PROMPT.md`](hw/KICAD_SESSION_PROMPT.md) |
| `docs/` | Course material, **not included**. See [`docs/README.md`](docs/README.md) |

## Quick start

Needs `gcc`, `make`, `zlib` (`sudo apt install build-essential zlib1g-dev`) and Python 3.

```sh
make -C radio/fw test        # radio driver: 244 checks
make -C proto test           # protocol simulator (21 scenarios) + usb_msc tests (116 checks), ~2 s
make -C proto e2e            # the Pi 3 program teamc-node, node against node over an emulated radio (~3 min)
python3 radio/phy_config.py  # radio profiles: channel, band edge, e.i.r.p. and EN 300 328 checks
python3 radio/linkbudget.py  # link budget, throughput, near-far, planning case
cd proto                                               # the simulator reads build/sample.txt from here
./build/sim sri --loss 0.1 --blackout 20:30            # try your own scenario
./build/sim sri --fhss 0.1 --loss 0.05 --ack-loss 0.3  # MRM: hopping, 10 % of hops busy, lost ACKs (~58 s)
./build/sim nm --nodes 10                              # Network Mode gossip (~12 s to the far end)
```

Rebuilding the workbook needs `openpyxl` (`pip install openpyxl`); `make -C proto usb-xcheck PYTHON=<python with
pyfatfs and "setuptools<81">` cross-checks the USB code against a second FAT implementation.
