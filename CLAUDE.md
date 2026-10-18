# MTP-F26 — Team C (UPC)

Santiago's workspace for the MTP F26 course project (Network Upgrade III+ Sustainability
competition). Santiago is on the **Radio Team**. This file is the shared memory between
sessions: read it first, and update the **Team**, **Status** and **Session log** sections
at the end of every session.

## Team C

| Sub-team | Members | Scope |
|---|---|---|
| RT — Radio | Santiago, Andrian, Marcos | Spectrum analysis + band choice, spectrum-sharing talks with other teams, antennas (QM → NM omni → MRM), MRM link budget, MRM multiple-access strategy |
| ET — Electronics | Carlos, Michele, Bikash, Guillem | Hardware; picks the micro and adapts to the radio module RT chooses |
| PT — Protocols/SW | Ibrahim, Guillem, Sofia | Protocol + software |
| PM / leader | Marcos | |

- ~9–10 people. Members move between RT and PT.
- Decision split: **RT picks the transceiver module and antennas; ET adapts and picks the micro.**
- Source of truth: `Project_Definition_Team_C.docx` (Ed. 00, 3-Oct-26) in the team Drive
  folder "MTP" (id `1fDriz2utaKJeJH9nbBDpE4Sf5K1nGDj2`). Writing there is visible to the
  whole team — ask Santiago before creating/changing files in it.

## Calendar

Classes and tutor meetings are on **Fridays**. Week 2 = Fri 2-Oct-26.

| Date | Milestone |
|---|---|
| Fri 16-Oct-26 | Band (9-Oct) and module + antenna (13-Oct) decided; order radios + antennas (10–12 day delivery) |
| Fri 23-Oct-26 | Inter-team meeting: agree `NM_SPEC.md`, every team's chip, MRM etiquette (hop + LBT, ≥ 10 m) |
| Fri 6-Nov-26 | Quick Mode attempt (week 7); NM interop test with the other teams |
| Fri 20-Nov-26 | NM rehearsal on the rims; go/no-go for MRM hopping |
| Fri 4-Dec-26 | Pretest |
| Fri 11-Dec-26 | Competition / project deadline (week 12) |
| Fri 18-Dec-26 | Presentations |

## Layout

- `docs/` — course material: competition rules PDF, Session #1 and PM slides, AN5142
  (annotated PDF + course-corrected `.xls`), CNAF poster, Project Definition example, `.mpp`
  example plan.
- `radio/linkbudget.py` — course-corrected AN5142 model (no 1/2 factor in flat-earth,
  |cos| worst-case ground bounce). `SCENARIOS` and `FRAMING` live here. Run
  `python3 radio/linkbudget.py`.
- `radio/build_workbook.py` — generates `radio/MTP-F26_TeamC_Radio_LinkBudget.xlsx` with
  live formulas (the hand-in artefact). Keep it in sync with `linkbudget.py`.
- `radio/build_course_sheet.py` → `radio/AN5142_course_layout_869MHz.xlsx`: the course AN5142 sheet
  rebuilt row for row (Ground Multipath inlined), course example as a check + SRI/MRM/NM baseline sheets.
- `radio/phy_config.py` — nRF24L01+/E01-ML01SP4 profiles (`TEAM_250K`, `TEAM_1M`, `NM_COMMON`, `TEAM_20DBM_FIXED` = option B, and `TEAM_FHSS`
  = the SRI/MRM baseline since 16-Oct, D-R6), UN-85 b checks (channel, band edge, e.i.r.p. with the omni at 3 dBi peak, RF_PWR ≤ −18 dBm,
  MRM plan spacing) and EN 300 328 adaptive-FHSS checks for `TEAM_FHSS` (37-channel hop set without the BLE advertising channels, COT/idle/CCA,
  RPD threshold vs the LBT level, [T0] e.i.r.p. with +1.5 dB uncertainty); regenerates `radio/fw/nrf24_config.h` (incl. `NRF24_RF_PWR_MAX_BITS`, `…_FHSS`, the
  hop order). `E01_PA_GAIN_DB` and `SP4_LNA_GAIN_DB` are estimates until T0/T17.
- `radio/fw/` — portable C99 nRF24L01+ driver behind a HAL (DPL + NOACK frames, RF_CH ≤ 83, RPD),
  CRC-16, power cap per profile (−18 dBm; only an `lbt` profile may use `NRF24_RF_PWR_MAX_BITS_FHSS`), LBT for
  the hopping profile (`nrf24_cca`, hop-set-only channels, 50 ms COT, idle gap), mock nRF24 with a simulated
  channel, host tests: `make -C radio/fw test` (244 checks). Profiles carry `hop`, `cot_us`, `idle_us`.
  The RFM69 driver and duty-cycle guard were removed 9-Oct (in git history).
- `radio/DECISIONS.md` (D-R1b/D-R2c/D-R3/D-R5c/D-R6/D-R6b current; D-R6 = 20 dBm hopping for MRM, D-R6b = option B;
  D-R4 fixed plan = 10 mW fallback only; D-R2b/D-R5b and the 868 records superseded),
  `HANDOFF_ET.md` (SP4 interface for electronics), **`NM_SPEC.md` (NM interop spec v1.0 for all teams: registers, frame,
  gossip, CRC, test vector; `NM_PHY_PROPOSAL.md` is now a pointer)**, `TEST_PLAN.md`
  (T0 gate at all RF_PWR steps, T2, T4, T5, T13–T18; T17/T18 = CCA threshold and hopping, gates for TEAM_FHSS outdoors; PER-based, nRF24
  has no RSSI), `ATENEA_QUESTIONS.md` (for Marcos; Q3 answered yes 16-Oct: 20 dBm confirmed).
