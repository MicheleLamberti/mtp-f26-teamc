# Radio test plan — nRF24L01+ / Ebyte E01-ML01SP4 + flex omni, 2.4 GHz

Version 0.5, 16-Oct-26 (v0.5: 20 dBm hopping is the SRI/MRM baseline; v0.4 added T0 all power steps, T17 CCA
threshold, T18 hopping;
v0.3 SP4 + omni; v0.2 the DP5 + patches; v0.1 the RFM69 at 868 MHz) · Owner: RT · Expected
values come from `linkbudget.py` (flat earth, worst-case ground bounce, antennas at 0.75 m,
−1 dB container, SP4 sensitivity −96 dBm at 250 kbps from the module datasheet).

No duty-cycle limit at 2.4 GHz: tests can be repeated freely. **Never exceed 10 dBm e.i.r.p. on a fixed
channel**: the driver only accepts RF_PWR −18 dBm for `TEAM_250K`, `TEAM_1M` and `NM_COMMON`. `TEAM_FHSS` (D-R6,
the SRI/MRM baseline, up to 20 dBm e.i.r.p. while hopping with LBT) goes outdoors once T0, T17 and T18 pass.

**The nRF24 has no RSSI.** It only has RPD, one bit that says "above −64 dBm at the chip" (about
−76 dBm at the E01 antenna port, through its ~12 dB LNA). So every range test measures **PER**
(frames lost out of frames sent), and levels come from the spectrum analyser or the model.

Record for every run: date, place, profile, RF_CH, distance, antenna, heights, box open/closed,
pad, frames sent/received.

## T0 — Bring-up and output power (bench, the day the modules arrive) — **gate for any field test**

1. Wire one SP4 (on its breakout) to the Raspberry Pi 3 (SPI0 + CSN = CE0 + CE GPIO 22 + IRQ GPIO 24; 3.3 V from the
   radio LDO, never the Pi's 3V3 pin, with ≥ 100 µF near the module); run
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
5. **Pi 3 checks (18-Oct, D-H1):**
   - Noise from the Pi in our band: with the SP4 in RX on the Pi, log RPD hits per hop channel (37 channels,
     10 000 samples each) with the Pi idle, under load (all four cores busy, SD writes, USB stick copy), HDMI off,
     WiFi/BT disabled and, if done, desoldered. Pass: no channel busier than the same test with the SP4 on a bench
     supply far from the Pi + 2 %. Drop any channel that fails from the hop set (`phy_config.py`).
   - The Pi's own current at 5 V and the cell current at 3.6 / 3.3 / 3.0 V through the 5.1 V boost (idle, radio TX
     bursts, stick copy, boot). Pass: the 5 V rail stays ≥ 4.75 V and `vcgencmd get_throttled` reports no undervoltage.

## T2 — Sensitivity / PER at 250 kbps (bench, conducted) — **gate for D-R2c before Quick Mode**

TX E01 → coax → lab step attenuator (≥ 100 dB total incl. fixed pads) → RX E01, both modules in
shielded boxes or far apart so nothing leaks around the attenuator.
1. Start at 60 dB, then add 2 dB steps; 1 000 frames per step; log PER.
2. Received level = output measured in T0 − attenuation − cable loss. The level where PER = 1 %
   is our sensitivity. Repeat at 1 Mbps (`TEAM_1M`).

Frames of 32 B. A +7 dBm module needs ~103 dB of isolation to the receiver: put the receiving module in a
shielded box (or a metal tin with the coax through it), or the PER curve measures leakage, not the attenuator.
Pass: PER ≤ 1 % at ≤ **−93 dBm** at 250 kbps (the conservative planning case: datasheet −96 "typical" at BER 0.1 %
+ 3 dB). If it is worse than −90, suspect a clone or a bad module. Write the measured 1 %-PER level into
`linkbudget.py` (`sens_dbm`) and drop `PLAN_SENS_DB` to 0.

On the Pi 3 (D-H1), also measure from the same runs: the gap between frames and the TX↔RX turnaround (logic
analyser on CE and IRQ). The model assumes 0.3 ms and 1 ms; 0.5 ms / 1 ms gives ~97 kbps, 1 ms / 2 ms ~73 kbps.
Write the values into `FRAMING` in `linkbudget.py` and the link timers in `proto/src/link.c`.

## T4 — Range, open box (campus, line of sight)

