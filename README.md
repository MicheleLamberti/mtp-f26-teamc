# MTP F26 · Team C workspace

Team C's working repository for the **MTP F26** course project at UPC (Network Upgrade III +
Sustainability competition). It contains radio analysis and firmware, the Raspberry Pi 3
node, protocol simulator, KiCad hardware designs and LaTeX reports.

> **Status (20-Oct-26):**
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
> - **Controller (18-Oct).** The software targets a Raspberry Pi 3 (WiFi/BT chip disabled or desoldered, Atenea Q22). The
>   radio does not change; power and the Linux software port do ([Pi 3 switch page](briefs/)).
> - **File/Unicode layer (20-Oct).** Integrated into `teamc-node`: verified SD caches, checked sender reads,
>   complete-stream validation and separate UTF-8 text views. Original file bytes, BOMs and line endings are preserved.
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
| [Hardware Proposal v0.6](briefs/TeamC%20Hardware%20Proposal%20v0.6.pdf) | KiCad carrier status, renders, BoM, fabrication rules and requests to electronics |
| [`briefs/TeamC Protocol Proposal v0.4.1.pdf`](briefs/) | Suggested protocol for protocols & software, **where each protocol spec lives**, simulator results |
| [File/Unicode guide](proto/test_encoding_text/guide/main.pdf) · [LaTeX](proto/test_encoding_text/guide/main.tex) | Build commands, C/Python/C++ APIs, node integration, BOM policies and validation |
| [Task 11 report](docs/task_11_unicode/report/main.pdf) · [LaTeX](docs/task_11_unicode/report/main.tex) | Unicode file transfer, BOMs, binary file handling and chunk boundaries |
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
| File verification and Unicode decoding (C ABI) | [`proto/test_encoding_text/encoding_stream_c.h`](proto/test_encoding_text/encoding_stream_c.h) | Team C |
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
| `proto/test_encoding_text/` | Python/C++ file layer and tests; C bridge used by the Linux node for verified caches and optional text decoding |
| `hw/` | KiCad: SP4 breakout (ready for the lab) and the Pi 3 A+ HAT carrier (rev A, routed, DRC clean, gerbers in `hw/teamc-carrier/fab/`); read [`hw/DESIGN_NOTES.md`](hw/DESIGN_NOTES.md) |
| `docs/task_11_unicode/` | Team-authored Task 11 report, LaTeX sources, research tools and reproducible validation |
| `docs/course_material/`, `docs/encoding_references/` | Local course originals and downloaded references; excluded from Git. See [`docs/README.md`](docs/README.md) |

## File transfer and text reading

`teamc-node` saves the original recovered bytes to the USB stick. Encoding reports and optional UTF-8
copies stay in its SD-card data directory. Strict automatic decoding is the default; an absent or
overlapping BOM can leave the encoding unresolved. Use `--text-encoding` to declare an agreed format,
or `--text-encoding none` to disable text processing. Partial reception at STOP still saves the received
prefix. See the [node README](proto/port/linux/README.md) for options and cache filenames.

## Quick start

On Linux/Raspberry Pi OS: `sudo apt install build-essential zlib1g-dev python3`.
The Linux node links C and C++17; `build-essential` supplies the compilers and libstdc++.

```sh
make -C radio/fw test        # radio driver and host checks
make -C proto test           # protocol simulator, USB checks and Linux node build
make -C proto/test_encoding_text test  # Python/C++ file and Unicode tests
make -C proto encoding-e2e   # C bridge and whole-node file/Unicode integration
make -C proto e2e            # the Pi 3 program teamc-node, node against node over an emulated radio (~3 min)
python3 radio/phy_config.py  # radio profiles: channel, band edge, e.i.r.p. and EN 300 328 checks
python3 radio/linkbudget.py  # link budget, throughput, near-far, planning case
cd proto                                               # the simulator reads build/sample.txt from here
./build/sim sri --loss 0.1 --blackout 20:30            # try your own scenario
./build/sim sri --fhss 0.1 --loss 0.05 --ack-loss 0.3  # MRM: hopping, 10 % of hops busy, lost ACKs (~58 s)
./build/sim nm --nodes 10                              # Network Mode gossip (~12 s to the far end)
```

[GitHub Actions](https://github.com/SantiBarrios2002/mtp-f26-teamc/actions/workflows/encoding-tests.yml)
runs the radio/protocol suites, file/Unicode tests, node integration/reboot tests and
ARM32/AArch64 compile checks for the file module and C bridge.
Physical Pi, radio and USB tests remain pending.

**The team's Pis** (C1, C2): hostnames, users, SSH, shutting down, another WiFi and a Pi with no network are in
[`PI_ACCESS.md`](PI_ACCESS.md). Passwords: ask Santiago.

Rebuilding the workbook needs `openpyxl` (`pip install openpyxl`); `make -C proto usb-xcheck PYTHON=<python with
pyfatfs and "setuptools<81">` cross-checks the USB code against a second FAT implementation.
