# Radio Team decisions — MTP-F26 Team C

Status key: **Proposed** (RT recommendation, not yet signed off) · **Agreed** (RT + PM sign-off,
with date) · **Superseded**.
Santiago accepted the RT recommendations as the working baseline on 4-Oct-26 so that build work
can start. They still need sign-off from Andrian and Marcos (PM), ideally at the Fri 9-Oct
session and no later than Fri 16-Oct.

---

> **9-Oct-26: band switch.** All four teams (us + 3 others) chose 2.4 GHz for every mode, so the
> 868 MHz records below (D-R1, D-R2, D-R5 initial) are **superseded** by D-R1b, D-R2b and D-R5b.
> They are kept for the report (why 868 was the better link and what 2.4 GHz costs). Numbers:
> `python3 radio/linkbudget.py`, scenarios S16–S20 of the workbook.

> **13-Oct-26: antenna and module decided** (Santiago, with Marcos): **one omni per box on an Ebyte
> E01-ML01SP4** (D-R2c, D-R5c). Antennas cannot change between competition modes, and the patches'
> NM risks (aiming, the rim corner, tuning) outweighed their +1 dB on MRM. D-R2b and D-R5b are superseded.

> **16-Oct-26: 20 dBm e.i.r.p. is the SRI/MRM baseline (D-R6).** A professor said yes to 20 dBm e.i.r.p.
> (reported by Santiago). Under CNAF UN-85 a) that applies to a narrowband radio only when it **hops** with
> the EN 300 328 sharing rules, so SRI and MRM run as adaptive FHSS + LBT on the same hardware (SP4 + one
> omni): **+10.5 dB** on every link (+5.0 dB at today's RF_PWR −12 until T0). NM stays at 10 mW on one channel.
> The 10 mW fixed-channel profile stays for Quick Mode, the bench and as the fallback.

> **18-Oct-26: the micro is a Raspberry Pi 3** (team request, D-H1). Nothing in the radio changes (SP4, omni,
> profiles, margins, NM spec). The controller, its power tree and the software port change; see D-H1 and
> `radio/pi3_impact.html`.

## D-H1 — Micro module: Raspberry Pi 3 (Model A+ suggested), WiFi/BT chip disabled or removed

**Status:** **Team request 18-Oct-26** (reported by Santiago); ET owns the choice of model; working assumption until
Atenea Q22 is answered · **Owner:** ET (board, model) + PT (Linux software) + RT (radio checks)

- **Rule.** The rules allow "one but only one module including a microprocessor (e.g. Arduino, BeagleBone,
  Raspberry…)" but ban "any chip implementing a standard wireless access protocol (e.g. WiFi, Bluetooth…)". Every
  Pi 3 (B, B+, A+) carries one (BCM43438 / CYW43455). Working assumption (Santiago): allowed if disabled for good in
  software (`dtoverlay=disable-wifi`, `disable-bt`, rfkill) or desoldered. **Atenea Q22** asks; the answer is needed
  before Quick Mode (6-Nov), because the micro shown there is final. Fallback if removal is required and desoldering
  fails: Compute Module 3+ (same SoC, no wireless, SODIMM carrier).
- **Model.** A+ suggested: lowest draw (~0.30–0.40 A at 5 V with one core busy), 65 × 56 mm, one USB port direct to
  the SoC. B works if owned (owned boards still count at market price in the BoM).
- **Hardware consequences.** HAT-style carrier on the 40-pin header; always-on 5.1 V boost ≥ 2.5 A from the cell
  (up to ~2 A input near 3.0 V); MAX17048 fuel gauge (no ADC); radio LDO from the cell as before, never the Pi's 3V3;
  stick on the Pi's own USB port (PIO-USB, stick boost and switch dropped); microSD taped for the drop test.
  ~1.7–2.2 W per box (A+), 4.2–5.4 h on one 3000 mAh cell; ~70–90 € per box (was 40–55 €).
- **Software consequences.** Same C code; Linux HAL (spidev one ioctl per command, libgpiod CE/IRQ with kernel
  timestamps, busy-wait µs delays), timerfd/epoll environment, files on the SD card with fdatasync, FatFs over the
  raw stick block device, read-only root, systemd watchdog. Tight timers (idle-ACK ~4 ms, TX_DS ~3.8 ms) need
  PREEMPT_RT + SCHED_FIFO on an isolated core, or wider values on Linux.
- **Numbers.** Goodput 107 → ~97 kbps if the frame gap grows to 0.5 ms (73 kbps at 1 ms gap + 2 ms turnaround, still
  > 67). A Linux reboot costs 10–30 s instead of 0.3 s: sim T19 (MRM as T14, receiver down 30 s) delivers the file in
  90.8 s (78.0 s at 10 s down, 60.5 s on the Pico). Boot target ≤ 10 s.
