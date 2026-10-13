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
| Fri 16-Oct-26 | Proposed (not yet agreed) RT band + module decision; order radios + antennas (10–12 day delivery) |
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
- `radio/phy_config.py` — nRF24L01+/E01-ML01SP4 profiles (`TEAM_250K`, `TEAM_1M`, `NM_COMMON`), UN-85 b
  checks (channel, band edge, e.i.r.p. with the omni at 3 dBi peak, RF_PWR ≤ −18 dBm, MRM plan spacing);
  regenerates `radio/fw/nrf24_config.h` (incl. `NRF24_RF_PWR_MAX_BITS`). `E01_PA_GAIN_DB` is an estimate until T0.
- `radio/fw/` — portable C99 nRF24L01+ driver behind a HAL (DPL + NOACK frames, RF_CH ≤ 83, RPD),
  CRC-16, power clamp (refuses/clamps RF_PWR above −18 dBm), mock nRF24 with a simulated channel, host tests:
  `make -C radio/fw test` (124 checks).
  The RFM69 driver and duty-cycle guard were removed 9-Oct (in git history).
- `radio/DECISIONS.md` (D-R1b/D-R2c/D-R4 draft/D-R5c current; D-R2b/D-R5b and the 868 records superseded),
  `HANDOFF_ET.md` (SP4 interface for electronics), `NM_PHY_PROPOSAL.md` (nRF24 NM PHY for other teams), `TEST_PLAN.md`
  (T0 gate, T2, T4, T5, T13–T16; PER-based, nRF24 has no RSSI), `ATENEA_QUESTIONS.md` (for Marcos).
- Radio brief (artifact, private — Santiago shares it with the team):
  https://claude.ai/artifact/MqP1rz4NzHmGTgJCYMYGqw — source `radio/brief.html`; edit it and
  republish to the same URL (v0.5 published 13-Oct: SP4 + one omni decided, MRM channel plan, shopping list).
- Hardware proposal for electronics (artifact, private): https://claude.ai/artifact/81s3ZPuHznAvgXU9zWjaWb
  — source `radio/hw_proposal.html` (v0.4 13-Oct: Pico 2 + one E01-ML01SP4 + flex omni, radio LDO, breakout, BoM).
- `hw/` — carrier PCB work. `hw/KICAD_SESSION_PROMPT.md` is the brief for the KiCad MCP design session
  (constraints, parts, pin map, power, mechanics, checkpoints, deliverables).
- `proto/` — PT protocol code (`src/`: link ARQ+resume, NM Trickle gossip, codec) and the PC
  simulator (`sim/`): `make -C proto test` (11 scenarios, ~1 s). See `proto/README.md`.
- Protocol/firmware proposal for PT (artifact, private): https://claude.ai/artifact/6g1P41SGs1eGf9Jme8YsAK
  — source `radio/pt_proposal.html` (v0.3.1 13-Oct: 32 B nRF24 frames, SR-ARQ + resume, NM gossip, sim results).
- PDF/HTML exports of the three pages: `briefs/` and the Windows folder (light theme, Chrome headless with
  mermaid from jsDelivr; the 9-Oct export script lived in the job scratch dir — recreate if needed).

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
  may go straight to main (Santiago, 9-Oct); never force-push. `docs/` is
  git-ignored (copyrighted course material). Put PDF exports of the pages in `briefs/` too.

## Status (keep current)

**9-Oct-26: BAND SWITCH to 2.4 GHz.** All four teams (us + 3 others) chose 2.4 GHz for every mode;
868 MHz is dropped (kept in `radio/DECISIONS.md` as superseded history). Everything below is the 2.4 GHz baseline.

**Radio — key results (9-Oct, `python3 radio/linkbudget.py`, workbook S16–S20):**
- Limit 10 mW e.i.r.p. (UN-85 b). UN-85 a) gives a narrowband radio nothing (10 mW/MHz); only FHSS gets
  100 mW (+10 dB) → Atenea Q3. No duty-cycle limit.
