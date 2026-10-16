"""MTP-F26 Team C - nRF24L01+ (Ebyte E01-ML01SP4) physical-layer profiles and register generator.

Turns the radio decisions (D-R1b band, D-R2c module, D-R4 channel plan, D-R5c antenna, D-R6
FHSS; see radio/DECISIONS.md) into nRF24L01+ register values, checks them against CNAF UN-85 b)
(2400-2483.5 MHz, 10 mW e.i.r.p.), UN-85 a) + ETSI EN 300 328 V2.2.2 for the adaptive-FHSS profile
(100 mW e.i.r.p.) and the nRF24L01+ Product Specification v1.0, and writes radio/fw/nrf24_config.h.

Register facts (nRF24L01+ PS v1.0):
    f       = 2400 + RF_CH MHz                     RF_CH 0..125; only 0..83 are legal in Spain
    RF_SETUP  RF_DR_LOW (bit 5) / RF_DR_HIGH (bit 3): 250 kbps = 10, 1 Mbps = 00, 2 Mbps = 01
              RF_PWR (bits 2:1): -18 / -12 / -6 / 0 dBm at the chip
    Frame   = 1 B preamble + 3..5 B address + 9-bit packet control field + 0..32 B payload + 1..2 B CRC
    Dynamic payload length (DYNPD/FEATURE.EN_DPL) needs ENAA on the pipe, so ENAA_P0 is on,
    retries are 0 and every frame goes out with W_TX_PAYLOAD_NOACK (FEATURE.EN_DYN_ACK):
    no Enhanced-ShockBurst ACKs on air, our own ARQ (proto/src/link.c) does the job.

Module (Ebyte E01-ML01SP4): PA after the chip, always in line; datasheet max +20 dBm. Its gain is
20-25 dB [ESTIMATE], so RF_PWR -18 dBm gives +2..+7 dBm at the IPEX. The checks use 25 dB (worst case
for the e.i.r.p. limit). Test T0 replaces E01_PA_GAIN_DB with a measurement. Every fixed-channel
profile is held at RF_PWR -18 dBm and the driver refuses anything higher (NRF24_RF_PWR_MAX_BITS): at
0 dBm the module would radiate ~+23 dBm e.i.r.p., 20x the limit.

D-R6 (baseline since 16-Oct-26, a professor approved 20 dBm e.i.r.p.): TEAM_FHSS, the SRI/MRM profile, hops
over FHSS_HOPSET with listen-before-talk
(EN 300 328 cl. 4.3.1.7.2, adaptive FHSS using LBT), which UN-85 a) allows 100 mW e.i.r.p. The driver
lets only an LBT profile go above -18 dBm (NRF24_RF_PWR_MAX_BITS_FHSS, the highest RF_PWR step whose
worst-case e.i.r.p. is <= 20 dBm), and refuses to transmit without a clear CCA on the current hop.
NM keeps the fixed-channel profile under UN-85 b); TEAM_250K stays for Quick Mode, the bench and as the fallback.

Occupied bandwidth uses Carson's rule 2 (fdev + BR/2) with the datasheet deviation
(160 kHz at 250 kbps/1 Mbps, 320 kHz at 2 Mbps); the bench spectrum test T13 replaces it.

Run:  python3 radio/phy_config.py           (report + regenerate the header)
"""

from __future__ import annotations

import math

from dataclasses import dataclass, field
from pathlib import Path

from linkbudget import MRM_CHANNELS, NRF24_CI_250K

BAND = (2400.0e6, 2483.5e6)   # CNAF UN-85 a) and b)
EIRP_MAX_DBM = 10.0           # 10 mW e.i.r.p., UN-85 b) (fixed channel)
EIRP_MAX_FHSS_DBM = 20.0      # 100 mW e.i.r.p., UN-85 a) FHSS (100 mW/100 kHz) - D-R6 baseline
XTAL_PPM = 60.0               # nRF24L01+ crystal requirement: +-60 ppm per box
E01_PA_GAIN_DB = 25.0         # module PA after the chip [ESTIMATE 20-25 dB, measure in T0]
E01_PSAT_DBM = 20.0           # module saturates around +20 dBm
MAX_PAYLOAD = 32

MAX_CHIP_DBM = -18            # hard limit for fixed-channel profiles: the driver refuses higher RF_PWR