- **Radio checks added.** T0: Pi noise per hop channel (idle/busy, wireless off/removed) and the Pi's current at
  3.6/3.3/3.0 V. T2: frame gap and turnaround on the Pi.
- Superseded: the Pico 2 suggestion (hw_proposal v0.4.x, in git history).

## D-R6 — SRI/MRM as adaptive FHSS + LBT at ≤ 20 dBm e.i.r.p. (CNAF UN-85 a)

**Status:** **Baseline since 16-Oct-26, confirmed** (a professor approved 20 dBm e.i.r.p.; Atenea Q3 answered
yes, reported by Santiago) · **Owner:** RT (PHY, driver) + PT (hop sync)

- **Rule.** CNAF UN-85 a) ("wideband data transmission systems", EN 300 328): **100 mW e.i.r.p.**, density
  ≤ 100 mW/100 kHz for **FHSS** and ≤ 10 mW/MHz for any other modulation, with access/mitigation techniques
  mandatory. Our non-hopping 250 kbps signal is < 1 MHz wide, so without hopping a) gives ~10 dBm: nothing.
  UN-85 b) (generic SRD, EN 300 440) stays < 10 mW. The course rules require CNAF 2017 compliance and say
  oral comments do not override the written rules; the professor's yes was confirmed on Atenea (Q3, 16-Oct).
  Keep the analyser plots (T13, T17, T18) as evidence for the ANNEX, and cite Q3 there.
- **Which FHSS.** EN 300 328 V2.2.2 has two kinds:
  - *Non-adaptive* (cl. 4.3.1.3/4.3.1.6): bursts ≤ 5 ms, gaps ≥ 5 ms and medium utilisation
    MU = P/100 mW × duty ≤ 10 % → 10 % duty at 20 dBm = ~16 kbps goodput (2 380 lines raw). Too slow.
  - **Adaptive with LBT (cl. 4.3.1.7.2): chosen.** No duty limit. ≥ 15 hop channels at all times over
    ≥ 70 % of the band; ≤ 400 ms TX per channel in any 400 ms × N window; before transmitting on a hop, an
    energy-detect CCA ≥ 18 µs (and ≥ 0.2 % of the occupancy time) at −70 dBm/MHz for 20 dBm (relaxed
    10·log(100 mW/P) below that, corrected for antenna gain); channel occupancy < 60 ms, then idle ≥ 5 %;
    busy channels are skipped; TX and RX follow the same hop pattern.
- **Our design** (`phy_config.py` TEAM_FHSS, all checks OK):
  - Hop set: **even RF_CH 4…78 without 26: 37 channels, 74.6 MHz (89 % of the band)**. The BLE advertising
    channels 2402/2426/2480 MHz (RF_CH 2/26/80) are left out: every phone near the boxes beacons there (review).
    Every team uses 20 dBm, which a narrowband radio may only do while hopping, so the other teams hop too: no fixed
    channels to avoid (the ±5 MHz guard around 24/49/82 is kept in `phy_config.py`, empty).
  - **Per-team hop order:** two unsynchronised teams on the same order and slot would collide in a fixed pattern
    for the whole round. Ours: stride 7 (`FHSS_STRIDE`); the NM/inter-team spec asks every team for a different
    stride (or its own permutation).
  - Hop order: sorted set with index stride 7 → consecutive hops ≥ 14 MHz apart; each channel once per
    1.2 s cycle. Slot (dwell) **30 ms** = one 16-frame burst (~26 ms) + turnaround + its ACK (~28.5 ms) + guard
    (25 ms until the 16-Oct review: too short for burst + ACK); accumulated TX ≤ 150 ms per channel.
  - CCA = the nRF24's RPD bit after 170 µs in RX (−64 dBm at the chip; ~−76 dBm at the SP4 port with an
    LNA of ~12 dB, ESTIMATE). Needed: ≤ −64 dBm at RF_PWR −12 (15.5 dBm e.i.r.p.), ≤ −68.5 dBm at 20 dBm.
    **T17 measures the RPD trip level**; if the LNA gives < ~5 dB, 20 dBm needs a lower step.
  - COT 50 ms, idle 2.5 ms, CCA 170 µs; hop + CCA overhead 0.3 ms per 30 ms slot (1.0 %).
- **Power and module: keep the SP4 + omni.** The SP4 is a +20 dBm module that we hold at RF_PWR −18. For
  20 dBm e.i.r.p. with the 3 dBi peak omni it needs ≤ +17.5 dBm at the IPEX. RF_PWR steps are 6 dB apart and
  the PA gain is only known to 20–25 dB, so `phy_config.py` takes the highest step that is legal at the
  worst-case gain: **−12 today (≤ 15.5 dBm e.i.r.p.)**; if T0 measures the gain ≤ 21.5 dB (≤ 23.5 dB before the review's +1.5 dB for in-box gain and per-module
  spread, and no credit for the cable that Molex may already count), −6 becomes legal
  (14–17.5 dBm out → 16.5–20 dBm e.i.r.p.). The E01-2G4M27D would now be legal in this mode (−99 dBm claimed)
  but cannot do the 10 mW fixed-channel mode (NM, Quick Mode, the fallback): not reopened.
