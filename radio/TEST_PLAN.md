# Radio test plan — nRF24L01+ / Ebyte E01-ML01SP4 + flex omni, 2.4 GHz

Version 0.5, 16-Oct-26 (v0.5: 20 dBm hopping is the SRI/MRM baseline; v0.4 added T0 all power steps, T17 CCA
threshold, T18 hopping;
v0.3 SP4 + omni; v0.2 the DP5 + patches; v0.1 the RFM69 at 868 MHz) · Owner: RT · Expected
values come from `linkbudget.py` (flat earth, worst-case ground bounce, antennas at 0.75 m,
−1 dB container, chip sensitivity −94 dBm at 250 kbps).

No duty-cycle limit at 2.4 GHz: tests can be repeated freely. **Never exceed 10 dBm e.i.r.p. on a fixed
channel**: the driver only accepts RF_PWR −18 dBm for `TEAM_250K`, `TEAM_1M` and `NM_COMMON`. `TEAM_FHSS` (D-R6,
the SRI/MRM baseline, up to 20 dBm e.i.r.p. while hopping with LBT) goes outdoors once T0, T17 and T18 pass.

**The nRF24 has no RSSI.** It only has RPD, one bit that says "above −64 dBm at the chip" (about
−76 dBm at the E01 antenna port, through its ~12 dB LNA). So every range test measures **PER**
(frames lost out of frames sent), and levels come from the spectrum analyser or the model.

Record for every run: date, place, profile, RF_CH, distance, antenna, heights, box open/closed,
pad, frames sent/received.

## T0 — Bring-up and output power (bench, the day the modules arrive) — **gate for any field test**

1. Wire one SP4 (on its breakout) to the Pico (SPI + CSN + CE, 3.3 V with ≥ 100 µF near the module); run
   `nrf24_init`. Pass: `NRF24_OK`. `NRF24_ERR_SPI` = wiring/CSN; `NRF24_ERR_NOT_PLUS` = an old
   nRF24L01 (no 250 kbps), return it.