# --- D-R6 baseline (SRI/MRM): adaptive FHSS + LBT (ETSI EN 300 328 V2.2.2, clause numbers in the checks) ----------
SP4_LNA_GAIN_DB = 12.0        # module LNA ahead of the chip [ESTIMATE; T17 measures the RPD trip level]
RPD_CHIP_DBM = -64.0          # nRF24L01+ received power detector threshold at the chip (PS v1.0)
FHSS_SELF_CH = 74             # our fixed MRM channel (TEAM_CH below), given up when we hop
# Since 16-Oct every team uses 20 dBm e.i.r.p., which a narrowband radio may only do while hopping (UN-85 a), so
# the other teams hop too: no fixed MRM channels left to avoid. MRM sharing = LBT + >= 10 m between boxes.
FHSS_OTHERS: list[int] = []   # fixed channels of other teams to keep clear of (none now)
FHSS_GUARD_MHZ = 5            # skip RF_CH within +-5 MHz of another team (nearest hop >= 6 MHz: C/I <= -50 dB)
FHSS_STRIDE = 7               # hop order = sorted set taken with this index stride (consecutive hops >= 14 MHz)
FHSS_SLOT_US = 25_000         # dwell per hop: one 16-frame SR-ARQ window (~22 ms) + guard
FHSS_COT_US = 50_000          # max TX time after one CCA (cl. 4.3.1.7.2 step 3: < 60 ms)
FHSS_IDLE_US = 2_500          # idle before re-CCA on the same channel (>= 5 % of COT, >= 100 us)
FHSS_CCA_US = 170             # RX time before RPD is valid (PS v1.0) = CCA observation time
N_MIN_FHSS = 15               # cl. 4.3.1.4.3.2: N >= max(15, 15 MHz / min separation)


def _hopset() -> list[int]:
    return [ch for ch in range(2, 81, 2) if all(abs(ch - x) > FHSS_GUARD_MHZ for x in FHSS_OTHERS)]


FHSS_HOPSET = _hopset()
FHSS_HOPSEQ = [FHSS_HOPSET[(i * FHSS_STRIDE) % len(FHSS_HOPSET)] for i in range(len(FHSS_HOPSET))]


def max_chip_dbm_for(eirp_max: float) -> int:
    """Highest RF_PWR step whose worst-case (PA gain 25 dB, omni 3 dBi peak) e.i.r.p. fits."""
    g, cable, pad = ANTENNAS["omni"]
    ok = [c for c in RF_PWR if min(c + E01_PA_GAIN_DB, E01_PSAT_DBM) + cable + pad + g <= eirp_max]
    return max(ok)

# Antenna path (D-R5c): gain dBi, cable/connector dB, pad dB. Same path for TX and RX. The e.i.r.p.
# check uses the datasheet PEAK gain (worst case); linkbudget.py uses 2 dBi for the antenna in the box.
ANTENNAS = {
    "omni": (3.0, -0.5, 0.0),     # Molex 146153-0100 flex dipole (2.4-3.0 dBi), 10 cm cable, IPEX on the SP4
}

RATES = {250_000: 0b100000, 1_000_000: 0b000000, 2_000_000: 0b001000}
FDEV = {250_000: 160e3, 1_000_000: 160e3, 2_000_000: 320e3}
RF_PWR = {-18: 0b00, -12: 0b01, -6: 0b10, 0: 0b11}
MAX_CHIP_DBM_FHSS = max_chip_dbm_for(EIRP_MAX_FHSS_DBM)   # -12 until T0 measures the PA gain

REG = dict(CONFIG=0x00, EN_AA=0x01, EN_RXADDR=0x02, SETUP_AW=0x03, SETUP_RETR=0x04, RF_CH=0x05,
           RF_SETUP=0x06, STATUS=0x07, RX_PW_P0=0x11, DYNPD=0x1C, FEATURE=0x1D)

TEAM_CH = FHSS_SELF_CH  # our MRM/SRI channel: proposal, final after the inter-team meeting (D-R4)
NM_CH = 80            # NM common channel: proposal for the other teams (NM_PHY_PROPOSAL.md)
TEAM_ADDR = bytes([0xE7, 0xC3, 0x1A, 0x5D, 0x92])   # 5 B pipe address: no 0x00/0xFF/0x55/0xAA runs
NM_ADDR = bytes([0xC2, 0x5A, 0x9D, 0x3E, 0x71])     # shared by all teams in NM