Boxes on ~70 cm supports, `TEAM_250K`, Molex flex omni in each box (lid open).
Distances 10 / 70 / 150 / 260 m, 1 000 frames each, our channel.

| Distance | Model level | Margin (sensitivity −96 dBm) |
|---|---|---|
| 10 m | −56 dBm | +40 dB |
| 70 m | −70 dBm | +26 dB |
| 150 m | −83 dBm | +13 dB |
| 260 m | −93 dBm | +3 dB |

PER ≤ 1 % alone does not say how much margin is left. **Measure attenuation to failure:** U.FL-jack-to-SMA
adapters and 3/6/10 dB SMA pads in the antenna feed, add pads until PER > 1 %; the pad value is the margin. Do it
at 8 azimuths of the box, and once with a person standing 1 m in front of the box.
Pass: ≥ 6 dB to failure at 70 m (10 mW, SRI) and at 260 m with `TEAM_FHSS` (MRM); record 0.75 m and 1.0 m antenna
height (the model says +5 dB for the extra 25 cm). Then one 2-minute file transfer at 70 m: pass if all 10 000
lines arrive (simulator: ~28 s at 5 % loss).

## T5 — Closed box and antenna placement

As T4 at 70 m and 260 m with the box closed. Compare: antenna at the top of the wall vs the middle,
box rotated 0 / 90 / 180° (omni pattern in the box, effect of the battery and PCB), box open vs closed.
Pass: closed-box margin to failure ≥ 6 dB at 260 m (pads as in T4), and the worst azimuth within 6 dB of the best.
If it fails, raise the antenna and re-check before anything else.

## T13 — Spectrum and e.i.r.p. (lab, spectrum analyser)

1. Carrier offset of each module (CW mode: `RF_SETUP` CONT_WAVE + PLL_LOCK): replaces the ±60 ppm
   assumption (`XTAL_PPM`).
2. 99 % occupied bandwidth at 250 kbps and 1 Mbps on RF_CH 82 (highest MRM channel). Pass: whole
   emission below 2483.5 MHz including the offset.
3. Conducted power (T0) + measured antenna gain (lab) → e.i.r.p. Pass: ≤ 10 dBm for the fixed-channel
   profiles, ≤ 20 dBm for `TEAM_FHSS` (D-R6). Put the plots in the ANNEX.
4. Option B only (`TEAM_20DBM_FIXED`): PSD in 1 MHz (EN 300 328 cl. 5.4.3). Expected = the e.i.r.p. (the whole
   < 1 MHz signal sits in one 1 MHz bin), i.e. 5–10 dB over the 10 dBm/MHz limit: record it for the Atenea Q11
   answer, and check the CCA every ≤ 10 ms in zero-span.

## T14 — Campus 2.4 GHz survey (Andrian) — WiFi load per channel and the NM channel

Use an SDR (HackRF) or the lab analyser at the SRI, MRM and NM sites, at the competition hour if possible: the
RPD bit only sees signals above ~-76 dBm at the port, while WiFi at ~-94 dBm in-channel already hurts an MRM link
received at ~-82 dBm. (An RPD sweep on one SP4 - RF_CH 0..83, 200 us each, 1 000 sweeps - is a quick first look.)
Output: % busy and level per channel. Pass: the NM channel RF_CH 77 busy < 5 % of the time (else propose another,
e.g. RF_CH 50); report the average busy share over the 37 hop channels (the simulator assumes 10 %) and, for the
fallback, over RF_CH 24/49/74/82. Note BLE advertising (2402/2426/2480 MHz) and any WiFi on channel 13.

## T15 — MRM near-far (our extra boxes as the "other teams")

The weak end is the **sender** (it listens for ACKs next to the other teams' senders, which transmit all the
time). Link at 260 m with `TEAM_FHSS`; two or three more boxes hopping at 20 dBm with continuous traffic (other
strides) stand 10 m and then 30 m from our sender. Measure ACK loss, POLLs and the 2-minute file time. Pass: all
10 000 lines in < 120 s at 10 m (simulator T14: 58 s with 5 % data / 30 % ACK loss; 115 s with 30 % loss both ways). For the fallback/option B: the
interferer on RF_CH 82 / 49 at 10 m / 2 m, PER ≤ 1 % (−50 / −60 dB selectivity).

## T16 — NM interop (with the other teams, see `NM_SPEC.md` §8)

