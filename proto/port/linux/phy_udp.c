/* MTP-F26 Team C - emulated radio over UDP (127.0.0.1), for whole-node tests on a PC. See phy.h.
 *
 * Each node binds its own port and sends every frame to its peers' ports. A datagram carries the channel,
 * bit rate, address, payload and the frame's start/end times (all processes share CLOCK_MONOTONIC). The
 * receiver keeps it only if the radios match (rate, address), it was on that channel when the frame began,
 * it was not transmitting itself (half-duplex), and the random link loss spares it. The sender sleeps through
 * PLL settling + airtime, so the timing is the nRF24's. LBT profiles follow the driver's rule: no frame without
 * a clear CCA since the last channel change or RX period, at most COT of transmissions per CCA.
 */
#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

#include "phy.h"

#define MAGIC 0x54435231u   /* "TCR1" */
#define MAX_PEERS 8
#define HIST 64
#define DG_LEN (4 + 1 + 1 + 4 + 5 + 8 + 8 + 32)

typedef struct {
    const nrf24_profile_t *p;
    int fd;
    uint16_t peers[MAX_PEERS];
    unsigned n_peers;
    double loss, busy;
    uint64_t rng;
    uint8_t ch;
    struct { uint64_t t; uint8_t ch; } hist[HIST];   /* channel changes, newest at hist_n - 1 */
    unsigned hist_n;
    struct { uint64_t s, e; } deaf[16];
    unsigned deaf_n;
    int cca_clear;
    uint64_t cot_start;
} udp_t;

uint64_t phy_now_us(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000u + (uint64_t)ts.tv_nsec / 1000u;
}

void phy_sleep_until(uint64_t t)
{
    uint64_t now = phy_now_us();
    if (t > now + 400u) {
        uint64_t w = t - 200u;
        struct timespec ts = {(time_t)(w / 1000000u), (long)(w % 1000000u) * 1000};
        while (clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &ts, NULL) == EINTR)
            ;
    }
    while (phy_now_us() < t)
        ;
}

static double rnd(udp_t *u)
{
    u->rng ^= u->rng >> 12;
    u->rng ^= u->rng << 25;
    u->rng ^= u->rng >> 27;
    return (double)((u->rng * 2685821657736338717ULL) >> 11) * (1.0 / 9007199254740992.0);
}

static void put64(uint8_t *p, uint64_t v)
{
    for (int i = 7; i >= 0; i--, v >>= 8)
        p[i] = (uint8_t)v;
}

static uint64_t get64(const uint8_t *p)
{
    uint64_t v = 0;
    for (int i = 0; i < 8; i++)
        v = v << 8 | p[i];
    return v;
}

static uint8_t channel_at(const udp_t *u, uint64_t t)
{
    unsigned n = u->hist_n < HIST ? u->hist_n : HIST;
    for (unsigned k = 0; k < n; k++) {   /* newest first */
        unsigned i = (u->hist_n - 1u - k) % HIST;
        if (u->hist[i].t <= t)
            return u->hist[i].ch;
    }
    return u->ch;
}

static int u_set_channel(void *ctx, uint8_t ch)
{
    udp_t *u = ctx;
    if (ch > NRF24_MAX_LEGAL_CH)
        return -1;
    u->ch = ch;
    unsigned i = u->hist_n++ % HIST;
    u->hist[i].t = phy_now_us();
    u->hist[i].ch = ch;
    u->cca_clear = 0;
    return 0;
}

static void u_start_rx(void *ctx)
{
    udp_t *u = ctx;
    u->cca_clear = 0;   /* as the driver: listening ends the channel occupancy */
}

static int u_cca(void *ctx)
{
    udp_t *u = ctx;
    phy_sleep_until(phy_now_us() + NRF24_TX_SETTLE_US + NRF24_FHSS_CCA_US);
    if (rnd(u) < u->busy) {
        u->cca_clear = 0;
        return 0;
    }
    u->cca_clear = 1;
    u->cot_start = phy_now_us();
    return 1;
}

static int u_send(void *ctx, const uint8_t *f, uint8_t len)
{
    udp_t *u = ctx;
    if (len == 0 || len > 32u)
        return -1;
    uint32_t air = nrf24_airtime_us(u->p, len);
    uint64_t t0 = phy_now_us();
    if (u->p->lbt && (!u->cca_clear || t0 + NRF24_TX_SETTLE_US + air > u->cot_start + u->p->cot_us)) {
        u->cca_clear = 0;
        return 1;
    }
    uint64_t start = t0 + NRF24_TX_SETTLE_US, end = start + air;
    phy_sleep_until(end);
    unsigned d = u->deaf_n++ % 16u;
    u->deaf[d].s = t0;
    u->deaf[d].e = end;
    uint8_t dg[DG_LEN];
    memset(dg, 0, sizeof dg);
    dg[0] = (uint8_t)(MAGIC >> 24);
    dg[1] = (uint8_t)(MAGIC >> 16);
    dg[2] = (uint8_t)(MAGIC >> 8);
    dg[3] = (uint8_t)MAGIC;
    dg[4] = u->ch;
    dg[5] = len;
    for (int i = 0; i < 4; i++)
        dg[6 + i] = (uint8_t)(u->p->bitrate_bps >> (24 - 8 * i));
    memcpy(dg + 10, u->p->address, 5);
    put64(dg + 15, start);
    put64(dg + 23, end);
    memcpy(dg + 31, f, len);
    for (unsigned k = 0; k < u->n_peers; k++) {
        struct sockaddr_in a;
        memset(&a, 0, sizeof a);
        a.sin_family = AF_INET;
        a.sin_port = htons(u->peers[k]);
        a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        sendto(u->fd, dg, sizeof dg, 0, (struct sockaddr *)&a, sizeof a);
    }
    return 0;
}