@dataclass
class Profile:
    name: str
    purpose: str
    rf_ch: int
    bitrate: int = 250_000
    chip_dbm: int = -18
    address: bytes = TEAM_ADDR
    antenna: str = "omni"
    crc_bytes: int = 2
    plan: list[int] = field(default_factory=lambda: list(MRM_CHANNELS))
    lbt: bool = False     # adaptive FHSS + LBT profile (UN-85 a), D-R6)

    @property
    def eirp_max(self) -> float:
        return EIRP_MAX_FHSS_DBM if self.lbt else EIRP_MAX_DBM

    @property
    def chip_cap(self) -> int:
        return MAX_CHIP_DBM_FHSS if self.lbt else MAX_CHIP_DBM

    @property
    def f(self) -> float:
        return 2400e6 + self.rf_ch * 1e6

    @property
    def obw(self) -> float:
        return 2 * (FDEV[self.bitrate] + self.bitrate / 2)

    @property
    def drift(self) -> float:
        return self.f * XTAL_PPM * 1e-6

    @property
    def conducted_dbm(self) -> float:
        return min(self.chip_dbm + E01_PA_GAIN_DB, E01_PSAT_DBM)

    @property
    def eirp_dbm(self) -> float:
        g, cable, pad = ANTENNAS[self.antenna]
        return self.conducted_dbm + cable + pad + g

    def airtime_us(self, payload: int) -> float:
        bits = (1 + len(self.address) + payload + self.crc_bytes) * 8 + 9
        return bits / self.bitrate * 1e6

    # --- checks -----------------------------------------------------------
    def checks(self) -> list[tuple[str, bool, str]]:
        chans = FHSS_HOPSET if self.lbt else [self.rf_ch]
        lo = 2400e6 + min(chans) * 1e6 - self.obw / 2 - self.drift
        hi = 2400e6 + max(chans) * 1e6 + self.obw / 2 + self.drift
        out = [
            ("RF_CH 0..83 (2400-2483 MHz)", all(0 <= c <= 83 for c in chans),
             f"RF_CH {min(chans)}..{max(chans)}" if self.lbt else f"RF_CH {self.rf_ch} = {self.f / 1e6:.0f} MHz"),
            (f"emission inside {BAND[0] / 1e6:.1f}-{BAND[1] / 1e6:.1f} MHz incl. drift", lo >= BAND[0] and hi <= BAND[1],
             f"{lo / 1e6:.3f}-{hi / 1e6:.3f} MHz, guard {min(lo - BAND[0], BAND[1] - hi) / 1e3:.0f} kHz"),
            (f"e.i.r.p. <= {self.eirp_max:.0f} dBm ({self.antenna}, UN-85 {'a' if self.lbt else 'b'})",
             self.eirp_dbm <= self.eirp_max,
             f"<= {self.conducted_dbm:+.1f} dBm at the IPEX -> <= {self.eirp_dbm:.1f} dBm e.i.r.p."),
            ("RF_PWR is a chip setting", self.chip_dbm in RF_PWR, f"{self.chip_dbm} dBm"),
            (f"RF_PWR <= {self.chip_cap} dBm (driver hard limit{', LBT profile' if self.lbt else ''})",
             self.chip_dbm <= self.chip_cap, f"{self.chip_dbm} dBm"),
            ("5 B address, no 0x00/0xFF/0x55/0xAA first byte", len(self.address) == 5
             and self.address[0] not in (0x00, 0xFF, 0x55, 0xAA), self.address.hex(" ").upper()),
            ("CRC-16 in hardware", self.crc_bytes == 2, f"{self.crc_bytes} B"),
        ]
        if not self.lbt:
            spacing = min(b - a for a, b in zip(sorted(self.plan), sorted(self.plan)[1:]))
            out.append(("MRM plan: neighbours >= 6 MHz apart (C/I <= -50 dB)", spacing >= 6,
                        f"RF_CH {self.plan}, min {spacing} MHz -> {NRF24_CI_250K[6 if spacing < 25 else 25]} dB"))
        else:
            out += self.fhss_checks()
        return out

    def fhss_checks(self) -> list[tuple[str, bool, str]]:
        """ETSI EN 300 328 V2.2.2, adaptive FHSS using LBT (clause 4.3.1)."""
        hs, u = sorted(FHSS_HOPSET), len(FHSS_HOPSET)
        sep_mhz = min(b - a for a, b in zip(hs, hs[1:]))
        n_min = max(N_MIN_FHSS, 15 / sep_mhz)
        span = (hs[-1] - hs[0]) * 1e6 + self.obw
        band = BAND[1] - BAND[0]
        acc_ms = 400 * N_MIN_FHSS / u                  # TX time per freq in the 400 ms x N window, 100 % duty
        seq_step = min(min(abs(a - b) for a, b in zip(FHSS_HOPSEQ, FHSS_HOPSEQ[1:] + FHSS_HOPSEQ[:1])), 99)
        others = min((abs(c - x) for c in hs for x in FHSS_OTHERS), default=99)
        g, cable, _ = ANTENNAS[self.antenna]
        p_mw = 10 ** (self.eirp_dbm / 10)
        tl = -70 + 10 * math.log10(100 / min(p_mw, 100))   # dBm/MHz at a 0 dBi antenna
        tl_port = tl + (g - 1.0) + cable                # corrected for the in-box gain (2 dBi, strict) + cable
        rpd_port = RPD_CHIP_DBM - SP4_LNA_GAIN_DB
        return [
            ("4.3.1.2 FHSS RF output power <= 20 dBm e.i.r.p.", self.eirp_dbm <= 20.0, f"{self.eirp_dbm:.1f} dBm"),
            ("4.3.1.4.3.2 hop set N >= max(15, 15 MHz/sep)", u >= n_min and set(FHSS_HOPSEQ) == set(hs),
             f"{u} channels, min sep {sep_mhz} MHz (N_min {n_min:.0f}); sequence visits each once per cycle"),
            ("4.3.1.4.3.2 operates over >= 70 % of the band", span >= 0.7 * band,
             f"{span / 1e6:.1f} MHz of {band / 1e6:.1f} MHz ({span / band * 100:.0f} %)"),
            ("4.3.1.4.3.2 accumulated TX <= 400 ms per 400 ms x N", acc_ms <= 400,
             f"<= {acc_ms:.0f} ms at 100 % duty ({u} channels, {FHSS_SLOT_US / 1e3:.0f} ms slots)"),
            ("4.3.1.4.3.2 occupation: each freq within 4 x dwell x U", u * FHSS_SLOT_US <= 4 * FHSS_SLOT_US * u,
             f"cycle {u * FHSS_SLOT_US / 1e6:.3f} s"),
            ("4.3.1.5.3 hop separation >= 100 kHz (and >= OBW)", sep_mhz * 1e6 >= max(100e3, self.obw),
             f"{sep_mhz} MHz vs OBW {self.obw / 1e3:.0f} kHz"),
            ("4.3.1.7.2 COT < 60 ms, slot <= COT", FHSS_COT_US < 60_000 and FHSS_SLOT_US <= FHSS_COT_US,
             f"COT {FHSS_COT_US / 1e3:.0f} ms, slot {FHSS_SLOT_US / 1e3:.0f} ms"),
            ("4.3.1.7.2 idle >= 5 % of COT and >= 100 us", FHSS_IDLE_US >= max(0.05 * FHSS_COT_US, 100),
             f"{FHSS_IDLE_US} us"),
            ("4.3.1.7.2 CCA >= 18 us and >= 0.2 % of COT", FHSS_CCA_US >= max(18, 0.002 * FHSS_COT_US),
             f"{FHSS_CCA_US} us (RPD settles in 170 us)"),
            ("4.3.1.7.2 CCA threshold (RPD) <= TL at the port", rpd_port <= tl_port,
             f"RPD {rpd_port:.0f} dBm (LNA {SP4_LNA_GAIN_DB:.0f} dB est.) vs TL {tl_port:.1f} dBm "
             f"({tl:.1f} dBm/MHz at 0 dBi): {tl_port - rpd_port:.1f} dB spare -> T17"),
            ("D-R6: hops >= 6 MHz from any fixed channel of another team", others >= FHSS_GUARD_MHZ + 1,
             f"others RF_CH {FHSS_OTHERS or 'none: all teams hop at 20 dBm'}"),
            ("D-R6: consecutive hops >= 10 MHz apart", seq_step >= 10, f"min {seq_step} MHz"),
        ]

    # --- registers ----------------------------------------------------------
    def registers(self) -> list[tuple[str, int, int]]:
        config = 0x08 | (0x04 if self.crc_bytes == 2 else 0) | 0x02   # EN_CRC, CRCO, PWR_UP, PTX
        return [
            ("EN_AA", REG["EN_AA"], 0x01),          # needed for DPL; frames go out NOACK
            ("EN_RXADDR", REG["EN_RXADDR"], 0x01),  # pipe 0 only
            ("SETUP_AW", REG["SETUP_AW"], 0x03),    # 5 B addresses
            ("SETUP_RETR", REG["SETUP_RETR"], 0x00),
            ("RF_CH", REG["RF_CH"], self.rf_ch),
            ("RF_SETUP", REG["RF_SETUP"], RATES[self.bitrate] | (RF_PWR[self.chip_dbm] << 1)),
            ("RX_PW_P0", REG["RX_PW_P0"], MAX_PAYLOAD),
            ("FEATURE", REG["FEATURE"], 0x05),      # EN_DPL | EN_DYN_ACK
            ("DYNPD", REG["DYNPD"], 0x01),          # dynamic payload on pipe 0
            ("STATUS", REG["STATUS"], 0x70),        # clear RX_DR | TX_DS | MAX_RT
            ("CONFIG", REG["CONFIG"], config),      # last: powers the radio up
        ]


