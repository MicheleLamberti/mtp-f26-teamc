/* MTP-F26 Team C - nRF24L01+ bench tool for the Raspberry Pi 3 (Linux HAL).
 *
 *   nrf24_probe init     [--profile P]             T0 step 1: driver start-up + register dump
 *   nrf24_probe survey   [--samples N] [--hopset]  RPD busy share per channel (T14, T0 step 5 Pi noise)
 *   nrf24_probe tx       [--count N] [--len L] [--profile P]   frames with sequence numbers; measures
 *                                                  the per-frame period and gap (T0 step 4, T2)
 *   nrf24_probe rx       [--seconds S] [--profile P]           counts frames and losses (T0 step 4, T2)
 *   nrf24_probe timing   [--n N]                   delay and wake-up jitter of this machine, no radio
 *
 *   Board options: --spidev /dev/spidev0.0 --hz 8000000 --chip /dev/gpiochip0 --ce 22 --irq 24 (-1 = poll)
 *   --rt CPU   run as SCHED_FIFO pinned to CPU (needs root; isolcpus=CPU on the kernel command line)
 *
 * tx and rx use the 10 mW profiles only (TEAM_250K, TEAM_1M, NM_COMMON): the 20 dBm profiles need
 * a CCA per hop and belong to the protocol (proto/src/link.c), not to a bench tool.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "nrf24_hal_linux.h"

typedef struct {
    const char *cmd;
    nrf24_linux_cfg_t board;
    const nrf24_profile_t *profile;
    unsigned count, len, samples, n;
    double seconds;
    int hopset, rt_cpu;
} opts_t;

static const nrf24_profile_t *const PROFILES[] = {&NRF24_PROFILE_TEAM_250K, &NRF24_PROFILE_TEAM_1M,
                                                  &NRF24_PROFILE_NM_COMMON, &NRF24_PROFILE_TEAM_FHSS,
                                                  &NRF24_PROFILE_TEAM_20DBM_FIXED};
#define N_PROFILES (sizeof PROFILES / sizeof PROFILES[0])

static const char *status_name(nrf24_status_t s)
{
    switch (s) {
    case NRF24_OK: return "OK";
    case NRF24_ERR_SPI: return "ERR_SPI (no answer on SPI: wiring, CSN, VCC, or SPI off)";
    case NRF24_ERR_NOT_PLUS: return "ERR_NOT_PLUS (an old nRF24L01 without 250 kbps: return it)";
    case NRF24_ERR_TIMEOUT: return "ERR_TIMEOUT";
    case NRF24_ERR_LEN: return "ERR_LEN";
    case NRF24_ERR_CH: return "ERR_CH";
    case NRF24_ERR_NODATA: return "ERR_NODATA";
    case NRF24_ERR_POWER: return "ERR_POWER";
    case NRF24_ERR_LBT: return "ERR_LBT";
    }
    return "?";
}

static int cmp_u32(const void *a, const void *b)
{
    uint32_t x = *(const uint32_t *)a, y = *(const uint32_t *)b;
    return x < y ? -1 : x > y;
}

/* min / mean / p99 / max of n samples (sorts them). */
static void stats(uint32_t *v, unsigned n, const char *label, const char *unit)
{
    if (!n)
        return;
    qsort(v, n, sizeof v[0], cmp_u32);
    double sum = 0;
    for (unsigned i = 0; i < n; i++)
        sum += v[i];
    printf("  %-34s min %6u  mean %8.1f  p99 %6u  max %6u %s\n", label, v[0], sum / n, v[(n * 99u) / 100u],
           v[n - 1], unit);
}

static int open_radio(const opts_t *o, nrf24_linux_t *lx, nrf24_hal_t *hal, nrf24_t *dev)
{
    if (nrf24_linux_open(lx, &o->board, hal)) {
        fprintf(stderr, "%s\n", lx->err);
        return -1;
    }
    if (o->rt_cpu >= 0 && nrf24_linux_realtime(lx, o->rt_cpu, 80))
        fprintf(stderr, "warning: %s; running without real-time priority\n", lx->err);
    nrf24_status_t st = nrf24_init(dev, hal, o->profile);
    printf("nrf24_init(%s): %s\n", o->profile->name, status_name(st));
    if (st != NRF24_OK) {
        nrf24_linux_close(lx);
        return -1;
    }
    return 0;
}