- **NM stays on its fixed channel under UN-85 b)** (10 mW, +9.9 dB). A hopping NM shared by four teams'
  boxes would need network-wide hop sync for a 0.5 kB file: not worth it.
- **Firmware** (`radio/fw`, 235 checks): only an `lbt` profile may use RF_PWR above −18 dBm
  (`NRF24_RF_PWR_MAX_BITS_FHSS`); a fixed-channel profile asking for it is refused at init. With an lbt
  profile the driver refuses channels outside the hop set, refuses to send without a clear `nrf24_cca()` on
  the current hop, ends the occupancy at 50 ms and waits the idle gap before a re-CCA on the same channel.
  Hop timing (`nrf24_fhss_channel(slot)`) and skipping a busy slot are the protocol's job.
- **Protocol** (`proto/sim --fhss BUSY`): the link code is unchanged; the radio layer hops. T12: all
  10 000 lines in 37.9 s with 5 % loss and 10 % of hops busy; T13: 57.2 s with 25 % busy and a receiver reboot
  (re-sync = one hop cycle). Still to design: hop acquisition on the Pi 3 (RX parks on one channel until
  the sender's slot clock is heard; each frame carries the slot number).
- **Margins** (h 0.75 m, workbook S24–S26): **SRI 70 m +36.5 · MRM 260 m +13.9 (+6.9 even at 0.5 m) ·
  MRM at the worst RF_PWR step +8.4 dB**, vs +26.0 / +3.4 at 10 mW. NM unchanged at +9.9.
  **Conservative planning case** (review 16-Oct; `linkbudget.py`): 1 %-PER sensitivity (+3 dB), 0 dBi at the worst
  azimuth in the box, 6 dB fade/body margin → **MRM +0.9 dB at 20 dBm, −4.6 dB at RF_PWR −12, −9.6 dB at 10 mW;
  NM 100 m behind a corner −3.1 dB; SRI 70 m at 10 mW +13 dB.** So MRM and NM are not safe on paper: antenna height,
  keeping people ≥ 2 m away and out of the path, and the T4/T5 measurements (attenuation to failure) decide.
- **Other teams (MRM near-far, `linkbudget.py`):** all four teams hop at 20 dBm, so the power ratios are the same
  as when everyone was at 10 mW: another team's box at 10 m lands 41.4 dB above our 260 m partner, 47.4 dB with the
  +6 dB two-ray peak possible inside the breakpoint. Hops < 6 MHz apart collide (selectivity −38 dB or worse):
  **~13 % of hop pairs at 10–20 m**, 8 % at 30 m, 55 % at 5 m, all at 2 m. Pessimistic (no CCA help): ~31 % of our
  ACKs lost at the sender end (three senders next to ours; the weak end), ~2 % of DATA at the receiver end, and a
  ~7 % co-channel ACK floor at any spacing (their CCA cannot hear us while we listen). Hence the **POLL**: on an ACK
  timeout the sender asks for the ACK with one short frame instead of resending the burst. **Ask for ≥ 10 m between
  teams' boxes at each MRM end, ideally ≥ 30 m between the senders** (never 2 m). Every team must use LBT.
- **Quick Mode** keeps TEAM_250K (one fixed channel, 10 mW): one line in < 2 min doesn't need the margin, and
  the hop sync may not be on the Pi 3 yet.
- **SRI also runs on TEAM_250K** (16-Oct review): teams take turns in SRI, +26 dB at 70 m and 10 mW is ample,
  goodput is highest without hopping (159 vs 141 kbps), and SRI then does not depend on the hop sync. The 20 dBm
  modes (option A, or B if Q11 = yes) are for MRM.
- **Not every team may hop.** If a team stays on a fixed channel, put that channel in `FHSS_OTHERS`
  (`phy_config.py`): the ±5 MHz guard is still there, one line to re-enable.

- **Two versions (16-Oct, Santiago: "apparently we wouldn't need to frequency hop"; rechecked, keep both):**

  | | **Option A: hopping (default)** | **Option B: one fixed channel** |
  |---|---|---|
  | Profile | `TEAM_FHSS`: 40 hops, 30 ms slots | `TEAM_20DBM_FIXED`: RF_CH 74 (MRM plan 24/49/74/82) |
  | EN 300 328 class | adaptive FHSS, LBT (cl. 4.3.1.7.2) | adaptive non-FHSS, frame-based LBT (cl. 4.3.2.6.3.2.2) |
  | Listen-before-talk | CCA per hop, COT ≤ 50 ms | CCA every ≤ 10 ms (COT 10 ms, idle 0.5 ms): ~6 frames per CCA |
  | Power density | 100 mW/100 kHz allowed: **compliant** | **10 dBm/MHz limit (cl. 4.3.2.3; EU Dec. 2006/771/EC as amended)**: a < 1 MHz signal at 15.5–20 dBm is **5–10 dB over** |
  | Margins (S24–S25 / S27–S28) | SRI +36.5, MRM +13.9 dB | identical |
  | Firmware / protocol | hop clock + acquisition on the Pi 3 | none: today's link code on one channel |
  | MRM sharing | random hop collisions (12 % of pairs at 10 m), ≥ 10 m | fixed plan at equal power: 74/82 pair 41 dB at 10 m vs −50 dB: OK at ≥ 10 m |
  | Use when | default | only if the course explicitly accepts 20 dBm on one fixed channel (Atenea Q11) |

  The UN-85 note in CNAF 2013/2017 states the density limit in its own text; CNAF 2021 refers to the EU decision,
  whose annex keeps "100 mW/100 kHz for FHSS, 10 mW/MHz for other modulations". The CNAF now in force is Orden
  TDF/732/2026 (BOE-A-2026-15661); its consolidated text leaves the UN notes out, so the EU decision is the
  reference. Switching A ↔ B is one profile change in the firmware; both are built and tested (`radio/fw`, 235 checks).

**Reverse if:** T17 shows the RPD threshold cannot meet the CCA level at a useful power, or the hop sync is not
working on the bench and in a 260 m field test by the **go/no-go on Fri 20-Nov** (not the pretest: too late to
recover): then MRM falls back to TEAM_250K at RF_PWR −18 (or option B if Atenea Q11 = yes).

## D-R2c — Module: Ebyte E01-ML01SP4 (genuine nRF24L01P + PA/LNA, SMD, IPEX)

**Status:** Decided 13-Oct-26 (Santiago, with Marcos) · **Owner:** RT → handed to ET

- Same radio as the DP5 (genuine Nordic nRF24L01P, PA + LNA, FCC/CE), SMD **14.85 × 18 mm, 10 pads at
  1.27 mm**: 1 VCC, 2 CE, 3 CSN, 4 SCK, 5 MOSI, 6 MISO, 7 IRQ, 8–10 GND. Supply 2.0–3.6 V (abs. max 3.6 V).
  TX 120 mA, RX 26 mA. Max output +20 dBm. **Sensitivity −96 dBm typ at 250 kbps** (datasheet).
- **IPEX (U.FL) socket on the module**: the omni's cable plugs in directly, so no SMA adapter and its loss.
- Why not the DP5 (SMA): it would need an SMA-male to U.FL-jack adapter (~0.5 dB) for the flex omni.
  Why not the 2G4M27D: its ~+9 dBm floor behind a ~3 dBi antenna is ~12 dBm e.i.r.p., over the limit.
- **Power:** RF_PWR −18 dBm only. Output +2..+7 dBm at the IPEX (PA gain 20–25 dB, ESTIMATE) → ≤ 9.5 dBm
  e.i.r.p. with the 3 dBi datasheet peak gain. The driver refuses any profile above −18 dBm and clamps
  direct RF_SETUP writes (`NRF24_RF_PWR_MAX_BITS`). T0 measures the real output; if it is only ~+2 dBm,
  every margin below drops by ~5 dB. Since 16-Oct (D-R6) SRI/MRM run the same module at RF_PWR −12/−6 as
  adaptive FHSS (≤ 20 dBm e.i.r.p.); −18 stays for NM, Quick Mode and the fallback.
- **SMD consequence:** modules shown at Quick Mode are final, so the SP4 needs a breakout (lab-made or the
  carrier PCB) from the first bench test. No breadboard stage with a different module.
- **Shopping (order by Fri 16-Oct; price and EU lead time to verify):** 6 × E01-ML01SP4 (2 boxes, 2 bench,
  2 spare), 4 × Molex 146153-0100, 2 × U.FL-plug to SMA-female pigtails (for T0/T13 on the spectrum
  analyser). Not needed any more: E01-ML01DP5, SMA pads, SMA whips.

## D-R5c — Antenna: one flex omni per box (Molex 146153-0100)

**Status:** Decided 13-Oct-26 (Santiago, with Marcos) · **Owner:** RT

- Molex 146153-0100: flex dipole (2.4/5 GHz), 34.9 × 9 mm, 0.1 mm, adhesive, 100 mm cable, U.FL/MHF
  (check the part is MHF, not MHF4). Datasheet peak gain 2.4–3.0 dBi (distributors disagree), efficiency
  > 66 % at 2.4 GHz. Backup: Taoglas FXP73.07.0100A (47 × 7 mm, 2.5 dBi, 50 %).
- Mounting: **vertical** (vertical polarisation, as agreed for NM), as high as possible on a side wall,
  ≥ 1–2 cm from the battery, PCB copper and metal, same orientation in every box.
- Model: 2 dBi in the box (container −1 dB separate), 0.5 dB cable, sensitivity −96 dBm. Margins at
  h = 0.75 m: **SRI 70 m +26.0 dB · MRM 260 m +3.4 dB (+8.3 at 1.0 m) · NM 100 m hop (−10 dB) +9.9 dB**
  (workbook S21–S23). MRM is the thin link: 20 dBm hopping (D-R6, +10.5 dB, now the baseline: +13.9 dB)
  and antenna height are the levers.
- No sideways rejection: the MRM channel plan's ≥ 10 m between teams' boxes still holds (8 MHz pair:
  41 dB near-far at 10 m vs −50 dB selectivity), but there is no extra isolation from the antenna.
- Quick Mode: the same flex antenna (simplest; the rules would allow a different one).
- T5 measures the in-box gain (whip reference vs flex, box open vs closed).

## D-R1b — Band: 2.4 GHz ISM (2400–2483.5 MHz), all modes, 250 kbps

**Status:** Agreed between the teams (reported by Santiago, 9-Oct-26) · details Proposed · **Owner:** RT

- **Why it is right for the competition:** MRM runs all teams *simultaneously* (rules: "all teams will have
  to operate their systems simultaneously"). At 868 the four teams would share one 250 kHz channel
  (~67/4 kbps each); at 2.4 GHz each team gets its own channel (D-R4). NM needs one PHY shared by all
  teams, and everyone is now on 2.4 GHz. No duty-cycle limit, so unlimited test rounds.
- **What it costs:** limit is **10 mW e.i.r.p.** (UN-85 b). UN-85 a) does not help a non-hopping
  radio (10 mW/MHz, and our signal is < 1 MHz wide); only FHSS gets 100 mW (Atenea Q3, S20: +10 dB).
  Margins at h = 0.75 m for the 9-Oct DP5 + patch build (history; current numbers in D-R5c and D-R6): **SRI 70 m +27.0 dB, MRM 260 m
  +4.4 dB, NM 100 m hop (−10 dB obstruction) +10.9 dB**, vs +36.7 / +13.9 / +20.5 at 868. MRM is the
  thin one: +9.3 dB at 1.0 m height, −2.6 dB at 0.5 m, so mount the patches as high as the box allows.
- **One air rate, 250 kbps GFSK, in every mode:** best sensitivity (−94 dBm chip) and best
  selectivity (D-R4). Goodput ~159 kbps with 32 B payloads, vs 67 kbps needed for the whole 1 MB file
  uncompressed, so 1–2 Mbps buys nothing that scores. 1 Mbps stays an SRI option (+18 dB).
- Legal channels: RF_CH 0–83 (f = 2400 + RF_CH MHz); ≤ 82 at 2 Mbps.

**Reverse if:** never for the band (the teams agreed). Revisit the rate if T2 shows 250 kbps PER problems.

## D-R2b — Module: Ebyte E01-ML01DP5 (genuine nRF24L01P + PA/LNA, SMA) — *superseded 13-Oct-26 by D-R2c*

**Status:** Proposed (RT pick 9-Oct-26, Santiago delegated the choice) · **Owner:** RT → handed to ET

- Genuine Nordic nRF24L01P (Ebyte), PA + LNA front end (assumed Skyworks RFX2401C: PA ~25 dB,
  LNA 12 dB / NF 2.5 dB, always in line), SMA-K, 2.54 mm DIP pins: SPI + CE + CSN + IRQ, 3.3 V.
  PA/LNA switching is inside the module. Mature drivers (RF24 library, ports for the Pico).
- **Power setting:** RF_PWR = −18 dBm gives about **+7 dBm at the SMA** (ESTIMATE from the PA gain;
  Ebyte publishes no table). With a 1 dB pigtail and a 4.5 dBi patch that is 10.5 dBm e.i.r.p., so a
  **≥ 0.5 dB pad** (buy 1/2/3 dB SMA pads) brings it to 10.0. With the 2 dBi QM whip no pad is needed
  (+8 dBm e.i.r.p.). **T0 must measure the real output** with a power meter / SA before any field test.
- Sensitivity in the model: chip value (−94 dBm @250 kbps), LNA ignored. Ebyte quotes ~−96 for the
  SMD sister part; T2 decides.
- **Backup:** E01-ML01SP4 (same radio, SMD 14.85 × 18 mm, u.FL) if ET prefers to solder it to the carrier.
- **Do not buy** E01C-* parts or no-name "nRF24L01+PA+LNA" boards: Ebyte's own E01C manual says
  Si24R1 clone. Check the chip on arrival (register behaviour, RPD bit).
- The Adafruit RFM69HCW order (old D-R2) is **cancelled**.
- **Shopping (order by Fri 16-Oct; prices and EU lead time still to verify):** 10 × E01-ML01DP5
  (2 boxes × 2 antennas, 4 bench, 2 spare), 2 × E01-ML01SP4, a set of SMA pads (1, 2, 3 dB, ×2),
  6 × SMA-to-u.FL / SMA pigtails (~10 cm) for the patches, 2 × 2.4 GHz SMA whips (QM, bench).

**Reverse if:** T0 shows the output at RF_PWR −18 cannot be padded to ≤ 10 dBm e.i.r.p. without losing
> 3 dB, or T2 shows a clone/poor receiver. Fallback: E01-ML01SP4, then a no-PA module.

## D-R4 (draft) — MRM access: one channel per team (FDMA)

**Status:** Draft for the inter-team meeting · **Owner:** RT

- Four teams, each on its own channel, all at 250 kbps. Proposal: **RF_CH 24 / 49 / 74 / 82**
  (2424 / 2449 / 2474 / 2482 MHz): three sit in the gaps between WiFi channels 1/6/11 at 25 MHz spacing,
  the fourth at the band edge, 8 MHz from its neighbour.
- Near-far is the real limit (ARQ means both ends transmit). Another team's box at 2 m with patches
  aligned arrives **55 dB above** our 260 m signal; side-on (~10 dB rejection per patch) 35 dB; at 10 m,
  41 / 21 dB. nRF24 selectivity at 250 kbps: −50 dB beyond 6 MHz, −60 dB beyond 25 MHz.
  So: the 25 MHz pairs are safe even co-located; **the 74/82 pair needs ≥ 10 m between those two
  teams' boxes** (or side-on placement). Ask the organisers for ≥ 10 m spacing at each end anyway.
- Final channel numbers after the campus 2.4 GHz survey (Andrian): if eduroam is not on 1/6/11 there,
  shift the plan.
- **Superseded for MRM on 16-Oct:** every team uses 20 dBm, so every team hops (D-R6): no fixed channel plan.
  What the teams agree instead: LBT per EN 300 328, ≥ 10 m between boxes at each end, NM on RF_CH 77 at 10 mW (`NM_SPEC.md`).
  The fixed plan stays as the 10 mW fallback (we would use 74).

## D-R5b — Antennas: two FR4 patches per box, vertical, front and back — *superseded 13-Oct-26 by D-R5c*

**Status:** Proposed (9-Oct-26; two antennas per box are allowed, per Santiago) · **Owner:** RT

- **The patches must stand vertically.** A patch radiates broadside; flat on the carrier PCB in a box
  lying flat it points at the sky and is ~5–10 dB down at the horizon. So each patch is its own small
  board (≈ 60 × 60 mm, FR4 1.6 mm, same KiCad project/lab order as the carrier) fixed to a box wall,
  fed by an SMA/u.FL pigtail. **Vertical linear polarisation** (feed on the bottom edge), agreed with
  the other teams for NM.
- One patch on the front wall, one on the back: SRI/MRM aim the front one at the peer; in NM the
  chain neighbours sit on both sides. **One E01 module per patch** (two per box): no RF switch or RF
  layout on our PCB, both radios can listen at once (selection diversity), TX on the one facing the peer.
- Patch for 2.44 GHz on FR4 (εr 4.4, h 1.6 mm, transmission-line model): **W 37.4 × L 28.9 mm**,
  inset-fed 50 Ω. Expected 4–5 dBi on FR4 [ASSUMPTION, model uses 4.5]. Bandwidth only ~27 MHz
  (VSWR < 2) while FR4 εr ±0.2 moves f0 by **±55 MHz**, and the box wall pulls it lower. So: fab a
  **tuning coupon** with L = 28.0 / 28.5 / 29.0 / 29.5 / 30.0 mm, measure S11 inside the closed box on a
  VNA (Prof. Santos, RF lab), keep the length centred on our channel. It only has to cover our 1 MHz
  channel, not the whole ISM band.
- Height: the box is 7 cm tall outside; a 60 mm board needs ~62 mm inside (measure the IKEA box). If it
  does not fit, use a 55 mm ground (some gain loss) or ask whether the box may stand on edge (Atenea Q4).
- Quick Mode antenna: 2 dBi SMA whip straight on the E01 (+8 dBm e.i.r.p., no pad). Rules: antennas
  need not be final at QM.
- Review with Prof. Puente / Prof. Santos before the board order. T5 compares patch vs whip in the box.

**Alternative asked 9-Oct: one omni for RX and TX, one E01 per box.** The E01 can't reach the cap
by itself (+7 dBm out, no lower step than −18 dBm in the chip), so with a 2 dBi omni and a 1 dB pigtail
it radiates 8 dBm, 2 dB under the cap, and the receive side also loses the patch's 2.5 dB:
**−4 dB on every link** vs D-R5b.

| Build (h 0.75 m) | e.i.r.p. | SRI 70 m | MRM 260 m | MRM at 1.0 m | NM 100 m (−10 dB) |
|---|---|---|---|---|---|
| Two patches (D-R5b) | 10.0 | +27.0 | **+4.4** | +9.3 | +10.9 |
| One omni 2 dBi, pigtail | 8.0 | +23.0 | **+0.4** | +5.3 | +6.9 |
| One omni on the SMA (no pigtail) | 8.7 | +24.4 | +1.8 | +6.7 | +8.3 |
| One omni, 0 dBi in the box | 6.0 | +19.0 | −3.6 | +1.3 | +2.9 |
| One omni + 100 mW FHSS (Atenea Q3 yes) | 18.0 | +33.0 | +10.4 | +15.3 | +16.9 |

- For it: simplest hardware (no patch boards, no VNA tuning, one radio), off-the-shelf antenna, no
  aiming, covers every direction in NM.
- Against: MRM at 260 m has no margin at 0.75 m, and an omni can't reject a neighbouring team side-on
  (the 74/82 pair would need ~15–20 m between boxes instead of 10 m).
- Verdict: only if the antennas can sit at ≥ 1.0 m or Atenea allows 100 mW FHSS. A middle option
  keeps the omni's strengths: **one patch (front, for SRI/MRM) + one omni (for NM)**, one E01 each:
  +4.4 dB on MRM and all-round coverage in NM. The carrier PCB keeps footprint B for any of the three.

## D-R1 — Primary band: 869.40–869.65 MHz (centre 869.525 MHz) — *superseded 9-Oct-26 by D-R1b*

**Status:** Proposed (working baseline 4-Oct-26) · **Owner:** RT

- Only this sub-band and 2.4 GHz allow a continuous 2-minute round (CNAF UN-39: 500 mW e.r.p.,
  ≤10 % duty cycle; UN-85 b: 10 mW e.i.r.p.).
- Range: +37 dB margin at 70 m, +14 dB at 260 m at 100 kbps (flat-earth, worst-case ground
  bounce). 2.4 GHz with nRF24 has −4.6 dB at 260 m with whips.
- Throughput: 100 kbps fits the 250 kHz channel (Carson 200 kHz + ±17 kHz drift, 7.6 kHz guard)
  and gives ~67 kbps goodput. That just carries 10 000 lines raw, so compression is the margin.
- **Duty cycle is the binding constraint:** one 2-min sending round is ~115 s of TX; the budget
  is 360 s per hour per box, so **≈3 full sending rounds per hour per box**, campus tests
  included. Mitigations: the firmware duty-cycle guard (`fw/dc_guard.c`), and run bench and
  repeated tests in 869.70–870.00 MHz (5 mW, no duty-cycle limit, profile `BENCH_5MW`).
- 2.4 GHz stays open as an **MRM add-on** (D-R4), not the primary band.

**Reverse if:** the other teams converge on 2.4 GHz for NM, or Atenea rules the competition
schedule out of the 10 % budget.

## D-R2 — Module: HopeRF RFM69HCW, 868 MHz variant (Semtech SX1231H) — *superseded 9-Oct-26 by D-R2b*

**Status:** Proposed (working baseline 4-Oct-26) · **Owner:** RT → handed to ET

Why RFM69HCW over Si4463:
- Range is not the constraint at 868; the Si4463's extra 3 dB of power and sensitivity buys
  margin we don't need.
- Bring-up risk: RFM69 has mature open drivers (RadioHead, LowPowerLab) and simple registers;
  Si4463 needs Silicon Labs' WDS-generated config blobs.
- NM interoperability: the RFM69 is the module other teams are most likely to pick, which makes
  a common NM PHY easier.
- Lower protocol-ban risk: Si4463 advertises IEEE 802.15.4g PHY support.

Operating point: **+17 dBm (PA1+PA2), not +20 dBm**. The datasheet limits the +20 dBm
high-power mode to 1 % duty cycle. At +17 dBm the e.r.p. is ~27 mW, far under 500 mW.

Configuration: `phy_config.py` profiles `SRI_100K` (100 kbps GFSK BT 0.5, Fdev 50 kHz),
`ROBUST_38K4` (fallback, +5 dB), `NM_COMMON` (shared PHY draft) and `BENCH_5MW`. Driver in `fw/`.

Purchase (recommended 9-Oct-26): the **Adafruit RFM69HCW breakout, PID 3070** ("868 or 915 MHz"; per
LowPowerLab the 868 and 915 MHz HopeRF parts are the same hardware). Buy 3 (2 boxes + 1 spare) for the bench and
Quick Mode, and **keep it in the final boxes** (soldered to the carrier PCB by its 0.1" headers), so the module shown
at QM is literally the one that competes. Price checked 9-Oct at Opencircuit: €13.65 excl. VAT (€16.50 incl.), 10–12 days
delivery, so it costs ~€10 per device more than a bare module (~€3–4). **Order by Fri 16 Oct** to have it for T0/T2
before a Quick Mode attempt in early November. The u.FL connector is not included (buy separately). Its 3.3 V regulator takes the
~95 mA TX bursts off the micro's supply, and it has u.FL/SMA pads. Switch to the bare RFM69HCW-868 only if the team
decides so **before** QM.

**Frozen at Quick Mode** (rules): changing the module afterwards loses the bonuses, so bench
test T2 must confirm 100 kbps PER before QM.

**Reverse if:** T2 shows 100 kbps sensitivity worse than −95 dBm, or Atenea bans the chip.
Fallback: Si4463 (same band, same link budget, more effort).

## D-R5 (initial) — Antenna for QM: λ/4 inverted-L wire, top of the box — *superseded 9-Oct-26 by D-R5b*

**Status:** Proposed · **Owner:** RT

- A λ/4 at 869.5 MHz is 86 mm; the box is 70 mm tall. Start with a solid-core wire soldered to
  the ANT pad, ~60 mm vertical up the box wall plus ~25 mm horizontal under the lid. Cut long,
  trim for best RSSI (later with a VNA at the antenna lab).
- Mount the radio and antenna as **high in the box as possible**: antenna height is the biggest
  lever (+12 dB going from 0.5 to 1.0 m at both ends).
- In parallel, buy one 868 MHz u.FL FPC or helical antenna for an A/B comparison in T5.
- Ask Concepción Santos / Carles Puente to review before the final choice (week 8).
- Shortlist for the final antenna (9-Oct-26, datasheet figures; buy with the radios for test T5).
  The RFM69HCW has no antenna, only a 50 Ω ANT pad, so add a u.FL next to it:
  | Antenna | Size | 868 MHz figures | Notes |
  |---|---|---|---|
  | Molex 211140-0100 (flex, u.FL, 100 mm cable) | 38 × 10 mm | 0.3 dBi peak, > 55 % eff. | Smallest; sticks vertically on the box wall near the top |
  | Taoglas FXP895.07.0200C (flex, u.FL) | 69.3 × 20 mm | 1.9 dBi peak, 52 % eff. | Better gain; 69 mm barely fits the 70 mm box height |
  | Linx ANT-868-HETH (helical, through-hole) | 25.4 × 15.3 × 8.9 mm | 5.6 dBi peak (on Linx's eval board) | Solders to the carrier PCB; needs its ground plane; real gain in the box will be lower |
  | Ignion NN chip booster | ~ a few mm | depends on matching network | Needs a matching network + VNA tuning on the PCB; Carles Puente co-founded Ignion |

**Antenna pick (recommended 9-Oct-26, Santiago asked for one choice):**
- Quick Mode: the λ/4 wire (86 mm, inverted-L). The rules allow antennas to change after QM, and it costs nothing.
- Final: **Molex 211140-0100** flex antenna (868-870 MHz, 38 × 10 mm, u.FL, 100 mm cable, 0.3 dBi peak, > 55 %
  efficiency, omni, linear; ~$2.50 at DigiKey). It fits upright on the box wall under the lid and survives the drop
  test glued flat. Its -5 dB return loss costs ~1.7 dB of mismatch, which the +13.9 dB MRM margin absorbs.
- Buy 4 antennas + 3 u.FL SMT connectors for the Adafruit boards (the connector is not included).
- Mount: vertical, as high as possible, ≥ 2 cm from the battery and any metal, same orientation in both boxes.
- Test T5 decides it: keep the Molex if it is within 3 dB of the wire in the closed box; otherwise fall back to the
  wire or try the Taoglas FXP895. Unknown: whether it needs a ground plane. Check the datasheet, then measure.

## Open

| ID | Decision | Target |
|---|---|---|
| D-H1 | Raspberry Pi 3 as the micro: Atenea Q22 (WiFi/BT chip disabled vs removed); ET picks the model (A+ suggested) | Q22 before QM 6-Nov |
| D-R3 | NM PHY + protocol shared by all teams: agree `NM_SPEC.md` v1.0 (nRF24, RF_CH 77, Trickle gossip, test vector) and learn every team's chip | inter-team meeting by 23-Oct; first interop test by 6-Nov |
| D-R4 | Superseded for MRM (every team hops); fixed plan 24/49/74/82 kept for the 10 mW fallback and option B | — |
| D-R5c | In-box gain of the flex omni (T5), mounting height | week 8 |
| D-R6b | Option B (20 dBm on one fixed channel, no hopping): ask Atenea Q11; use only on an explicit yes | Q11 now |
| D-R6 | 20 dBm hopping is the baseline (Atenea Q3 = yes, 16-Oct): T0 all steps, T17, T18; hop sync on the Pi 3; ≥ 10 m between teams' boxes at MRM | bench by week 8 |