- Radio brief (artifact, private — Santiago shares it with the team):
  https://claude.ai/artifact/MqP1rz4NzHmGTgJCYMYGqw — source `radio/brief.html`; edit it and
  republish to the same URL (v0.10 published 17-Oct: review fixes, conservative planning case, 37 hops / 30 ms, NM ch 77 + link to
  the NM spec, Q12–Q21; v0.9: options A/B, NM diagram).
- Hardware proposal for electronics (artifact, private): https://claude.ai/artifact/81s3ZPuHznAvgXU9zWjaWb
  — source `radio/hw_proposal.html` (v0.4.4 17-Oct: TX/RX role switch (Atenea Q8), U.FL secured for the drop test, Mac/Windows
  sticks; v0.4.3: Pico 2 + one E01-ML01SP4 + flex omni, radio LDO, breakout, BoM, low-battery countermeasures).
- `hw/` — carrier PCB work. `hw/KICAD_SESSION_PROMPT.md` is the brief for the KiCad MCP design session
  (constraints, parts, pin map, power, mechanics, checkpoints, deliverables).
- `proto/` — PT protocol code (`src/`: link ARQ+resume, NM Trickle gossip + relay log `nm_log.c`, codec, USB stick
  I/O `usb_msc.c` over FatFs R0.15a in `third_party/fatfs/`) and the PC simulator (`sim/`, `--fhss BUSY` = the SRI/MRM
  hopping radio layer): `make -C proto test` (21 scenarios incl. T18 = NM spec test vector and T19 = Pi 3 reboot, + 109 usb_msc checks, ~2 s; `--reboot-down S` sets the
  downtime per reboot, 0.3 s Pico / 10–30 s Linux); `make usb-xcheck PYTHON=<venv
  python with pyfatfs + setuptools<81>` cross-checks FAT16/32 images. `port/pico/usb_msc_pico.c` = TinyUSB + PIO-USB
  skeleton, NOT compiled here (no pico-sdk / ARM gcc on this machine).
  See `proto/README.md`.
- Protocol/firmware proposal for PT (artifact, private): https://claude.ai/artifact/6g1P41SGs1eGf9Jme8YsAK
  — source `radio/pt_proposal.html` (v0.3.7 17-Oct: **Protocol specs section** = where each interface is defined, POLL,
  streaming codec, 107 kbps, sim results; v0.3.6: NM diagrams, relay log, usb_msc, option B).
- **NM Interop Spec** (artifact, private — Santiago shares it with the other teams): https://claude.ai/artifact/CeoNGSUz67ifecwzzkmgLS
  — source `radio/nm_spec.html`, built from `radio/NM_SPEC.md` (keep both in sync; v1.0 draft 16/17-Oct).
- **Pi 3 switch page** (artifact, private — for the whole team): https://claude.ai/artifact/Q5EZxmB1HhcbiQhs2menMw
  — source `radio/pi3_impact.html` (v0.1 18-Oct: what a Raspberry Pi 3 instead of the Pico 2 changes; styles copied from
  `hw_proposal.html`). Assumes the WiFi/BT chip is disabled or desoldered (Atenea Q22).
- PDF/HTML exports of the pages: `briefs/` (PDF) and the Windows folder (HTML + PDF + workbooks), light theme, headless
  Chromium from `~/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome`, mermaid@11.4.1 from jsDelivr; the export
  script lived in the job scratch dir (wraps each page in a doctype with `data-theme="light"`) — recreate if needed. No poppler here: check PDFs with pypdf text.

## Working rules

- Conventions in the model: gains in dBi, losses as **negative** dB, powers in dBm.
- LibreOffice is not installed. `openpyxl` is not installed system-wide, so build the workbook from a
  scratch venv (`python3 -m venv <scratch>/venv && <scratch>/venv/bin/pip install openpyxl
  formulas`), then recalculate it with `formulas` and compare against `linkbudget.py`. Scratch
  venvs under /tmp disappear, so recreate it when needed.
- After changing scenarios: also extend `RX_BW_KHZ` / `NF_DB` in `build_workbook.py` (one
  entry per scenario) and add any new carrier frequency to its `REG` table.
- Before ending a session: `make -C radio/fw test` and `make -C proto test` must pass, and
  `python3 radio/phy_config.py` must report all checks OK.
- The Sept-18 `mtp-f26.zip` "advisory kit" in Downloads is **not** team work (assumes
  "Team X", wrong dates, pre-picked RFM69/nRF24/Black Pill). Use its analysis as input only;
  never present its choices as team decisions.
- Treat anything not in the Project Definition or confirmed by Santiago as a proposal.
- Git repo: https://github.com/SantiBarrios2002/mtp-f26-teamc (public, created 9-Oct-26). Early commits
  may go straight to main (Santiago, 9-Oct); never force-push. **Keep one branch, `main`** (Santiago, 16-Oct): a
  session that works in a worktree branch fast-forwards `main` to it at the end and deletes the branch. `docs/` is
  git-ignored (copyrighted course material). Put PDF exports of the pages in `briefs/` too.