static int cmd_init(const opts_t *o)
{
    nrf24_linux_t lx;
    nrf24_hal_t hal;
    nrf24_t dev;
    if (open_radio(o, &lx, &hal, &dev))
        return 1;
    static const uint8_t regs[] = {0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09,
                                   0x11, 0x17, 0x1C, 0x1D};
    printf("  reg  value\n");
    for (unsigned i = 0; i < sizeof regs; i++)
        printf("  0x%02X  0x%02X\n", regs[i], nrf24_read_reg(&dev, regs[i]));
    printf("  RF_CH %u = %u MHz, %u bps, SPI %u Hz, %u SPI errors\n", dev.rf_ch, 2400u + dev.rf_ch,
           o->profile->bitrate_bps, lx.spi_hz, lx.spi_errors);
    nrf24_linux_close(&lx);
    return 0;
}

static int in_hopset(uint8_t ch)
{
    for (unsigned i = 0; i < NRF24_FHSS_N; i++)
        if (NRF24_FHSS_HOPSEQ[i] == ch)
            return 1;
    return 0;
}

static int cmd_survey(opts_t *o)
{
    o->profile = &NRF24_PROFILE_TEAM_250K;   /* listen only: any legal channel */
    nrf24_linux_t lx;
    nrf24_hal_t hal;
    nrf24_t dev;
    if (open_radio(o, &lx, &hal, &dev))
        return 1;
    printf("RPD survey, %u samples per channel (busy = RPD set in any of 3 reads 20 us apart, as nrf24_cca)\n",
           o->samples);
    printf("  ch   MHz  hop  busy %%\n");
    for (uint8_t ch = 0; ch <= NRF24_MAX_LEGAL_CH; ch++) {
        if (o->hopset && !in_hopset(ch))
            continue;
        nrf24_set_channel(&dev, ch);
        unsigned busy = 0;
        for (unsigned s = 0; s < o->samples; s++) {
            hal.ce(hal.ctx, 0);   /* fresh RX each sample: RPD is not latched from earlier */
            dev.rx_on = 0;
            nrf24_start_rx(&dev);
            hal.delay_us(hal.ctx, NRF24_FHSS_CCA_US);
            int b = nrf24_carrier(&dev);
            for (int k = 0; k < 2 && !b; k++) {
                hal.delay_us(hal.ctx, 20u);
                b = nrf24_carrier(&dev);
            }
            busy += (unsigned)b;
        }
        printf("  %2u  %4u   %s  %5.1f\n", ch, 2400u + ch, in_hopset(ch) ? "*" : " ", 100.0 * busy / o->samples);
    }
    nrf24_linux_close(&lx);
    return 0;
}

static int cmd_tx(const opts_t *o)
{
    if (o->profile->lbt) {
        fprintf(stderr, "tx uses the 10 mW profiles only (TEAM_250K, TEAM_1M, NM_COMMON)\n");
        return 2;
    }
    nrf24_linux_t lx;
    nrf24_hal_t hal;
    nrf24_t dev;
    if (open_radio(o, &lx, &hal, &dev))
        return 1;
    uint8_t len = (uint8_t)(o->len < 3 ? 3 : o->len > 32 ? 32 : o->len);
    uint32_t *period = calloc(o->count, sizeof *period);
    if (!period)
        return 1;
    uint8_t f[32];
    unsigned ok = 0, timeouts = 0, np = 0;
    uint32_t prev = 0;
    for (unsigned i = 0; i < o->count; i++) {
        f[0] = (uint8_t)(i >> 8);
        f[1] = (uint8_t)i;
        for (uint8_t k = 2; k < len; k++)
            f[k] = (uint8_t)(i * 7u + k);
        uint32_t t = nrf24_linux_micros();
        if (i)
            period[np++] = t - prev;
        prev = t;
        nrf24_status_t st = nrf24_send(&dev, f, len);
        if (st == NRF24_OK)
            ok++;
        else
            timeouts++;
    }
    uint32_t air = nrf24_airtime_us(o->profile, len);
    printf("sent %u of %u frames of %u B on RF_CH %u (%u timeouts, %u SPI errors)\n", ok, o->count, len, dev.rf_ch,
           timeouts, lx.spi_errors);
    double mean = 0;
    for (unsigned i = 0; i < np; i++)
        mean += period[i];
    mean = np ? mean / np : 0;
    stats(period, np, "period between frames", "us");
    printf("  airtime %u us -> per-frame gap %.0f us (model in linkbudget.py FRAMING: 300 us)\n", air, mean - air);
    if (mean > 0)
        printf("  back-to-back rate: %.1f kbps of payload\n", len * 8.0 * 1000.0 / mean);
    free(period);
    nrf24_linux_close(&lx);
    return timeouts ? 1 : 0;
}

