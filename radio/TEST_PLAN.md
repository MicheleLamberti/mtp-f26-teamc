# Radio test plan — nRF24L01+ / Ebyte E01-ML01SP4 + flex omni, 2.4 GHz

Version 0.3, 13-Oct-26 (v0.2 assumed the DP5 + patches; v0.1 the RFM69 at 868 MHz) · Owner: RT · Expected
values come from `linkbudget.py` (flat earth, worst-case ground bounce, antennas at 0.75 m,
−1 dB container, chip sensitivity −94 dBm at 250 kbps).

No duty-cycle limit at 2.4 GHz: tests can be repeated freely. **Never exceed 10 dBm e.i.r.p.**:
the driver only accepts RF_PWR −18 dBm (`TEAM_250K`, `TEAM_1M`, `NM_COMMON` profiles).

**The nRF24 has no RSSI.** It only has RPD, one bit that says "above −64 dBm at the chip" (about
−76 dBm at the E01 antenna port, through its ~12 dB LNA). So every range test measures **PER**
(frames lost out of frames sent), and levels come from the spectrum analyser or the model.

Record for every run: date, place, profile, RF_CH, distance, antenna, heights, box open/closed,
pad, frames sent/received.

## T0 — Bring-up and output power (bench, the day the modules arrive) — **gate for any field test**

1. Wire one SP4 (on its breakout) to the Pico (SPI + CSN + CE, 3.3 V with ≥ 100 µF near the module); run
   `nrf24_init`. Pass: `NRF24_OK`. `NRF24_ERR_SPI` = wiring/CSN; `NRF24_ERR_NOT_PLUS` = an old
   nRF24L01 (no 250 kbps), return it.
2. **Conducted output power** at RF_PWR −18 dBm (a test build may unlock −12 for this step only), the
   module's IPEX through a U.FL-to-SMA pigtail into the spectrum analyser or
   power meter (lab, ≥ 20 dB attenuator in front if the instrument needs it). Expected ~+7 /
   ~+13 dBm (estimate; could be ~5 dB lower if the PA gain is 20 dB). Add the pigtail loss back. Write the
   value into `E01_PA_GAIN_DB` (`phy_config.py`) and `p_pa_dbm`
   (`linkbudget.py`), then pick the pad so that output + cable + pad + antenna gain ≤ 10 dBm.
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
3. Conducted power (T0) + measured antenna gain (lab) → e.i.r.p. Pass: ≤ 10 dBm. Put the plot in the ANNEX.

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

## Order

T0 → T2 (before QM) → T14 (survey) → T4 → T13 (book the lab) → T5 → T15 → T16.