2. **Conducted output power at all four RF_PWR steps** (−18 / −12 / −6 / 0 dBm; a lab-only test build
   unlocks them, CW or continuous frames), the module's IPEX through a U.FL-to-SMA pigtail into the spectrum
   analyser or power meter (lab, **≥ 30 dB attenuator in front**: up to +20 dBm). Expected ~+2..+7 /
   +8..+13 / +14..+19 / ~+20 dBm (PA gain 20–25 dB, saturating near +20). Add the pigtail loss back. Write
   the gain into `E01_PA_GAIN_DB` (`phy_config.py`) and `p_pa_dbm` (`linkbudget.py`). Fixed channel:
   output + cable + antenna peak gain ≤ 10 dBm at −18. **D-R6:** `phy_config.py` then picks the highest
   step with output − 0.5 + 3 ≤ 20 dBm (−6 if the gain is ≤ 23.5 dB, else −12). Also log the supply
   current at each step (radio LDO budget). **Low battery:** repeat the highest legal step with the SP4's VCC at
   3.6, 3.3 and 3.0 V from the bench supply (3.0 V ≈ the radio rail at the cell's cutoff through the LDO). If the
   output drops > 2 dB at 3.0 V, raise the firmware low-battery threshold or switch to the buck-boost option
   (`HANDOFF_ET.md`, Power).
3. Clone check: the chip marking says nRF24L01P (Nordic), and the TX/RX current at the bench supply
   matches the E01 datasheet. A Si24R1 clone usually shows a different current and a weaker T2.
4. Two boxes 1 m apart, `TEAM_250K`, flex antennas fitted: 1 000 frames of 32 B. Pass: ≥ 999 received.

## T2 — Sensitivity / PER at 250 kbps (bench, conducted) — **gate for D-R2b before Quick Mode**

TX E01 → coax → lab step attenuator (≥ 100 dB total incl. fixed pads) → RX E01, both modules in
shielded boxes or far apart so nothing leaks around the attenuator.
1. Start at 60 dB, then add 2 dB steps; 1 000 frames per step; log PER.
2. Received level = output measured in T0 − attenuation − cable loss. The level where PER = 1 %
   is our sensitivity. Repeat at 1 Mbps (`TEAM_1M`).

Pass: PER ≤ 1 % at ≤ **−92 dBm** at 250 kbps (model uses −94; the LNA should give ~−96). If it is
worse than −90, suspect a clone or a bad module, and update `linkbudget.py` with the measured value.

## T4 — Range, open box (campus, line of sight)

Boxes on ~70 cm supports, `TEAM_250K`, Molex flex omni in each box (lid open).
Distances 10 / 70 / 150 / 260 m, 1 000 frames each, our channel.

| Distance | Model level | Margin (sensitivity −96 dBm) |
|---|---|---|
| 10 m | −56 dBm | +40 dB |
| 70 m | −70 dBm | +26 dB |
| 150 m | −83 dBm | +13 dB |
| 260 m | −93 dBm | +3 dB |

Pass: PER ≤ 1 % at 70 m and 150 m; at 260 m record the PER at 0.75 m and at 1.0 m antenna height
(the model says +5 dB for the extra 25 cm). Then one 2-minute file transfer at 70 m: pass if all
10 000 lines arrive (simulator: ~28 s at 5 % loss).

## T5 — Closed box and antenna placement

As T4 at 70 m and 260 m with the box closed. Compare: antenna at the top of the wall vs the middle,
box rotated 0 / 90 / 180° (omni pattern in the box, effect of the battery and PCB), box open vs closed.
Pass: closed-box PER ≤ 1 % at 260 m. If it fails, raise the antenna and re-check before anything else.

## T13 — Spectrum and e.i.r.p. (lab, spectrum analyser)

1. Carrier offset of each module (CW mode: `RF_SETUP` CONT_WAVE + PLL_LOCK): replaces the ±60 ppm
   assumption (`XTAL_PPM`).
2. 99 % occupied bandwidth at 250 kbps and 1 Mbps on RF_CH 82 (highest MRM channel). Pass: whole
   emission below 2483.5 MHz including the offset.
3. Conducted power (T0) + measured antenna gain (lab) → e.i.r.p. Pass: ≤ 10 dBm for the fixed-channel
   profiles, ≤ 20 dBm for `TEAM_FHSS` (D-R6). Put the plots in the ANNEX.

## T14 — Campus 2.4 GHz survey (Andrian) — **decides the D-R4 channel plan**

Firmware loop on one SP4 with its flex antenna at the SRI, MRM and NM sites, at the competition hour if
possible: for RF_CH 0..83, RX for 200 µs, read RPD (`nrf24_carrier`), 1 000 sweeps. Output: % busy
per channel. An SDR (HackRF) or the lab analyser gives the same picture with levels. Pass: each of
the four MRM channels and RF_CH 80 (NM) is busy < 5 % of the time; otherwise move the plan.

## T15 — MRM near-far (two of our boxes as the "other team")

Link at 260 m on RF_CH 74; a third box 2 m and 10 m from the receiver sends continuously on
RF_CH 82 (8 MHz away) and then RF_CH 49 (25 MHz away). Pass: PER of the 260 m link stays ≤ 1 % with
the interferer at 10 m on RF_CH 82 and at 2 m on RF_CH 49 (model: −50 / −60 dB selectivity vs
41 / 55 dB near-far).

## T16 — NM interop (with the other teams, see `NM_PHY_PROPOSAL.md`)

## T17 — CCA threshold: where does RPD trip? (lab, D-R6) — **gate for TEAM_FHSS outdoors**

The listen-before-talk check is the RPD bit, so its level at the SP4 antenna port decides whether we meet
EN 300 328 cl. 4.3.1.7.2 step 5 (−70 dBm/MHz at 20 dBm e.i.r.p., relaxed by 10·log(100 mW/P) below that,
corrected for the antenna gain).
1. Signal generator (or a second SP4 through the step attenuator of T2) into the receiving SP4's IPEX:
   a 250 kbps GFSK signal, then a CW tone, then a ~20 MHz wideband source (WiFi from a phone or the SG's
   noise mode) if available. Step 1 dB; at each step run `nrf24_cca()` 1 000 times.
2. Trip level = input where CCA reports busy ≥ 90 %. Expected ~−76 dBm (−64 dBm chip − ~12 dB LNA).
3. Pass: trip level (in dBm/MHz for the wideband source) ≤ the threshold `phy_config.py` prints for the
   chosen step (−64 dBm at −12, −68.5 dBm at 20 dBm e.i.r.p.). Write the LNA gain into `SP4_LNA_GAIN_DB`.
   If it fails at 20 dBm, keep the lower step (the threshold relaxes with power).

## T18 — Hopping behaviour on the spectrum analyser (lab, D-R6) — **gate for TEAM_FHSS outdoors**

`TEAM_FHSS` sender with a receiver following it, file transfer running.
1. Max-hold, 2400–2483.5 MHz: 27 channels visible, none within ±5 MHz of RF_CH 24/49/82, whole emission
   inside the band. Peak e.i.r.p. per T13.
2. Zero-span on one hop channel: dwell ≤ 25 ms, bursts ≤ 50 ms after each CCA, ≥ 2.5 ms idle before a re-CCA
   on the same channel; each channel revisited every ~0.68 s.
3. A CW interferer at −60 dBm on one hop channel: the sender skips that channel (no bursts on it) while the
   transfer goes on. Then a −35 dBm CW at 2395 MHz and at 2488.5 MHz (EN 300 328 table 2): CCA and link still
   work.
4. Pass: all of the above; record plots for the ANNEX and for the Atenea answer if the teachers want proof.

## Order

T0 → T2 (before QM) → T14 (survey) → T13 + T17 + T18 (one lab booking) → T4 with `TEAM_FHSS` (260 m model
+13.9 dB at RF_PWR −6, +8.4 dB at −12; `TEAM_250K` as the 10 mW reference) → T5 → T15 (with our hopping box
≥ 15 m from the "other team") → T16.