## Status (keep current)

**9-Oct-26: BAND SWITCH to 2.4 GHz.** All four teams (us + 3 others) chose 2.4 GHz for every mode;
868 MHz is dropped (kept in `radio/DECISIONS.md` as superseded history). Everything below is the 2.4 GHz baseline.

**16-Oct-26: 20 dBm e.i.r.p. is the SRI/MRM BASELINE (D-R6).** A professor said yes to 20 dBm (Santiago).
Under CNAF UN-85 a) a narrowband radio gets it only while hopping with the EN 300 328 sharing rules, so SRI/MRM run
as adaptive FHSS + LBT; NM stays at 10 mW on one channel (UN-85 b). **Confirmed: Atenea Q3 answered yes.**

**Radio — key results (17-Oct, `python3 radio/linkbudget.py`, workbook S21–S28, formulas = Python to 0 dB):**
- SRI/MRM: hopping at ≤ 20 dBm e.i.r.p. (S24–S26): **SRI 70 m +36.5 · MRM 260 m +13.9 dB** (+6.9 at 0.5 m; +8.4 at
  today's RF_PWR −12 until T0 shows the PA gain ≤ 21.5 dB and allows −6). **NM 100 m hop (−10 dB) +9.9 dB** at 10 mW.
- **Conservative planning case (17-Oct review: sens +3 dB, 0 dBi worst azimuth, −6 dB fade/body): MRM 20 dBm +0.9 dB
  (−4.6 at −12), NM −3.1 dB, SRI +23.5.** Antenna height, people away from the boxes and T4/T5 attenuation-to-failure
  decide. Repeat this caveat whenever margins come up.
- 10 mW fixed-channel fallback (S21–S22, also Quick Mode): SRI +26.0, MRM +3.4. If T0 measures only ~+2 dBm at
  −18, the 10 mW margins drop ~5 dB (hopping picks the highest legal step anyway).
- Non-adaptive FHSS would be capped at MU 10 % (10 % duty at 20 dBm, ~16 kbps): too slow → adaptive with LBT.
- Goodput (model counts the 4 B header and a 0.3 ms frame gap since 17-Oct): 107 kbps fixed, 96 kbps hopping with 10 %
  busy (> 67 needed raw, 22 at 3×). Sim: T2 27 s, T12 37.7 s, T13 68.6 s, T14 58.3 s, T14b 114.7 s (all pass).
- **SRI runs on `TEAM_250K`** (10 mW fixed, +26 dB, 107 kbps, no hop-sync dependency; 16-Oct review). 20 dBm is for MRM.
- **Every team uses 20 dBm (Santiago, 16-Oct) → every team hops; no fixed MRM plan.** Near-far at 10 m: 41.4 dB (+6 two-ray
  peak); hops ≤ 4 MHz apart collide (13 % of pairs at 10–20 m) → ~31 % lost ACKs at the sender (pessimistic) + ~7 % co-channel
  floor at any spacing → POLL frame. Sim T14 (5 % data / 30 % ACK loss): 58 s. **≥ 10 m between teams' boxes, 30 m between
  senders**; per-team hop order (ours stride 7).
- NM round is **5 min** (SRI/MRM 2 min); NM file is 0.5 kB. No duty-cycle limit anywhere in 2.4 GHz.
- Power: radio 3.3 V LDO straight from the 3.0–4.2 V cell is fine (dropout ≤ 0.1 V at 150 mA; below ~3.4 V it passes
  the cell through, ≥ 2.95 V at cutoff). Countermeasures in `HANDOFF_ET.md`: ideal diode → ADC3 battery sense,
  firmware thresholds (3.5 / 3.4 / 3.2 V), T0 at 3.6/3.3/3.0 V, buck-boost fallback. Not after the 5 V boost.

**Baseline (2.4 GHz):**
- D-R1b 2400–2483.5 MHz, **250 kbps GFSK in every mode**.
- D-R2c **Ebyte E01-ML01SP4** (genuine nRF24L01P + PA/LNA, SMD 14.85 × 18 mm, 1.27 mm pads, IPEX), one per box
  (decided 13-Oct, Santiago with Marcos). RF_PWR −18 (+2..+7 dBm est.) for 10 mW; −12/−6 while hopping. Needs a
  breakout from the first bench test (QM module = final). Not the DP5, not the 2G4M27D (can't do 10 mW), never E01C-*.
- D-R5c **one Molex 146153-0100 flex omni** (34.9 × 9 mm, 2.4–3.0 dBi, U.FL) in the SP4, vertical, high on a wall.
  Same antenna for SRI/MRM/NM and QM.
- **D-R6 MRM: `TEAM_FHSS`** — 37 hops, even RF_CH 4–78 without 26 (BLE advertising 2/26/80 left out), stride 7, 30 ms
  slots, RPD as the CCA (170 µs), COT 50 ms + 2.5 ms idle, power cap per profile in the driver. **NM: `NM_COMMON`**
  (RF_CH 77 = 0x4D, 10 mW; `NM_SPEC.md`). **QM/bench/fallback: `TEAM_250K`** (RF_CH 74, 10 mW).
- D-R4: superseded for MRM (all teams hop at 20 dBm); fixed plan RF_CH 24/49/74/82 = 10 mW fallback (and option B).
- Software: Pico 2 (suggested to ET), C on the Pico SDK; protocol in `proto/` (SR-ARQ + resume + POLL, one deflate
  stream, Trickle NM gossip, usb_msc over FatFs); where each interface is defined: pt page "Protocol specs".

**20 dBm, two versions (rechecked 16-Oct, D-R6/D-R6b):** A = hopping (`TEAM_FHSS`, default, EN 300 328 compliant).
B = one fixed channel at 20 dBm with frame-based LBT (`TEAM_20DBM_FIXED`, COT 10 ms): same margins, no hop sync, but
EN 300 328 cl. 4.3.2.3 / the EU SRD decision cap non-hopping radios at 10 dBm/MHz → our 0.6 MHz signal is 5–10 dB
over; use B only on an explicit yes (Atenea Q11). CNAF in force: Orden TDF/732/2026 (BOE-A-2026-15661); its
consolidated text omits the UN notes, so the EU decision 2006/771/EC (as amended to 2022/180) is the reference.

**18-Oct-26: controller → Raspberry Pi 3 (team request; proposal page v0.1).** Working assumption (Santiago): the Pi 3 is
allowed with its WiFi/BT chip disabled in software or desoldered; the rule (p.6) bans "any chip implementing" WiFi/BT,
so Atenea Q22 asks. Radio unchanged (SP4, omni, margins, NM spec). Changes: always-on 5.1 V boost ≥ 2.5 A from the cell
(Pi ~1.7–2.2 W with the A+, 4–5 h on 3000 mAh), MAX17048 fuel gauge (no ADC on the Pi), radio LDO from the cell as before,
HAT-style carrier; Linux HAL (spidev buffer transfers, libgpiod, busy-wait delays, timerfd), PREEMPT_RT or wider ACK/TX_DS
timers, read-only root + data partition, boot ≤ 10 s target; goodput 107 → ~97 kbps if the frame gap grows to 0.5 ms;
sim T19: MRM with a 30 s reboot still 90.8 s. PIO-USB + stick boost obsolete. Cost ~70–90 €/box (was 40–55).

**Open decisions:**
- [ ] D-R3 NM common PHY + protocol: agree `NM_SPEC.md` v1.0 with the teams by 23-Oct; every team's chip in writing;
      interop test by 6-Nov (NM win gates the cost category)
- [ ] D-R6 go/no-go for MRM hopping on Fri 20-Nov (T17, T18, 260 m transfer); else TEAM_250K, or option B on a Q11 yes
- [ ] ET: micro choice — **18-Oct: the team wants a Raspberry Pi 3** (A+ suggested; WiFi/BT chip disabled or desoldered,
      Atenea Q22 before QM 6-Nov) — and the pin map (Pi proposal on the Pi 3 page)

**Next up (17-Oct, roughly in order):**
- [ ] **Order now** (one batch, QM modules are final): 6 × E01-ML01SP4, 4 × Molex 146153-0100 (MHF, not MHF4),
      2 × U.FL-to-SMA pigtails. ~~3–4 × Pico 2~~ (18-Oct: Pi 3 instead; count the boards we have). Verify EU seller + lead time. Not needed: DP5, SMA pads, whips, RFM69.
- [ ] Name owners: SP4 breakout, carrier PCB, Pico toolchain + USB host + hop sync, NM inter-team talks (PT),
      sustainability report, BoM + invoices, mechanics/drop test (secure the U.FL plug)
- [ ] Santiago: share the NM Interop Spec page (artifact Share menu) with the other teams; brief v0.10 / hw v0.4.4 /
      pt v0.3.7 with Team C (pt → Ibrahim, Guillem, Sofia)
- [ ] By 20-Oct: Marcos posts `ATENEA_QUESTIONS.md` Q1, Q4–Q9, Q11–Q22 (Q22 = Pi 3 wireless chip; Q2, Q10 not needed; Q3 answered yes —
      archive the written answer)
- [ ] By 23-Oct inter-team meeting: each team's chip; NM spec agreed; everyone hops with LBT at ≤ 20 dBm in its own
      order, ≥ 10 m between boxes (30 m between senders); interop date 6-Nov
- [ ] QM deliverables (PD, plan, action item list, provisional BoM) + Atenea petition before 17:00 the day before;
      check the Project Definition lists QM, SRI, MRM, NM and cost (rules p.3)
- [ ] Andrian: campus 2.4 GHz survey (T14): WiFi load per hop channel and on the NM channel 77
- [ ] ET: SP4 breakout (1.27 → 2.54 mm) for the first bench test; measure the IKEA 365+ inside dimensions
- [ ] Bench, once modules arrive: T0 at all four RF_PWR steps and at 3.6/3.3/3.0 V (pigtail, ≥ 30 dB pad), then T2;
      T13 lab booking with T17 (RPD trip level) + T18 (hop pattern) — gates for TEAM_FHSS outdoors
- [ ] Field: T4/T5 attenuate to failure (planning case MRM +0.9, NM −3.1 dB); antenna as high as the box allows
- [ ] Pico software: `nrf24_hal_t` once ET confirms the pin map; hop clock + acquisition (only in the simulator so
      far); compile/bench `proto/port/pico/usb_msc_pico.c` (3–4 sticks, FAT32 + exFAT, 120 MHz clock)
- [ ] Simulator: MRM scenario with the 4 teams' boxes modelled explicitly (today a loss rate, T14)
- [ ] **ON HOLD (9-Oct):** CST MCP (patches dropped 13-Oct; still useful to model the omni in the box). Santiago is
      asking the radio teacher which CST version the team may install on laptops. Then: review the code of
      `teslawei/mcp-cst-studio` (live on Windows, or offline VBA from WSL) or `woson-L` CST-MCP (CST 2026 Python API)
      before installing; `mcp-openems` as a free cross-check. Nothing installed yet.

## Session log

Newest first. One entry per session: what was done, what was decided (and by whom),
what's pending.

### 2026-10-18 — Pi 3 instead of the Pico 2: impact analysis + team page
- Santiago: the team wants a Raspberry Pi 3 in the build; asked for an analysis with subagents (code inventory + web
  research). Finding: every Pi 3 (B/B+/A+) has a WiFi/BT chip, which the rules (p.6) ban "even unused"; CM3+ has none.
  Santiago then: assume we can disable or desolder the chip and use the Pi 3; make a page to share with the team.
- Page "Team C Pi 3 Switch" v0.1 (`radio/pi3_impact.html`, artifact Q5EZxmB1HhcbiQhs2menMw; PDF in `briefs/` + Windows
  folder): at-a-glance table, variant pick (A+), power tree (boost, fuel gauge, runtime), Pi pin map, software port,
  Linux timing, goodput (107 → 97 / 91 / 73 kbps), reboot sim results, mechanics, BoM delta, owners. Atenea Q22 drafted.
- Simulator: `--reboot-down S` and test T19 (MRM as T14, receiver down 30 s → 90.8 s; 10 s → 78 s; Pico 60.5 s).
- Not yet updated for the Pi: hw_proposal, pt_proposal, brief, HANDOFF_ET, KiCad brief (still say Pico 2) — wait for ET's
  variant pick and the Q22 answer.
- Checks: fw 244, proto 21 scenarios + 109 usb, phy_config all OK.
- **Start next session with:** Q22 answer? which Pi 3 variant and how many boards? then port the HAL to Linux.

### 2026-10-17 — Opus review fixes; NM interop spec; protocol specs section
- Santiago asked for Opus reviewers on the whole project, then to fix their findings (commit a4bbad7 + this one):
  link (duplicated tail after a late HELLO, done without END, ACK sent mid-burst, POLL frame for lost ACKs), driver (COT
  overflow, SETUP_AW before the addresses, CW/PLL_LOCK bits masked, channel change via standby), codec (streaming, 4 KB
  buffers instead of whole-file RAM), NM (64 chunks, stale `have`, whole-file CRC before "complete"), radio model
  (header counted as payload + frame gap → 107 kbps not 159; 30 ms slots; BLE advertising channels out → 37 hops;
  two-ray near-far; conservative planning case MRM +0.9 / NM −3.1 dB), sim hop clocks with drift (T14 realistic 58 s,
  T14b stress, T15–T17). USB: Mac/Windows sticks (GPT, UTF-8 names, write-protect); we bring our own sticks.
- Santiago asked for a protocol-specs section, especially the NM spec to share with the other teams: `radio/NM_SPEC.md`
  v1.0 (RF_CH 77, registers in hex, frame, Trickle rules, CRC-16 check 0x29B1, 3-frame test vector, interop test) and
  its page (NM Interop Spec artifact); sim T18 decodes the test vector. pt v0.3.7 has the "Protocol specs" table
  (NM spec, frames.h/link.h, phy_config → nrf24_config.h, nrf24.h, codec.h, usb_msc.h, nm_log.h). Brief v0.10, hw v0.4.4
  (role switch, U.FL secured). `NM_PHY_PROPOSAL.md` → pointer; TEST_PLAN T16 written out; PDFs re-exported (4 pages).
- Checks: fw 244, proto 20 scenarios + 109 usb, phy_config all OK, workbook = Python (0 dB over 28 scenarios),
  usb-xcheck (bare FAT16/32, MBR, GPT) OK. Santiago then asked to tidy CLAUDE.md/README and leave the repo clean:
  Calendar, Status and Next up deduplicated; README status updated; only `main`, no worktrees.
- **Start next session with:** NM spec shared with the teams? order placed? T0 at all four steps and at 3.0 V.

### 2026-10-16 (night) — relay log, usb_msc started, 20 dBm rechecked (A/B), NM diagrams
- Relay log: `nm_gossip` keeps a trace (first/last heard, broadcasts, per-chunk times); `nm_log.c` formats
  NM_LOG.TXT; the sim writes one per node (`build/nm_logs/`) and checks them (T10).
- usb_msc: portable module over FatFs R0.15a (LFN, exFAT, cp850, fixed 11-Dec-2026 timestamp): largest root .txt
  (skips hidden, "._", our log), 4 KB chunked load to a flash sink, save via `.part` + read-back CRC + rename
  (found by the tests: a failing stick left a truncated final file). 96 host checks (FAT16/32/exFAT, full, fault,
  unplugged) + pyfatfs cross-check. Pico glue skeleton + bench checklist in `proto/port/pico/`.
- 20 dBm recheck (Santiago: "apparently we wouldn't need to hop"): EN 300 328 V2.2.2 non-FHSS = 20 dBm AND
  10 dBm/MHz PSD (cl. 4.3.2.3) + frame-based LBT above 10 dBm; EU SRD decision same density. Kept both: A default,
  B built (profile, driver per-profile COT/idle/hop, 41 new fw checks → 235; S27–S28; workbook 28 scenarios, 0 dB),
  Atenea Q11 drafted. Pages: brief v0.9 (A/B table, NM diagram), pt v0.3.6 (NM sequence + node flowchart, relay
  log, usb_msc), hw v0.4.3 footer. Mermaid: a ";" inside a sequence label breaks it (fixed).

### 2026-10-16 (close) — Atenea Q3 answered yes; every team at 20 dBm
- Santiago: assume every team uses 20 dBm e.i.r.p. → they hop too (narrowband needs FHSS for 20 dBm). Hop set opened
  to all 40 even channels 2–80 (no fixed channels to avoid); near-far back to the equal-power ratios: ≥ 10 m between
  boxes; random hop collisions estimated (12 % of pairs) and simulated (T14, 30 % loss both ways: 81 s). D-R4 fixed
  plan → fallback only. Pages: brief v0.8, pt v0.3.5.
- NM status (answered in chat): NM_COMMON + Trickle gossip, 8 nodes in 8.3 s (17 s harsh); 100 m hop +9.9 dB, ~177 m
  max with −10 dB obstruction; risks = other teams' chips (must speak nRF24 ESB) and rim spacing > ~150 m
  (then a shared 20 dBm hopping NM). D-R3 agreement + interop day are the open items.
- NM proof (rules): a team wins NM by "delivering a copy of the NM-file from at least one of their node devices",
  byte-identical, uploaded to USB in 3 min after STOP; bonus needs one prior individual success (QM/Pretest/SRI).
  Our gossip gives every node a full copy. To do: Atenea Q9 (output name/encoding), write the file to flash as soon
  as it completes, optional relay log on the USB stick (offered to Santiago).
- Santiago: Q3 confirmed, 20 dBm e.i.r.p. for our hopping design is allowed in writing. D-R6 status → confirmed;
  the "written confirmation" items are closed (DECISIONS, ATENEA_QUESTIONS, workbook, brief v0.7.2, CLAUDE.md).
- **Start next session with:** order placed? T0 at all four steps and at 3.0 V; teams told (≥ 15 m)?

### 2026-10-16 (end) — low-battery countermeasures; everything on `main`
- Santiago asked whether a 3.3 V LDO works from a 3.0–4.2 V cell, or should sit after the 5 V boost / use a 5 V
  battery. Answer: LDO from the cell is right (after the boost ~60 % efficient + ripple at the PA; no 5 V cell).
- Santiago: add the countermeasures to the docs anyway and keep one branch (`main`). Added to HANDOFF_ET (Power),
  TEST_PLAN T0 (output at 3.6/3.3/3.0 V), KiCad brief (ideal diode LM66100, LDO dropout spec, low-battery row,
  buck-boost option), pages brief v0.7.1 / hw v0.4.3 / pt v0.3.4 (battery check in ui/store); PDFs re-exported.
- Branch `worktree-fhss-20dbm` fast-forwarded into `main` and deleted on GitHub.
- **Start next session with:** written yes on Atenea? order placed? T0 at all four steps and at 3.0 V; teams told (≥ 15 m)?

### 2026-10-16 (later) — 20 dBm hopping made the SRI/MRM baseline
- Santiago: a professor said yes to 20 dBm e.i.r.p. → make D-R6 the baseline (not a draft). Atenea Q3 now asks for
  the yes in writing (rules: oral comments don't override the written rules); not blocking.
- New finding at 20 dBm next to 10 mW teams: hops 5 MHz away (−38 dB) would drown them → hop guard widened to ±5 MHz
  (27 channels, nearest 6 MHz, −50 dB); still needs **≥ 15 m between our boxes and theirs** at MRM (51.9 dB at 10 m).
- Relabelled S21–S26 (baseline / fallback), near-far printout for 20 dBm, workbook rebuilt (0 dB diff); phy_config
  profiles retitled (TEAM_FHSS = SRI/MRM, TEAM_250K = QM/bench/fallback); fw 194 checks; sim 13/13 (T12 35.9 s,
  T13 53.8 s). DECISIONS, TEST_PLAN v0.5, Q3, handoff, NM note, READMEs. Pages: brief v0.7, hw v0.4.2, pt v0.3.3; PDFs.
- **Start next session with:** written yes on Atenea? order placed? T0 at all four steps; other teams told (≥ 15 m)?

### 2026-10-16 — 20 dBm with frequency hopping (D-R6 draft)
- Santiago: a teacher mentioned we could qualify for 20 dBm e.i.r.p.; asked how, which module, how to know, then
  asked to add the scenarios and update the whole project. Also asked for a HW/SW stack walkthrough and the power
  tree (answered in chat: Pico VSYS via diode, radio LDO, 5 V boost for the stick, MCP73831 USB-C charging).
- Checked primary texts: CNAF UN-85 a)/b) (CNAF 2013 notes, same structure in 2017) and ETSI EN 300 328 V2.2.2
  cl. 4.3.1. Only adaptive FHSS with LBT gives 20 dBm without a duty cap. Rules: oral comments don't override the
  written rules → Atenea Q3 in writing, cc Prof. Umbert.
- Built (proposal, not decided): `linkbudget.py` S24–S26 + FHSS goodput; workbook rebuilt (0 dB diff, FHSS block in
  Throughput); `phy_config.py` TEAM_FHSS + EN 300 328 checks (all OK); driver power cap per profile + `nrf24_cca`,
  hop order, COT/idle (194 checks); sim `--fhss` with T12/T13 (13/13 pass); DECISIONS D-R6, TEST_PLAN v0.4 (T17,
  T18), Q3 rewritten, handoff v0.4, NM note, READMEs. Pages: brief v0.6, hw v0.4.1, pt v0.3.2 republished; PDFs.
- Module answer: keep the SP4 (it is a +20 dBm module); the 2G4M27D would be legal while hopping but not at 10 mW.
- **Start next session with:** Atenea Q3 answer? order placed? T0 at all four steps.

### 2026-10-13 — Antenna + module decided: one omni on the E01-ML01SP4
- Santiago and Marcos reviewed the 2.4 GHz options. Antennas can't change between competition modes.
- Explained why antenna gain matters under the e.i.r.p. cap (RX gain is free; the E01 can't fill the cap
  with a low-gain antenna; patches also reject neighbours sideways). Vistronica VIS1797 (generic
  NRF24L01+PA+LNA, Colombian shop): drop-in but unverified chip and optimistic −104 dBm; not added.
- Fixed-antenna comparison: patches risk NM (aiming, rim corner, tuning); one omni is simplest. The
  E01-2G4M27D (−99 dBm) was rejected by Santiago: ~+9 dBm floor + 3 dBi antenna exceeds 10 dBm.
- **Decided (Santiago, with Marcos): one Molex 146153-0100 flex omni + one Ebyte E01-ML01SP4 per box**
  (D-R2c, D-R5c). SP4 datasheet: −96 dBm @250k, +20 dBm max, 120/26 mA, IPEX on the module.
  Margins: SRI +26.0, MRM +3.4 (+8.3 at 1.0 m), NM +9.9 dB (S21–S23; workbook 0 diff).
- Firmware: power clamp (init refuses, write_reg clamps RF_PWR above −18 dBm), 124 checks. phy_config: SP4 + omni
  at 3 dBi peak ≤ 9.5 dBm e.i.r.p.; BENCH_WHIP dropped. Docs: HANDOFF_ET v0.3, KiCad brief (one SP4, no patches),
  TEST_PLAN v0.3, Atenea Q10 not needed. Pages: brief v0.5, hw v0.4, pt v0.3.1 republished; PDFs re-exported.
- **Start next session with:** order placed? who builds the SP4 breakout? CST answer from the radio teacher.

### 2026-10-09 (evening) — 2.4 GHz port finished
- Santiago asked to finish the "Next up" and how a single omni for RX/TX would look.
- Single omni: −4 dB on every link (E01 can't fill the 10 dBm cap without antenna gain; RX loses the patch gain):
  MRM 260 m +0.4 dB, NM +6.9 dB. Recorded in D-R5b with a patch + omni middle option. Not decided.
- Firmware: nRF24 driver + mock + 138 checks; phy_config rewritten for nRF24 (4 profiles, all checks OK);
  RFM69 driver, SX1231 mock and dc_guard removed. Protocol: 32 B frames (DATA 28, HELLO name 21, NM chunk 25),
  nRF24 airtime, 250 kbps; sim 11/11 pass, no-compression case now delivers all 10 000 lines (73 s).
- Docs: NM PHY v0.2, test plan v0.2 (T0 output-power gate, T14 survey, T15 near-far), ET handoff v0.2 (radio LDO,
  2 × E01 pin map), KiCad brief (2 footprints, patch boards + tuning coupon), README.
- Republished brief v0.4, hardware v0.3, protocol v0.3; PDFs re-exported to `briefs/` and the Windows folder.
- **Start next session with:** antenna decision (patches / omni / mix), order placed?, ET pin map → Pico HAL.

### 2026-10-09 (later) — 2.4 GHz switch
- The other 3 teams want 2.4 GHz for all modes; Santiago: drop 868. 4 teams in total. Two antennas per box allowed.
- Haiku agents swept our files/web; a Sonnet agent picked the module from primary datasheets. Found in the rules:
  MRM is simultaneous (decisive for 2.4 GHz), NM round is 5 min.
- RT pick: Ebyte E01-ML01DP5 at ~+7 dBm + pad; 250 kbps everywhere; two vertical FR4 patches per box (one E01 each).
  MRM 260 m margin drops to +4.4 dB (from +13.9 at 868): antenna height and Atenea Q3 (FHSS 100 mW) are the levers.
- Added S16–S20 + near-far/channel-plan printout to `linkbudget.py`; workbook rebuilt, formulas = Python (0 diff).
  New D-R1b/D-R2b/D-R4 draft/D-R5b; old 868 records marked superseded. Atenea Q2 obsolete, Q3/Q4 rewritten, Q10 added.
- **Start next session with:** order placed? T0 output measurement; then redo the stale docs/firmware list above.

### 2026-10-09
- Andrian is starting band research: data/time, bandwidth, noise and interference per band,
  EIRP, spectral efficiency, modulation. Most of it is already in the workbook. Still open:
  measuring interference on campus (SDR/analyser survey) and 4-GFSK as an option (Si4463 only).
  Offered him a research map or a Noise & Interference sheet; no answer yet.
- Created the public GitHub repo `mtp-f26-teamc` (Santiago: OK if other teams see it). Excluded `docs/`
  and added `briefs/` (PDF exports), a README, and a sample-generator fallback to repo text when
  the course PDFs are missing (2.67×; all 11 sim tests still pass).
- Antennas: the RFM69HCW has none (only a 50 Ω ANT pad). Shortlist added to D-R5: Molex 211140 flex,
  Taoglas FXP895 flex, Linx ANT-868-HETH helical, Ignion NN chip. Wire λ/4 (86 mm) stays the QM antenna.
- Santiago opened the course AN5142 .xls (f0 = 2467 MHz) thinking it was ours. Built
  `AN5142_course_layout_869MHz.xlsx`, which reproduces the course example to 2e-13 dB. The 869 MHz baseline
  gives margins of SRI +36.7, MRM +13.9 and NM +20.5 dB, matching linkbudget.py. No Excel or LibreOffice here,
  so the original .xls can't be edited with its formulas kept.
- Purchase recommendation: Adafruit RFM69HCW breakout (PID 3070) for bench + QM, kept for the final
  so the QM module stays the same. €13.65 excl. VAT at Opencircuit, 10–12 days delivery: order by 16-Oct. Recorded in D-R2.
- Antenna pick: wire for QM, Molex 211140-0100 for the final (buy 4 + 3 u.FL connectors). Recorded in D-R5.
- Radio brief v0.3 and hardware page v0.2 republished (Adafruit breakout, antenna, shopping list,
  cost ≈€55–65 with lab PCB). PDFs re-exported to `briefs/` and the Windows folder; old versions removed.
- Wrote `hw/KICAD_SESSION_PROMPT.md` for a new session to design the carrier PCB with the KiCad MCP.
- Now a git repo: background sessions edit in a worktree (`.claude/worktrees/`, ignored). Santiago
  allowed pushing early commits straight to main.
- End of day: radio driver 154 checks, sim 11/11 scenarios, phy_config all checks OK.
- **Start next session with:** the KiCad prompt, or the outcome of Fri 16-Oct (sign-off, order placed?).

### 2026-10-07
- Read the full competition rules for hardware constraints. Key ones: one micro module only; no
  WiFi/BT chip, even unused (so no Pico W/ESP32); USB file I/O during a foil-wrapped setup,
  so ≥1 MB on-board storage is needed; drop test; Tx/Rx button + blinking LED; no node-position switch.
- Published the RT hardware suggestion for ET: Pico 2 (RP2350, non-W) + RFM69HW/HCW-868 on a
  custom 2-layer carrier, PIO-USB host on USB-A, 18650 + MCP73831, 5 V boost only for the stick,
  ≈€30–55/device. It is a suggestion, since ET owns the micro choice.
- Added Atenea Q6 (USB through the foil) and Q7 (micro+radio combo boards).
- Published the RT protocol/firmware suggestion for PT. Measured compression on English text in 100 B lines:
  deflate stream ≈3.0× (UTF-16 ≈4.7×), 4 KB blocks 2.2×. At ~3× the file takes ≈40 s instead of 119 s,
  so ≈9 rounds/h fit the duty limit instead of 3. NM proposal: Trickle gossip (RFC 6206), no routing.
  Added Atenea Q8 (role switch) and Q9 (encoding, output file name).
- Built the PC protocol simulator in `proto/`, which runs the same C protocol code the Pico
  will run. All 11 tests pass, and the main scenarios were checked over 20 seeds:
  10k lines in ≤38 s at 5 % loss, ≤50 s with fades plus a 10 s jamming attack, reboots resume,
  NM far end in ≤14 s (10 nodes). Without compression, only 9 643 lines.
  The sim found a bug: fixed timeouts broke the 38.4 kbps fallback (883 lines). Timeouts now
  scale with bit rate, and the fallback delivers 10k lines in 92 s.
- Exported the 3 pages (HTML + PDF, light theme for print) to
  `C:\Users\santi\Documents\Máster\3er Cuatri\MTP\Team C briefs\`. Re-export after republishing.

### 2026-10-04
- Created this CLAUDE.md (team, calendar, layout, status, log).
- Santiago adopted the RT recommendations as the working baseline (868 MHz + RFM69HCW).
- Built `radio/phy_config.py` (register profiles, CNAF fit, duty budget), `radio/fw/` driver +
  154 passing host tests, and the decision/handoff/NM/test-plan/Atenea docs.
- Finding: duty cycle, not range or rate, is the binding constraint (≈3 rounds/h/box).
- Published radio brief v0.2 (baseline, duty budget, ET handoff, NM PHY, test plan, questions).
- Added baseline scenarios S13–S15 to `linkbudget.py` and rebuilt the workbook (15 scenarios;
  formulas recalculated with `formulas`, zero difference vs Python).
- **Start next session with:** what came out of Fri 9-Oct (sign-off? other teams' bands?
  Atenea answers? ET micro choice?), then log it and update Status.

### 2026-10-03
- Read Team C's Project Definition from Drive; mapped sub-teams and RT scope.
- Found the Sept-18 advisory zip diverges from the real PD (dates, team, decisions).
- Built `radio/` workpack: `linkbudget.py`, `build_workbook.py`, link-budget xlsx
  (formulas verified against Python), and published the radio brief artifact.
- Proposed (not decided) 16-Oct band/module decision date.
