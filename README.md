# MTP F26 · Team C workspace

Santiago's working repository for the **MTP F26** course project at UPC (Network Upgrade III +
Sustainability competition), shared with Team C. It holds the radio team's analysis and
firmware, plus the starting protocol code and simulator handed to protocols & software.

> **Status:** on 9-Oct-26 all four teams moved to **2.4 GHz**. On 13-Oct-26 the radio team decided
> the module and antenna: one **Ebyte E01-ML01SP4** (nRF24L01+) and one **flex omni** per box, 250 kbps. See [`radio/DECISIONS.md`](radio/DECISIONS.md). Hardware and protocol
> pages are **suggestions** to the electronics and protocols teams, who own those decisions.
> Since 16-Oct-26 (**D-R6**, a professor approved 20 dBm e.i.r.p.) SRI and MRM run the same hardware as a
> hopping radio with listen-before-talk (CNAF UN-85 a), EN 300 328 adaptive FHSS) at up to **20 dBm e.i.r.p.**,
> +10.5 dB on every link. NM stays at 10 mW on one channel; the 10 mW profile also serves Quick Mode.

## Read first

| Document | For |
|---|---|
| [`briefs/TeamC Radio Brief v0.7.1.pdf`](briefs/) | 2.4 GHz band, module (E01-ML01SP4), one omni, MRM channel plan, 20 dBm hopping baseline (D-R6), link budget, test plan |
| [`briefs/TeamC Hardware Proposal v0.4.3.pdf`](briefs/) | Suggested board for electronics: Pico 2 + E01-ML01SP4 + flex omni, BoM, power |
| [`briefs/TeamC Protocol Proposal v0.3.4.pdf`](briefs/) | Suggested protocol for protocols & software, with simulator results |
| [`CLAUDE.md`](CLAUDE.md) | Team, calendar, status and session log (kept up to date each session) |

## Layout

| Path | What |
|---|---|
| `radio/linkbudget.py` | Course-corrected AN5142 link budget and throughput model (`python3 radio/linkbudget.py`) |
| `radio/MTP-F26_TeamC_Radio_LinkBudget.xlsx` | The same model as a workbook with live formulas (built by `build_workbook.py`) |
| `radio/AN5142_course_layout_869MHz.xlsx` | The **course** AN5142 sheet rebuilt in its own layout (course 2.4 GHz example + our old 869 MHz baseline; built by `build_course_sheet.py`) |
| `radio/phy_config.py` | nRF24 radio profiles, CNAF UN-85 and datasheet checks, e.i.r.p. per antenna, EN 300 328 checks for the SRI/MRM hopping profile (D-R6); generates `radio/fw/nrf24_config.h` |
| `radio/fw/` | Portable C99 nRF24L01+ driver (power cap per profile, LBT/CCA for the FHSS profile), CRC-16, mock radio and host tests |
| `radio/*.md` | Decisions, electronics handoff, shared NM radio settings, test plan, Atenea questions |
| `radio/*.html` | Sources of the three published pages (PDF exports in `briefs/`) |
| `proto/` | Protocol code (link with resume, NM gossip, compression) and the PC simulator. See [`proto/README.md`](proto/README.md) |
| `hw/` | Carrier PCB (KiCad), starting with [`hw/KICAD_SESSION_PROMPT.md`](hw/KICAD_SESSION_PROMPT.md) |
| `docs/` | Course material, **not included**. See [`docs/README.md`](docs/README.md) |

## Quick start

Needs `gcc`, `make`, `zlib` (`sudo apt install build-essential zlib1g-dev`) and Python 3.

```sh
make -C radio/fw test        # radio driver: 194 checks
make -C proto test           # protocol simulator: 13 scenarios in ~1 s
python3 radio/phy_config.py  # radio profiles: channel, band edge, e.i.r.p. checks
python3 radio/linkbudget.py  # link budget table
./proto/build/sim sri --loss 0.1 --blackout 20:30   # try your own scenario
./proto/build/sim sri --fhss 0.2 --loss 0.05         # SRI/MRM baseline (D-R6): hopping, 20 % of hops busy
```

Rebuilding the workbook needs `openpyxl` (`pip install openpyxl`).