- MRM is simultaneous (rules), 4 teams → one channel each at 2.4 GHz (at 868 they'd share 250 kHz).
- Margins at h 0.75 m with SP4 + one omni (workbook S21–S23): **SRI 70 m +26.0 · MRM 260 m +3.4 (thin; +8.3 at
  1.0 m) · NM 100 m hop −10 dB obstr. +9.9 dB**. If T0 measures only ~+2 dBm out, every margin drops ~5 dB.
- NM round is **5 min** (SRI/MRM 2 min); NM file is 0.5 kB.

**Baseline (2.4 GHz; module + antenna DECIDED 13-Oct by Santiago with Marcos):**
- D-R1b 2400–2483.5 MHz, **250 kbps GFSK in every mode** (goodput ~159 kbps ≫ 67 needed).
- D-R2c **Ebyte E01-ML01SP4** (genuine nRF24L01P + PA/LNA, SMD 14.85 × 18 mm, 1.27 mm pads, IPEX), one per box,
  RF_PWR −18 only (+2..+7 dBm est.) → ≤ 9.5 dBm e.i.r.p.; needs a breakout from the first bench test (QM module
  = final). Not the DP5 (adapter loss), not the 2G4M27D (~12 dBm e.i.r.p.), never E01C-* (Si24R1 clone).
- D-R5c **one Molex 146153-0100 flex omni** (34.9 × 9 mm, 2.4–3.0 dBi, U.FL) plugged into the SP4, vertical, high
  on a wall. Same antenna for SRI/MRM/NM and QM (antennas can't change between modes). Patches dropped.
- D-R4 draft: MRM channels RF_CH 24/49/74/82; near-far up to 55 dB at 2 m → ≥10 m between teams' boxes.

**Open decisions:**
- [ ] D-R4 channel plan with the 3 other teams (after Andrian's campus WiFi survey)
- [ ] D-R3 NM common PHY: rewrite `NM_PHY_PROPOSAL.md` for nRF24
- [ ] Atenea Q3 (FHSS 100 mW) — worth +10 dB on MRM

**Next up:**
- [ ] Order by 16-Oct (D-R2c): 6 × E01-ML01SP4, 4 × Molex 146153-0100 (MHF, not MHF4), 2 × U.FL-to-SMA pigtails.
      Verify EU seller + lead time first. Not needed: DP5, SMA pads, whips, Adafruit RFM69, 868 Molex.
- [ ] ET: SP4 breakout (1.27 → 2.54 mm) for the first bench test
- [ ] T0: measure SP4 output at RF_PWR −18 (U.FL-to-SMA pigtail into the SA) before any field test; T2 at 250 kbps
- [ ] Andrian: campus 2.4 GHz survey (eduroam channels at the SRI/MRM/NM sites) — now decides D-R4
- [ ] Share brief v0.5 / hw v0.4 / pt v0.3.1 + `NM_PHY_PROPOSAL.md` v0.2 and the MRM channel plan with the teams
- [ ] Write the Pico 2 HAL for `nrf24_hal_t` once ET confirms the pin map; MRM 4-team sim scenario
- [ ] **ON HOLD (9-Oct):** CST MCP (patches dropped 13-Oct; still useful to model the omni in the box). Santiago is asking the radio teacher which CST version
      the team may install on laptops. Then: review the code of `teslawei/mcp-cst-studio` (live on Windows, or
      offline VBA from WSL) or `woson-L` CST-MCP (CST 2026 Python API) before installing; `mcp-openems` as a
      free cross-check. Nothing installed yet.
- [ ] Measure the IKEA 365+ box inside dimensions (where the omni can sit highest; board outline)
- [ ] Marcos posts `ATENEA_QUESTIONS.md` (Q2 and Q10 not needed; Q1, Q3, Q4 updated)
- [ ] Share the protocol proposal with PT (Ibrahim, Guillem, Sofia); PT owner for NM gossip talks

## Session log

Newest first. One entry per session: what was done, what was decided (and by whom),
what's pending.

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