static int cmd_rx(const opts_t *o)
{
    if (o->profile->lbt) {
        fprintf(stderr, "rx uses the 10 mW profiles only (TEAM_250K, TEAM_1M, NM_COMMON)\n");
        return 2;
    }
    nrf24_linux_t lx;
    nrf24_hal_t hal;
    nrf24_t dev;
    if (open_radio(o, &lx, &hal, &dev))
        return 1;
    nrf24_start_rx(&dev);
    printf("listening on RF_CH %u for %.0f s (%s)\n", dev.rf_ch, o->seconds,
           lx.irq_fd >= 0 ? "IRQ edges" : "polling");
    unsigned got = 0, lost = 0, dup = 0, rpd = 0, edges = 0;
    int have_last = 0;
    uint16_t last = 0;
    uint32_t start = nrf24_linux_micros(), dur = (uint32_t)(o->seconds * 1e6);
    while (nrf24_linux_micros() - start < dur) {
        if (lx.irq_fd >= 0) {
            uint32_t t;
            if (nrf24_linux_wait_irq(&lx, 20000u, &t) == 1)
                edges++;
        } else {
            nrf24_linux_delay_us(200u);
        }
        uint8_t f[32], len = 0;
        while (nrf24_poll_rx(&dev, f, &len) == NRF24_OK) {
            if (len < 2)
                continue;
            uint16_t seq = (uint16_t)(f[0] << 8 | f[1]);
            got++;
            rpd += dev.last_rpd;
            if (have_last) {
                uint16_t d = (uint16_t)(seq - last);
                if (d == 0)
                    dup++;
                else
                    lost += d - 1u;
            }
            have_last = 1;
            last = seq;
        }
    }
    unsigned total = got + lost;
    printf("received %u frames, %u lost by sequence gap, %u duplicates: PER %.2f %%\n", got, lost, dup,
           total ? 100.0 * lost / total : 0.0);
    printf("  RPD set on %.0f %% of frames (above ~-76 dBm at the antenna port); %u IRQ edges; %u SPI errors\n",
           got ? 100.0 * rpd / got : 0.0, edges, lx.spi_errors);
    nrf24_linux_close(&lx);
    return 0;
}

static uint64_t mono_ns(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000u + (uint64_t)ts.tv_nsec;
}

static int cmd_timing(const opts_t *o)
{
    if (o->rt_cpu >= 0) {
        nrf24_linux_t lx;
        memset(&lx, 0, sizeof lx);
        if (nrf24_linux_realtime(&lx, o->rt_cpu, 80))
            fprintf(stderr, "warning: %s; measuring without real-time priority\n", lx.err);
    }
    unsigned n = o->n;
    uint32_t *v = calloc(n, sizeof *v);
    if (!v)
        return 1;
    printf("delay_us overshoot (asked vs got), %u runs each:\n", n);
    static const uint32_t asks[] = {15u, 130u, 170u, 2500u};   /* CE pulse, PLL settle, CCA, LBT idle */
    for (unsigned a = 0; a < sizeof asks / sizeof asks[0]; a++) {
        for (unsigned i = 0; i < n; i++) {
            uint64_t t0 = mono_ns();
            nrf24_linux_delay_us(asks[a]);
            uint64_t got = (mono_ns() - t0) / 1000u;
            v[i] = (uint32_t)(got > asks[a] ? got - asks[a] : 0u);
        }
        char label[48];
        snprintf(label, sizeof label, "delay_us(%u)", asks[a]);
        stats(v, n, label, "us late");
    }

    /* Periodic 1 ms wake-ups (a small cyclictest): how late does the scheduler wake us? */
    unsigned wakes = n * 5u;
    uint32_t *w = calloc(wakes, sizeof *w);
    if (!w)
        return 1;
    uint64_t next = mono_ns() + 1000000u;
    for (unsigned i = 0; i < wakes; i++) {
        struct timespec ts = {(time_t)(next / 1000000000u), (long)(next % 1000000000u)};
        clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &ts, NULL);
        uint64_t late = mono_ns() - next;
        w[i] = (uint32_t)(late / 1000u);
        next += 1000000u;
    }
    printf("1 ms periodic wake-ups, %u of them (%.1f s):\n", wakes, wakes / 1000.0);
    stats(w, wakes, "wake-up lateness", "us");
    uint32_t worst = w[wakes - 1];
    printf("  budget: a stall > ~2400 us mid-burst triggers the receiver's idle ACK; the TX_DS wait is ~3800 us.\n");
    printf("  verdict: %s\n", worst < 500u ? "OK for the link timers as they are"
                              : worst < 2000u ? "tight: use --rt on an isolated core, or PREEMPT_RT"
                                              : "too slow: PREEMPT_RT + isolcpus, or widen the Linux link timers");
    free(v);
    free(w);
    return 0;
}

