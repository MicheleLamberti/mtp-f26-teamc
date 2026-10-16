# Questions for the Atenea forum

For Marcos to post as project leader. Draft 4-Oct-26 · Team C Radio Team.

1. **Allowed chips.** Are proprietary GFSK packet transceivers allowed, specifically the Nordic
   nRF24L01+ on the Ebyte E01-ML01SP4 module (with a PA/LNA)? Its Enhanced ShockBurst packet
   format is Nordic-proprietary, not a standard wireless protocol, and it has no Bluetooth.
2. *(Obsolete 9-Oct-26: all teams moved to 2.4 GHz, which has no duty-cycle limit. Do not post.)*
   **Duty cycle and the schedule.** In 869.40–869.65 MHz (CNAF UN-39) each transmitter is
   limited to 10 % of any hour (360 s). A 2-minute sending round uses ~115 s. How will the
   competition schedule SRI, MRM and NM rounds (and rehearsals) so that teams stay within that?
   Is the 10 % assessed per transmitter?
3. **2.4 GHz power: please confirm in writing the 20 dBm e.i.r.p. a professor approved for hopping
   radios (+10.5 dB on the 260 m link).** *Updated 16-Oct-26: a professor said yes orally; the rules say
   oral comments don't override the written rules, so we ask for it here. Please cc Prof. Anna Umbert
   (spectrum regulations).* We read CNAF UN-85 a) as allowing 100 mW e.i.r.p.
   for wideband data systems that follow EN 300 328, with 100 mW/100 kHz for frequency hopping and
   10 mW/MHz for other modulations, so a non-hopping narrowband radio like ours stays at ~10 mW.
   Our plan for SRI and MRM: the same Ebyte E01-ML01SP4 (nRF24L01P) as **adaptive FHSS with
   listen-before-talk** (EN 300 328 V2.2.2 cl. 4.3.1.7.2): 27 hop channels over 2402–2476 MHz (89 % of the
   band), 25 ms per hop, an energy-detect check (≥ 170 µs, threshold ≤ −70 dBm/MHz scaled to our power)
   before transmitting on each hop, busy channels skipped, ≤ 50 ms per channel occupancy, ≤ 20 dBm
   e.i.r.p. measured on the lab analyser. Network Mode stays on one channel at 10 mW (UN-85 b).
   (a) Please confirm that a student system designed and measured this way may use UN-85 a) at up to 20 dBm
   e.i.r.p.
   (b) What evidence do you want: analyser plots (power, hop pattern, dwell, skip of a busy channel),
   the design checks, or both? (c) Does this also apply to the other teams if they want it?
   Also: is the E01-ML01SP4 (Nordic nRF24L01P, proprietary Enhanced ShockBurst) fine under the
   standard-protocol ban (see Q1)?
4. **Support height.** Is the support fixed at 70 cm, or "about 70 cm" with some tolerance?
   May the antenna sit anywhere inside the box (e.g. under the lid)? May the box stand on its
   15 × 7 cm edge on the support (so a vertical antenna board can be taller)?
5. **Cooperation.** Is it acceptable for teams to agree a common NM physical layer and an MRM
   frequency split? Is sharing radio settings (not code) within the rules?
6. **USB access during setup.** The rules say the containers stay wrapped in aluminium foil while
   we download the file from the USB memory device. May we open the foil locally at the USB port
   to insert the stick? And may the stick be removed before Tx/Rx starts, with the file kept in
   on-board memory?
7. **Combined boards.** Does a board that carries both the microprocessor and the radio transceiver
   (e.g. Adafruit Feather RP2040 RFM69) count as the one allowed microprocessor module, or as a
   "single commercial module embedding the entire system"?
8. **Role switch.** The professor picks the transmitting device after the file has been loaded into
   both. May each device have a TX/RX role switch? It does not indicate network position.
9. **Encoding and output name.** Is "UNICODE .txt" UTF-8 or UTF-16? And what file name should the
   received file have on the USB stick (the original name, or a fixed one)?
10. *(Not needed since 13-Oct-26: we use one antenna per box. Do not post.)* **Two antennas.** Please confirm
    that a device may use two antennas inside the box.