static int u_recv(void *ctx, uint64_t deadline, uint8_t *f, uint8_t *len, uint64_t *t_end, uint8_t *rpd)
{
    udp_t *u = ctx;
    for (;;) {
        uint64_t now = phy_now_us();
        if (now >= deadline)
            return 0;
        uint64_t left = deadline - now;
        struct timespec ts = {(time_t)(left / 1000000u), (long)(left % 1000000u) * 1000};
        struct pollfd p = {u->fd, POLLIN, 0};
        int r = ppoll(&p, 1, &ts, NULL);
        if (r <= 0)
            continue;
        uint8_t dg[DG_LEN];
        if (recv(u->fd, dg, sizeof dg, 0) != (ssize_t)sizeof dg)
            continue;
        uint32_t magic = (uint32_t)dg[0] << 24 | (uint32_t)dg[1] << 16 | (uint32_t)dg[2] << 8 | dg[3];
        uint32_t rate = (uint32_t)dg[6] << 24 | (uint32_t)dg[7] << 16 | (uint32_t)dg[8] << 8 | dg[9];
        uint8_t n = dg[5];
        uint64_t s = get64(dg + 15), e = get64(dg + 23);
        if (magic != MAGIC || rate != u->p->bitrate_bps || memcmp(dg + 10, u->p->address, 5) || n == 0 || n > 32u)
            continue;
        if (channel_at(u, s) != dg[4] || channel_at(u, e) != dg[4])
            continue;   /* we were listening on another channel */
        int deaf = 0;
        for (unsigned k = 0; k < 16u && k < u->deaf_n; k++)
            if (u->deaf[k].s < e && s < u->deaf[k].e)
                deaf = 1;
        if (deaf || rnd(u) < u->loss)
            continue;
        memcpy(f, dg + 31, n);
        *len = n;
        *t_end = e;
        *rpd = 1;
        return 1;
    }
}

static void u_close(void *ctx)
{
    udp_t *u = ctx;
    close(u->fd);
    free(u);
}

int phy_udp_open(phy_t *phy, const phy_udp_opts_t *o, const nrf24_profile_t *profile, char *err, unsigned errlen)
{
    udp_t *u = calloc(1, sizeof *u);
    if (!u)
        return -1;
    u->p = profile;
    u->loss = o->loss;
    u->busy = o->busy;
    u->rng = (uint64_t)o->seed * 0x9E3779B97F4A7C15ULL + 1u;
    u->ch = profile->rf_ch;
    unsigned my = 0;
    const char *s = o->spec;
    if (strncmp(s, "udp:", 4) || sscanf(s + 4, "%u", &my) != 1 || !my || my > 65535u) {
        snprintf(err, errlen, "bad radio spec %s (want udp:<port>:<peer>[,<peer>...])", s);
        free(u);
        return -1;
    }
    const char *q = strchr(s + 4, ':');
    while (q && u->n_peers < MAX_PEERS) {
        unsigned pp = (unsigned)strtoul(q + 1, NULL, 10);
        if (pp && pp <= 65535u)
            u->peers[u->n_peers++] = (uint16_t)pp;
        q = strchr(q + 1, ',');
    }
    u->fd = socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
    struct sockaddr_in a;
    memset(&a, 0, sizeof a);
    a.sin_family = AF_INET;
    a.sin_port = htons((uint16_t)my);
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (u->fd < 0 || bind(u->fd, (struct sockaddr *)&a, sizeof a) < 0) {
        snprintf(err, errlen, "cannot bind udp port %u: %s", my, strerror(errno));
        if (u->fd >= 0)
            close(u->fd);
        free(u);
        return -1;
    }
    u_set_channel(u, profile->rf_ch);
    memset(phy, 0, sizeof *phy);
    phy->ctx = u;
    phy->profile = profile;
    phy->set_channel = u_set_channel;
    phy->start_rx = u_start_rx;
    phy->cca = u_cca;
    phy->send = u_send;
    phy->recv = u_recv;
    phy->close = u_close;
    return 0;
}
