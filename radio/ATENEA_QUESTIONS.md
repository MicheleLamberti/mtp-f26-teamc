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
3. *(**Answered YES, 16-Oct-26:** 20 dBm e.i.r.p. confirmed for our hopping design (reported by Santiago).
   Do not post again. Kept for the record. Archive the written answer (link or screenshot) in the Drive folder.)* **2.4 GHz power: please confirm in writing the 20 dBm e.i.r.p. a
   professor approved for hopping radios (+10.5 dB on the 260 m link).** *A professor had said yes orally; the
   rules say oral comments don't override the written rules, so we asked here, cc Prof. Anna Umbert
   (spectrum regulations).* We read CNAF UN-85 a) as allowing 100 mW e.i.r.p.
   for wideband data systems that follow EN 300 328, with 100 mW/100 kHz for frequency hopping and
   10 mW/MHz for other modulations, so a non-hopping narrowband radio like ours stays at ~10 mW.
   Our plan for SRI and MRM: the same Ebyte E01-ML01SP4 (nRF24L01P) as **adaptive FHSS with
   listen-before-talk** (EN 300 328 V2.2.2 cl. 4.3.1.7.2): 40 hop channels over 2402–2480 MHz (94 % of the
   band), 30 ms per hop, an energy-detect check (≥ 170 µs, threshold ≤ −70 dBm/MHz scaled to our power)
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
11. **20 dBm without frequency hopping? (new 16-Oct-26)** Q3 confirmed 20 dBm e.i.r.p. for our hopping design. May
    we also transmit at up to 20 dBm e.i.r.p. on **one fixed channel** (nRF24, 250 kbps, occupied bandwidth
    ~0.6 MHz), with listen-before-talk before every ≤ 10 ms of transmission? We ask because EN 300 328 (and the EU
    SRD decision behind CNAF UN-85 a) limits non-hopping equipment to 10 mW/MHz, which such a narrow signal
    exceeds by 5–10 dB. If the answer is no, we stay with frequency hopping (already built and tested).

Added 16-Oct-26 after the project review:

12. **NM layout.** Approximate length of the South and East rims and spacing between nodes? May NM also use
    20 dBm with frequency hopping if all teams agree?
13. **MRM placement.** Minimum distance between different teams' boxes at each end? May teams choose positions?
14. **"Attacks".** What do they consist of (jamming, power cut, shielding, moving the box), and how long?
15. **Drop test.** Which device is dropped, what counts as a pass, and may it be repaired before MRM?
16. **Scoring.** Does the "first continuous range" of correct lines have to start at line 1? Do extra bytes after
    the last correct line disqualify the file?
17. **File details.** Which line terminator (CR, LF or CRLF)? Is the USB stick ours or provided by the professors?
18. **Quick Mode.** May a PC supply the file and receive it (Session #1 slide 15 says yes; the rules PDF is silent)?
19. **Cost category.** Is the IKEA box included in the unit cost? Does a lab-made breakout count €15? Is the ranking on
    the total with or without non-purchased items?
20. **MRM etiquette.** Must every team use listen-before-talk in MRM (relevant to Q3(c))?
21. **NM output.** Must every relay box also write the NM-file to USB after STOP, and under which file name?
