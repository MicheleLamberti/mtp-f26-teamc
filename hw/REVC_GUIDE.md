# Carrier rev C ("simple") — build and test guide

Team C, MTP F26 · 24-Oct-26 · DRAFT for the first build. For someone who can solder through-hole parts but is not an
electronics specialist. Files: `hw/teamc-carrier-simple/` (schematic PDF, `fab/` for the lab, assembly drawings),
parts list `hw/BOM_revC.csv`, shopping list `hw/REVC_SHOPPING.md`, design decisions
`hw/teamc-carrier-simple/CONCEPT.md`.

**Golden rule: measure before you plug.** The Pi and the radio breakout go on last, only after every test point
shows the right voltage.

## 1. What is on the board (one sentence per block)

| Block | Parts | What it does |
|---|---|---|
| Cell | BT1 holder + one **protected** 18650 | The battery sits in a holder soldered on the board; no battery cable to get wrong. |
| Fuse | F1: 4 A fast 5×20 mm fuse in two clips | Blows on a short or a reversed cell. You pull it out and push a new one in by hand (keep the spare in the box). |
| Reversed-cell guard | D1 (1N5822, big black diode) | Does nothing normally. If the cell goes in backwards, D1 shorts it so the fuse blows before anything else sees a negative voltage. |
| 5 V for the Pi | U2, Pololu U3V70F5 module | Turns the cell's 3.0–4.2 V into 5 V. Its ENABLE pin is wired to the panel power toggle. |
| One-way valve | U3, Pololu ideal diode #5388 | Lets 5 V go from the boost to the Pi but never back (if someone plugs the Pi's micro-USB while the box is on). |
| 3.3 V for the radio | U4 MCP1700 (3-leg regulator) + C11, C12 | Turns the 5 V into a clean 3.3 V for the radio only. Never powered from the Pi's own 3.3 V pin. |
| Battery level | U6, Adafruit MAX17048 #5580 | Tells the Pi the cell's charge over I2C (address 0x36). |
| Pi link | J1 (2×20 box header) + 40-wire ribbon | Carries 5 V, ground and every signal to the Pi. Keyed: it only goes in one way. |
| Radio | J30 (1×8 socket) + H30 standoff | The lab-made SP4 radio breakout plugs in here and sits ~11 mm above the board. R82–R84 (33 Ω) soften the SPI edges; R80 keeps the radio deselected while the Pi boots. |
| Panel leads | J10 (GO/STOP), J11 (role), J12 (mode), J14 (LEDs), J22 (power toggle), J23 (charger) | 2- and 3-pin JST-XH plugs for everything on the box wall. |
| Panel protection | D12–D16 (P4KE10A, small standing diodes) + R54–R57, R9 (1 kΩ) | A static zap on a metal lever goes into the diode at the connector, and the 1 kΩ limits what reaches the Pi. |
| LEDs | R60, R61 (330 Ω) | Current limit for the two panel LEDs. |
| Bench | J13 (UART: 1 GND, 2 TX from the Pi, 3 RX into the Pi), TP1–TP4 | Serial console and the four points where you clip the multimeter. |
| Wire links | W1–W4 | Four short insulated wires on the component side where one copper layer cannot cross (three ground, one radio IRQ). |

The software needs no change: same GPIOs as rev A/B (CE 22, CSN 8, IRQ 24, SPI 9/10/11, I2C 2/3, GO/STOP 17,
role 27, mode NM 23 / MRM 16, LEDs 5/6, UART 14/15). The Pi's internal pull-ups (turned on by `ui.c`) hold the
panel inputs high; there are no pull-up resistors on the board.

## 2. The board itself

- **120 × 68 mm, one copper layer**, milled at the UPC lab: no plated holes, no solder mask, no silkscreen.
- **Every part sits on the plain (component) side and is soldered on the copper side.** Use the assembly drawing
  `fab/teamc-carrier-simple_assembly_component_side.pdf` to place parts (it is drawn as you see the component side);
  `..._assembly_copper_side.pdf` is the view while soldering.
- Pin 1 of every connector and IC is the **square pad**.
- **Holes are not plated.** A pin is connected only by the solder on the copper side. After soldering, check that
  every joint wets both the pin and the copper ring.
- Two slots and a notch next to the cell holder take a cable tie over the cell (drop test).

### Places that look odd but are intended
- Some tracks pass **between the two legs of a resistor** on the copper side (SCK under R84/R83, LED_ACT_A under R61,
  CSN and IRQ under R57, the role line under R54/R55). The resistor body is on the other side, so nothing touches.
  Just keep each joint small so it does not reach the track running past it.
- Three ground areas and the radio's IRQ line meet only through the **wire links W1–W4**. Without them the board
  does not work (ground missing on part of the board, or no radio interrupt).

## 3. Soldering order (low parts first, tall parts last)

Work from the assembly drawing; tick each reference off.