static void usage(void)
{
    fprintf(stderr,
            "usage: nrf24_probe init|survey|tx|rx|timing [--profile P] [--count N] [--len L] [--seconds S]\n"
            "       [--samples N] [--hopset] [--n N] [--rt CPU] [--spidev DEV] [--hz HZ] [--chip DEV] [--ce GPIO]\n"
            "       [--irq GPIO|-1]   profiles:");
    for (unsigned i = 0; i < N_PROFILES; i++)
        fprintf(stderr, " %s", PROFILES[i]->name);
    fprintf(stderr, "\n");
}

int main(int argc, char **argv)
{
    opts_t o;
    memset(&o, 0, sizeof o);
    nrf24_linux_cfg_t def = NRF24_LINUX_CFG_DEFAULT;
    o.board = def;
    o.profile = &NRF24_PROFILE_TEAM_250K;
    o.count = 1000;
    o.len = 32;
    o.samples = 200;
    o.n = 1000;
    o.seconds = 10;
    o.rt_cpu = -1;
    if (argc < 2) {
        usage();
        return 2;
    }
    o.cmd = argv[1];
    for (int i = 2; i < argc; i++) {
        const char *a = argv[i], *v = i + 1 < argc ? argv[i + 1] : NULL;
        if (!strcmp(a, "--hopset")) {
            o.hopset = 1;
            continue;
        }
        if (!v) {
            usage();
            return 2;
        }
        i++;
        if (!strcmp(a, "--profile")) {
            o.profile = NULL;
            for (unsigned k = 0; k < N_PROFILES; k++)
                if (!strcmp(v, PROFILES[k]->name))
                    o.profile = PROFILES[k];
            if (!o.profile) {
                usage();
                return 2;
            }
        } else if (!strcmp(a, "--count")) {
            o.count = (unsigned)strtoul(v, NULL, 0);
        } else if (!strcmp(a, "--len")) {
            o.len = (unsigned)strtoul(v, NULL, 0);
        } else if (!strcmp(a, "--seconds")) {
            o.seconds = atof(v);
        } else if (!strcmp(a, "--samples")) {
            o.samples = (unsigned)strtoul(v, NULL, 0);
        } else if (!strcmp(a, "--n")) {
            o.n = (unsigned)strtoul(v, NULL, 0);
        } else if (!strcmp(a, "--rt")) {
            o.rt_cpu = atoi(v);
        } else if (!strcmp(a, "--spidev")) {
            o.board.spidev = v;
        } else if (!strcmp(a, "--hz")) {
            o.board.spi_hz = (uint32_t)strtoul(v, NULL, 0);
        } else if (!strcmp(a, "--chip")) {
            o.board.gpiochip = v;
        } else if (!strcmp(a, "--ce")) {
            o.board.ce_gpio = (unsigned)strtoul(v, NULL, 0);
        } else if (!strcmp(a, "--irq")) {
            o.board.irq_gpio = atoi(v);
        } else {
            usage();
            return 2;
        }
    }
    if (o.count < 2 || o.samples < 1 || o.n < 10) {
        usage();
        return 2;
    }
    if (!strcmp(o.cmd, "init"))
        return cmd_init(&o);
    if (!strcmp(o.cmd, "survey"))
        return cmd_survey(&o);
    if (!strcmp(o.cmd, "tx"))
        return cmd_tx(&o);
    if (!strcmp(o.cmd, "rx"))
        return cmd_rx(&o);
    if (!strcmp(o.cmd, "timing"))
        return cmd_timing(&o);
    usage();
    return 2;
}