PROFILES = [
    Profile("TEAM_250K", "Quick Mode, bench and fallback: our fixed channel at 10 mW (UN-85 b), 250 kbps",
            rf_ch=TEAM_CH),
    Profile("TEAM_1M", "fixed-channel option at 1 Mbps, 10 mW (fallback only)", rf_ch=TEAM_CH, bitrate=1_000_000),
    Profile("NM_COMMON", "PHY shared by all teams in NM (see NM_PHY_PROPOSAL.md)", rf_ch=NM_CH, address=NM_ADDR),
    Profile("TEAM_FHSS", "SRI/MRM baseline: adaptive FHSS + LBT, <= 20 dBm e.i.r.p. (D-R6, UN-85 a)",
            rf_ch=FHSS_HOPSEQ[0], chip_dbm=MAX_CHIP_DBM_FHSS, lbt=True),
]


def header_text() -> str:
    out = [
        "/* GENERATED by radio/phy_config.py - do not edit by hand. */",
        "#ifndef NRF24_CONFIG_H",
        "#define NRF24_CONFIG_H",
        "",
        "#include <stdint.h>",
        "",
        "typedef struct { uint8_t addr; uint8_t value; } nrf24_reg_t;",
        "",
        "typedef struct {",
        "    const char *name;",
        "    const nrf24_reg_t *regs;  /* CONFIG last: it powers the radio up */",
        "    uint8_t n_regs;",
        "    uint8_t rf_ch;            /* f = 2400 + rf_ch MHz */",
        "    uint32_t bitrate_bps;",
        "    uint8_t address[5];       /* TX_ADDR = RX_ADDR_P0, LSByte first on SPI */",
        "    uint8_t crc_bytes;",
        "    uint8_t max_len;          /* largest payload (dynamic payload length) */",
        "    uint8_t pwr_max_bits;     /* highest RF_PWR this profile may use */",
        "    uint8_t lbt;              /* 1 = adaptive FHSS: hop set only, CCA before TX, COT limit */",
        "} nrf24_profile_t;",
        "",
        f"/* Highest RF_PWR the driver accepts: {MAX_CHIP_DBM} dBm at the chip. The E01 PA follows it, so a",
        " * higher setting would break the 10 mW e.i.r.p. limit (CNAF UN-85 b). */",
        f"#define NRF24_RF_PWR_MAX_BITS {RF_PWR[MAX_CHIP_DBM]}u",
        "",
        "/* D-R6 (SRI/MRM baseline, 16-Oct-26): adaptive FHSS + LBT under UN-85 a), 100 mW e.i.r.p.",
        f" * (EN 300 328 V2.2.2 cl. 4.3.1.7.2). Only an lbt profile may use RF_PWR up to {MAX_CHIP_DBM_FHSS} dBm, the",
        " * highest step whose worst-case e.i.r.p. (PA 25 dB, omni 3 dBi peak) is <= 20 dBm. T0 may raise it. */",
        f"#define NRF24_RF_PWR_MAX_BITS_FHSS {RF_PWR[MAX_CHIP_DBM_FHSS]}u",
        f"#define NRF24_FHSS_SLOT_US {FHSS_SLOT_US}u   /* dwell per hop */",
        f"#define NRF24_FHSS_COT_US {FHSS_COT_US}u   /* max TX time after one clear CCA (< 60 ms) */",
        f"#define NRF24_FHSS_IDLE_US {FHSS_IDLE_US}u    /* idle before a new CCA on the same channel */",
        f"#define NRF24_FHSS_CCA_US {FHSS_CCA_US}u     /* RX time before RPD is valid */",
        f"#define NRF24_FHSS_N {len(FHSS_HOPSEQ)}u",
        f"/* Hop order: RF_CH {min(FHSS_HOPSET)}..{max(FHSS_HOPSET)} even ({len(FHSS_HOPSET)} channels); all teams hop at 20 dBm, "
        "so no fixed channels to avoid. */",
        "static const uint8_t NRF24_FHSS_HOPSEQ[NRF24_FHSS_N] = {",
        "    " + ", ".join(f"{c}u" for c in FHSS_HOPSEQ[:15]) + ",",
        "    " + ", ".join(f"{c}u" for c in FHSS_HOPSEQ[15:]) + ",",
        "};",
        "",
    ]
    for p in PROFILES:
        out.append(f"/* {p.name}: {p.purpose}")
        out.append(f" * RF_CH {p.rf_ch} = {p.f / 1e6:.0f} MHz, {p.bitrate // 1000} kbps, RF_PWR {p.chip_dbm} dBm "
                   f"(<= {p.conducted_dbm:+.0f} dBm at the E01 IPEX), {p.antenna}: {p.eirp_dbm:.1f} dBm e.i.r.p. */")
        out.append(f"static const nrf24_reg_t NRF24_REGS_{p.name}[] = {{")
        for name, addr, val in p.registers():
            out.append(f"    {{0x{addr:02X}, 0x{val:02X}}},  /* {name} */")
        out.append("};")
        addr = ", ".join(f"0x{b:02X}" for b in p.address)
        out.append(f"static const nrf24_profile_t NRF24_PROFILE_{p.name} = {{")
        out.append(f'    "{p.name}", NRF24_REGS_{p.name},')
        out.append(f"    (uint8_t)(sizeof NRF24_REGS_{p.name} / sizeof NRF24_REGS_{p.name}[0]),")
        out.append(f"    {p.rf_ch}u, {p.bitrate}u, {{{addr}}}, {p.crc_bytes}u, {MAX_PAYLOAD}u,")
        out.append(f"    {RF_PWR[p.chip_cap]}u, {1 if p.lbt else 0}u,")
        out.append("};")
        out.append("")
    out.append("#endif /* NRF24_CONFIG_H */")
    return "\n".join(out) + "\n"