1. **Wire links W1–W4.** Insulated 22 AWG solid wire, ends stripped ~3 mm, laid flat on the component side
   between its two holes, soldered on the copper side. Lengths (cut the wire to this, hole-to-hole + 2 × 5.5 mm):
   W1 GND 4.0 mm (cut 15 mm), W2 GND 7.2 mm (18 mm), W3 GND 6.0 mm (17 mm), **W4 RADIO_IRQ 5.7 mm (17 mm)**.
   Positions: `fab/wire_links.csv`. A dab of glue keeps each one flat.
2. **Test loops TP2, TP3, TP4.** Bend ~1.5 cm of bare tinned wire into a small loop, push both ends into the one
   hole, solder. Keep them low (~5 mm): **TP2 and TP4 sit under the radio breakout**, which is only ~11 mm up.
3. **Resistors** (axial, any direction): 33 Ω R82, R83, R84; 10 kΩ R80; 1 kΩ R9, R54, R55, R56, R57;
   330 Ω R60, R61. Lie them flat on the board.
4. **TVS diodes D12–D16 (P4KE10A).** They stand upright. **The band (cathode) goes to the square pad**, i.e. the
   bent-over lead goes into the square pad and the body stands on the round pad (that is the GND side). Same for
   all five. A reversed TVS shorts the line to ground: the panel input reads "pressed" all the time.
5. **D1 (1N5822)**: lies flat; **band to the square pad** (VBAT side). Reversed, it shorts the cell and blows the fuse
   the first time you insert the cell.
6. **Capacitors**: C10, C18 (100 nF) and C11, C12 (1 µF) have no polarity; push C11 and C12 right down (they sit
   under the breakout, keep them under ~7 mm). **C1 and C9 (100 µF electrolytic) are
   polarised: the long leg (+) goes into the square pad**, the stripe on the can marks −.
7. **U4 MCP1700 (TO-92, 3 legs).** Look at the flat face with the legs down: **left = 1 GND, middle = 2 VIN (5 V),
   right = 3 VOUT (3.3 V)**. Pad 1 is the square pad. Match the flat side to the outline on the assembly drawing.
   Push it down so it is no taller than ~8 mm (it sits under the breakout).
8. **Fuse clips F1** (two pairs). The little end-stops of each clip face outward, so the fuse is held between them.
   Fit the fuse when you reach test B in section 4 (the holder feeds the board only through it).
9. **JST-XH headers** J10, J11, J12, J14, J22, J23 (latch side as on the assembly drawing), **J13** (3 pins cut from
   the male strip), **J30** (1×8 socket for the breakout).