Before the session: every team checks its code against the `NM_SPEC.md` §6 test vector (our sim does it, T18).
1. **By Fri 6-Nov (week 7):** one box per team in one room, all on `NM_COMMON` (RF_CH 77, 10 mW). Every box
   sends 1 000 NM frames to every other box at 10 m. Pass: ≥ 99 % received with a valid crc16 (count bad CRCs
   and frames from other files separately: they point at register or byte-order mistakes).
2. Same day: gossip run; one box starts with the test-vector file. Pass: every box writes an identical copy
   within 60 s. Record each box's relay log.
3. **Fri 20-Nov:** rehearsal along part of the South/East rims with all teams; note the box spacing that still
   works (the planning case gives −3.1 dB at 100 m, so the measured spacing decides).

## T17 — CCA threshold: where does RPD trip? (lab, D-R6) — **gate for TEAM_FHSS outdoors**

The listen-before-talk check is the RPD bit, so its level at the SP4 antenna port decides whether we meet
EN 300 328 cl. 4.3.1.7.2 step 5 (−70 dBm/MHz at 20 dBm e.i.r.p., relaxed by 10·log(100 mW/P) below that,
corrected for the antenna gain).
1. Signal generator (or a second SP4 through the step attenuator of T2) into the receiving SP4's IPEX:
   a 250 kbps GFSK signal, then a CW tone, then a ~20 MHz wideband source (WiFi from a phone or the SG's
   noise mode) if available. Step 1 dB; at each step run `nrf24_cca()` 1 000 times.
2. Trip level = input where CCA reports busy ≥ 90 %. Expected ~−76 dBm (−64 dBm chip − ~12 dB LNA).
   Test **every module that goes into a box** (the −64 dBm RPD threshold has no published tolerance, and the
   LNA gain varies). The driver reads RPD three times over ≥ 200 µs and treats any 1 as busy.
3. Pass: trip level (in dBm/MHz for the wideband source) ≤ the threshold `phy_config.py` prints for the
   chosen step (−64 dBm at −12, −68.5 dBm at 20 dBm e.i.r.p.). Write the LNA gain into `SP4_LNA_GAIN_DB`.
   If it fails at 20 dBm, keep the lower step (the threshold relaxes with power).

## T18 — Hopping behaviour on the spectrum analyser (lab, D-R6) — **gate for TEAM_FHSS outdoors**

`TEAM_FHSS` sender with a receiver following it, file transfer running.
1. Max-hold, 2400–2483.5 MHz: 40 channels visible (even RF_CH 2–80), whole emission
   inside the band. Peak e.i.r.p. per T13.
2. Zero-span on one hop channel: dwell ≤ 30 ms, bursts ≤ 50 ms after each CCA, ≥ 2.5 ms idle before a re-CCA
   on the same channel; each channel revisited every ~1.2 s.
3. A CW interferer at −60 dBm on one hop channel: the sender skips that channel (no bursts on it) while the
   transfer goes on. Then a −35 dBm CW at 2395 MHz and at 2488.5 MHz (EN 300 328 table 2): CCA and link still
   work.
4. EN 300 328 items not covered elsewhere (review 16-Oct), at the highest legal power step:
   - out-of-band mask at the hop-set edges (RF_CH 4 and 78) at full power;
   - spurious/harmonics, radiated (the Molex omni is a 2.4/5 GHz dual-band antenna, so the 2nd harmonic at
     ~4.9 GHz may radiate well): ≤ −30 dBm e.i.r.p. per MHz;
   - receiver blocking (category 1): link PER ≤ 10 % with a CW at −53 dBm at 2380 / 2504 MHz and −47 dBm in
     2300–2674 MHz outside the band (the SP4's LNA likely has no SAW filter);
   - output power per module at 3.6 V supply (the PA gain rises with VCC).
5. Pass: all of the above; record plots for the ANNEX and for the Atenea answer if the teachers want proof.

## Order

T0 → T2 (before QM) → T14 (survey) → T13 + T17 + T18 (one lab booking) → T4 with `TEAM_FHSS` (260 m model
+13.9 dB at RF_PWR −6, +8.4 dB at −12; `TEAM_250K` as the 10 mW reference) → T5 → T15 (with our hopping box
hopping at 20 dBm too, 10 m from ours) → T16. **Go/no-go for hopping in MRM: Fri 20-Nov** (T17, T18 and a
260 m transfer with `TEAM_FHSS` passed); otherwise MRM runs `TEAM_250K`. SRI runs `TEAM_250K` in any case.