def report() -> bool:
    ok_all = True
    for p in PROFILES:
        t32 = p.airtime_us(MAX_PAYLOAD)
        print(f"\n{p.name} - {p.purpose}")
        print(f"  RF_CH {p.rf_ch} = {p.f / 1e6:.0f} MHz, {p.bitrate / 1e3:.0f} kbps, Carson OBW {p.obw / 1e3:.0f} kHz, "
              f"drift +-{p.drift / 1e3:.0f} kHz/box")
        print(f"  frame airtime (32 B payload) {t32:.0f} us (+130 us TX settling per frame)")
        if p.lbt:
            print(f"  hop set ({len(FHSS_HOPSET)}): RF_CH {FHSS_HOPSET}")
            print(f"  hop order: {FHSS_HOPSEQ}")
        for label, ok, detail in p.checks():
            ok_all &= ok
            print(f"  [{'OK ' if ok else 'FAIL'}] {label:52} {detail}")
    print("\nNo duty-cycle limit in 2400-2483.5 MHz (UN-85 b, or UN-85 a with LBT): no TX budget to track.")
    print("Non-adaptive FHSS would add MU = P/100 mW x DC <= 10 % (cl. 4.3.1.6): not used.")
    return ok_all


if __name__ == "__main__":
    ok = report()
    hdr = Path(__file__).with_name("fw") / "nrf24_config.h"
    hdr.parent.mkdir(exist_ok=True)
    hdr.write_text(header_text())
    print(f"\nwrote {hdr.relative_to(Path(__file__).parent.parent)}  ({'all checks pass' if ok else 'CHECKS FAILED'})")
    raise SystemExit(0 if ok else 1)