10. **J1 box header**: the key notch as on the assembly drawing. Pin 1 is the square pad.
11. **Modules U2, U3, U6** on male header pins: put the pins in the module, plug the module into the board, solder
    the board side, then the module side. Before fitting **U6 (Adafruit #5580)**, see the SJ2 check in section 4.
12. **TP1** (red Keystone test point, outside the breakout area) and **BT1 cell holder** last (it is big and covers
    the area of several tracks). Check the + mark of the holder against the assembly drawing: **+ is the end next to
    the fuse clips**.
13. Nylon standoffs: M3 × 10 mm at MH1–MH3 (board to the box floor), **M3 × 11 mm at H30 for the breakout**.

## 4. Tests before plugging in the Pi and the radio

You need a multimeter; a bench supply with a current limit makes it safer.

**A. Before any power (multimeter on resistance / beep):**
1. **Ground continuity** (the lab board has no plated holes, so check it by hand): TP3 (GND) to each of J1's eight
   GND pins (6, 9, 14, 20, 25, 30, 34, 39), to J30 pin 1, to J13 pin 1, to the − end of BT1, to pin 2 of J10, J11, J12, J22, J23 and to pin 3
   of J14 — all must beep.
2. **No shorts:** TP1 (VBAT), TP2 (5 V) and TP4 (3.3 V) to TP3 (GND) must **not** beep (with the electrolytics the
   reading climbs for a second; that is fine).
3. **The panel inputs are not shorted** by a reversed TVS: J10 pin 1, J11 pin 1, J12 pins 1 and 3 and J22 pin 1 to
   GND must not beep.
4. **Fuel gauge jumper SJ2** on the Adafruit #5580 (do this before soldering U6, or with the module unplugged): its
   chip must run from the cell. Measure between the **centre pad of SJ2 and the BAT pad**: it must beep. If it does
   not (the board file shows SJ2 open), bridge the centre pad to the BAT side with a blob of solder. (Use the
   jumper's name as printed on the module; Adafruit's product page does not describe it.)

**B. First power, toggle OFF** (the power toggle J22 closed; or a wire across J22's two pins). **Fit the fuse in F1
now.** Best: a bench supply at 3.7 V (never above 5 V), current limit 0.3 A, clipped to the two ends of the holder
(+ to the + end). Otherwise insert the cell.
5. Current drawn with the box OFF: **expect about 0.05–0.3 mA** (the boost's 100 kΩ pull-up ~40 µA + the gauge
   ~23 µA + the boost asleep + D1's leakage; none of these is a guaranteed datasheet figure). **This is the 1N5822
   leakage check**: above ~0.5 mA, lift one leg of D1 and measure again; a leaky D1 slowly drains the cell in the box.
6. TP1 = the cell voltage; TP2 ≈ 0 V (boost asleep); TP4 ≈ 0 V.

**C. Toggle ON** (open the toggle / remove the wire), still without the Pi and the breakout:
7. **TP2 (5V_PI): 4.8–5.2 V.**
8. **TP4 (3V3_RADIO): 3.2–3.4 V.** Never above 3.6 V (the radio's limit).
9. Current: a few mA. If the supply hits its limit or something gets warm, switch off and look for a short.

**D. Optional — reversed cell (only with a current-limited bench supply, 0.3 A, never with a real cell; fuse
fitted):** connect the supply backwards to the holder. The voltage should collapse to about −0.4 V (D1 conducting), the supply sits at
its limit, nothing else warms up. With a real cell this current is what blows F1.

**E. Breakout:** switch OFF, plug the SP4 breakout into J30 (its pin 1 = GND on the square pad end) and screw it to
the H30 standoff. Switch ON: TP4 still 3.2–3.4 V. Switch OFF.

**F. Pi:** with the box OFF, connect the ribbon: **red wire = pin 1 at both ends**; on the Pi, pin 1 is the end of
the GPIO header nearest the microSD slot. Switch ON. The Pi boots. Then on the Pi:
- `vcgencmd get_throttled` → `throttled=0x0` (no under-voltage). If not 0x0, measure 5 V at the Pi's pin 2 under load:
  it must stay ≥ 4.75 V.
- `i2cdetect -y 1` shows **36** (fuel gauge).
- `nrf24_probe init` (see `radio/fw/linux/README.md`) finds the radio.
- Press GO/STOP, flip the role and mode toggles: `teamc-node`'s UI test or `gpioget` sees the lines go low.

## 5. Using the box

- **Power toggle: lever DOWN = OFF.** The toggle only tells the boost to sleep; the battery current never goes
  through it. If its lead breaks, the box **stays on** (on purpose: a broken lead in the drop test must not stop the
  run). Before mounting the toggle, check with the meter which two lugs beep with the lever **down**, and wire those
  two to the J22 lead.
- **Charging:** switch the box **OFF**, then plug a **USB-A-to-USB-C** cable into the charger at the box wall (many
  of these TP4056 boards lack the USB-C resistors, so a C-to-C cable gives no power). Red LED = charging, the other
  LED = full (~3.5 h from empty at 1 A).
- Never plug the Pi's own micro-USB while the box is on (the ideal diode protects the boost, but do not rely on it).
- Strap the cell: a cable tie through the slot and the notch, over the cell. Glue the JST housings and the U.FL
  antenna plug, tape the microSD, for the drop test.
- Spare fuse: 5×20 mm, 4 A **fast** (F4A). If the box is dead, check the fuse first (TP1 shows the cell, but the
  boost sees nothing → fuse).

## 6. Common mistakes (and what you see)

| Mistake | Symptom |
|---|---|
| Cell in backwards | Fuse blows at once (that is what D1 is for). Replace the fuse, turn the cell round. |
| D1 or a TVS soldered backwards | D1: fuse blows as soon as the cell goes in. TVS: that panel input always reads "pressed" (D12–D15); D16 reversed holds ENABLE near 0.6 V, an undefined level: the box may be on, off or flaky. |
| Electrolytic C1/C9 reversed | It gets hot or bulges. Replace it the right way round. |
| MCP1700 turned round | TP4 anything but 3.2–3.4 V (it can even pass 5 V through). **Hard rule: never plug the breakout unless TP4 reads 3.2–3.4 V.** |
| A wire link missing | W4: the radio never raises its interrupt (sends time out). W1–W3: odd faults on part of the board; the continuity check in step A1 catches it. |
| Ribbon rotated or offset by one row | The key on J1 prevents rotation at the board; at the Pi, check red = pin 1 (microSD end). |
| A joint that only touches the pin | Unplated holes: no connection at all. Reflow with a little more solder so it wets the copper ring. |
| SJ2 left open on the #5580 | The gauge reads nothing or 0 % (its chip has no supply). |
| Test loop or regulator too tall | The breakout does not seat on its standoff. Bend the loop lower / push U4 down. |
| Box "off" but the cell drains | D1 leakage (step 5), or the toggle wired to the wrong lugs (lever down = open = ON). |
| Charging with a C-to-C cable | Nothing happens. Use USB-A to USB-C. |
