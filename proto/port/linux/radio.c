/* MTP-F26 Team C - radio layer of the Linux node. See radio.h. */
#define _GNU_SOURCE
#include "radio.h"

#include "frames.h"

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/random.h>
#include <time.h>

static uint32_t air(const radio_t *r, uint8_t len) { return nrf24_airtime_us(r->p, len); }

static int idx_of(uint8_t ch)
{
    for (unsigned i = 0; i < NRF24_FHSS_N; i++)
        if (NRF24_FHSS_HOPSEQ[i] == ch)
            return (int)i;
    return -1;
}

/* Hop slot of time t for this node (a slave counts from RADIO_GUARD_US before the estimated start). */
static int64_t slot_of(const radio_t *r, uint64_t t)
{
    int64_t x = (int64_t)t + (r->master ? 0 : (int64_t)RADIO_GUARD_US) - r->origin;
    return x >= 0 ? x / (int64_t)r->slot_us : -1 - (-x - 1) / (int64_t)r->slot_us;
}

/* Start of slot k as this node uses it. */
static uint64_t slot_start(const radio_t *r, int64_t k)
{
    return (uint64_t)(r->origin + k * (int64_t)r->slot_us - (r->master ? 0 : (int64_t)RADIO_GUARD_US));
}

static int hopping(const radio_t *r) { return r->fhss && (r->master || r->synced); }

uint8_t radio_channel_at(const radio_t *r, uint64_t t)
{
    if (!r->fhss)
        return r->p->rf_ch;
    if (!hopping(r))
        return NRF24_FHSS_HOPSEQ[0];
    int64_t k = slot_of(r, t) % (int64_t)NRF24_FHSS_N;
    return NRF24_FHSS_HOPSEQ[k < 0 ? k + (int64_t)NRF24_FHSS_N : k];
}

static void tune(radio_t *r, uint64_t now)
{
    if (!r->fhss)
        return;
    int64_t k = hopping(r) ? slot_of(r, now) : -1;
    uint8_t ch = radio_channel_at(r, now);
    if (k == r->cur_k && ch == r->ch)
        return;
    r->prev_ch = r->ch;
    r->prev_k = r->cur_k;
    r->prev_tune_us = r->tune_us;
    r->cur_k = k;
    r->tune_us = now;
    r->slot_state = 0;
    if (ch != r->ch) {
        r->phy->set_channel(r->phy->ctx, ch);
        r->ch = ch;
        r->in_rx = 0;   /* listen again on the new channel before waiting there */
    }
}

/* When the frame at the head of the queue may start (>= now). */
static uint64_t tx_ready(const radio_t *r, uint64_t now)
{
    uint64_t t = now > r->backoff_until ? now : r->backoff_until;
    if (!hopping(r))
        return t;
    int64_t k = slot_of(r, t);
    uint64_t s = slot_start(r, k), next = slot_start(r, k + 1);
    if (k == r->cur_k && r->slot_state < 0)
        return next + r->hop_us;   /* this hop's CCA was busy */
    if (t < s + r->hop_us)
        t = s + r->hop_us;
    if (t + NRF24_TX_SETTLE_US + air(r, r->qlen[r->qh]) > next)
        return next + r->hop_us;   /* would cross the hop boundary */
    return t;
}

static void pop(radio_t *r)
{
    r->qh = (r->qh + 1u) % RADIO_QCAP;
    r->qn--;
}

/* Send the head of the queue now (tx_ready said so). */
static void tx_one(radio_t *r)
{
    const uint8_t *f = r->q[r->qh];
    uint8_t len = r->qlen[r->qh];
    if (r->p->lbt && r->slot_state == 0) {
        int clear = r->phy->cca(r->phy->ctx);
        r->in_rx = 1;
        if (!clear) {
            r->st.lbt_busy++;
            if (hopping(r)) {
                r->slot_state = -1;
                r->st.hops_skipped++;
            } else {   /* parked slave or a fixed channel: random back-off of 1-3 ms */
                uint32_t b = 1000u + r->env.rand32(r->env.ctx) % 2000u;
                r->backoff_until = phy_now_us() + b;
            }
            return;
        }
        r->slot_state = 1;
    }
    int res = r->phy->send(r->phy->ctx, f, len);
    if (res == 1) {   /* the driver wants a fresh CCA (after an RX period, or the COT is used up) */
        r->slot_state = 0;
        return;
    }
    r->in_rx = 0;
    r->tx_active = 1;
    if (res == 0)
        r->st.frames_tx++;
    else
        r->st.send_fail++;   /* lost like a frame on air: the protocol retransmits */
    pop(r);
}

/* A slave follows the master's hop timing from each frame it hears. */
static void follow(radio_t *r, uint64_t t_end, uint8_t len, int beacon)
{
    if (!r->fhss || r->master)
        return;
    int64_t t0 = (int64_t)t_end - (int64_t)air(r, len);   /* the frame's first bit */
    /* Which tuning heard it: a frame can be read after the next hop began (it waited in the FIFO). */
    uint8_t ch;
    int64_t k;
    uint64_t tuned;
    if (t0 >= (int64_t)r->tune_us) {
        ch = r->ch, k = r->cur_k, tuned = r->tune_us;
    } else if (t0 >= (int64_t)r->prev_tune_us) {
        ch = r->prev_ch, k = r->prev_k, tuned = r->prev_tune_us;
    } else {
        return;
    }
    int idx = idx_of(ch);
    if (idx < 0)
        return;
    int64_t slot = (int64_t)r->slot_us;
    int64_t c = t0 - (int64_t)r->hop_us;          /* latest possible start of the master's slot */
    int64_t lo = (int64_t)t_end - slot;           /* earliest: the frame ends inside the slot */
    r->last_heard = t_end;
    if (!r->synced || k < 0) {
        /* Acquisition. origin = start of hop 0 of a cycle in the past, so origin + K * slot is hop K. */
        int64_t K = (int64_t)idx + (int64_t)NRF24_FHSS_N;
        r->origin = (beacon ? c : lo + (c - lo) / 2) - K * slot;   /* a beacon marks the slot start exactly */
        r->synced = 1;
        r->st.syncs++;
        r->heard_k = K;
        r->heard_end = t_end;
        r->win_min = INT64_MAX;
        r->win_slots = 0;
        if (getenv("TEAMC_DEBUG_SYNC"))
            fprintf(stderr, "sync ACQUIRE idx=%d origin=%lld\n", idx, (long long)r->origin);
        return;
    }
    int64_t s = r->origin + k * slot;   /* our estimate of that hop's start */
    int64_t shift = 0;
    int first = k != r->heard_k;        /* the first frame we hear in this slot */
    int late = first && t0 < (int64_t)tuned + (int64_t)NRF24_TX_SETTLE_US + (int64_t)RADIO_GUARD_US / 2 + 300;
    if (beacon) {
        shift = c - s;   /* the beacon opens the master's slot: no guessing */
    } else if (late && r->heard_k == k - 1 && (int64_t)r->heard_end < c && (int64_t)r->heard_end + slot > c) {
        /* We tuned in mid-burst: the slot began between the last frame heard (previous slot) and this one. */
        shift = (int64_t)r->heard_end + (c - (int64_t)r->heard_end) / 2 - s;
    } else if (c < s) {
        shift = c - s;   /* heard earlier than predicted: the hop began at least that early */
    }
    if (shift) {
        r->win_min = c - (s + shift);   /* offsets are relative to the estimate: start the window again */
        r->win_slots = 0;
    } else {
        if (c - s < r->win_min)
            r->win_min = c - s;
        if (first && ++r->win_slots >= RADIO_WIN_SLOTS) {
            /* No frame in the last slots began less than win_min after our estimate + PLL + CCA: the hop
             * starts at least that much later (drift, or an early estimate). Move by exactly that. */
            if (r->win_min > 0)
                shift = r->win_min;
            r->win_min = INT64_MAX;
            r->win_slots = 0;
        }
    }
    if (getenv("TEAMC_DEBUG_SYNC"))
        fprintf(stderr, "sync k=%lld idx=%d heard_k=%lld late=%d len=%u t0-tuned=%lld c-s=%lld shift=%lld origin=%lld\n",
                (long long)k, idx, (long long)r->heard_k, (int)(t0 < (int64_t)tuned + 930), len,
                (long long)(t0 - (int64_t)tuned), (long long)(c - s), (long long)shift, (long long)(r->origin + shift));
    r->origin += shift;
    r->heard_k = k;
    r->heard_end = t_end;
}

static void rx_frame(radio_t *r, const uint8_t *f, uint8_t len, uint64_t t_end, uint8_t rpd)
{
    int beacon = len == 1 && f[0] == RADIO_BEACON;
    follow(r, t_end, len, beacon);
    if (beacon)
        return;   /* radio layer only */
    r->st.frames_rx++;
    if (r->h.on_frame)
        r->h.on_frame(r->h.proto, f, len, rpd);
}

/* Master, hopping: hop 0 of the cycle opens with the beacon (after settling + CCA, if the hop is clear). */
static int beacon_due(const radio_t *r, uint64_t now)
{
    if (!r->fhss || !r->master || r->cur_k < 0 || r->cur_k % (int64_t)NRF24_FHSS_N || r->beacon_k == r->cur_k ||
        r->slot_state < 0)
        return 0;
    uint64_t s = slot_start(r, r->cur_k);
    return now >= s + r->hop_us && now + NRF24_TX_SETTLE_US + air(r, 1) <= slot_start(r, r->cur_k + 1);
}

static void send_beacon(radio_t *r)
{
    if (r->slot_state == 0) {
        r->in_rx = 1;
        if (!r->phy->cca(r->phy->ctx)) {
            r->slot_state = -1;   /* busy: no beacon and no frames on this hop */
            r->st.lbt_busy++;
            r->st.hops_skipped++;
            return;
        }
        r->slot_state = 1;
    }
    const uint8_t b = RADIO_BEACON;
    int res = r->phy->send(r->phy->ctx, &b, 1);
    if (res == 1) {
        r->slot_state = 0;   /* needs a fresh CCA */
        return;
    }
    r->beacon_k = r->cur_k;
    r->in_rx = 0;
    if (res == 0)
        r->st.beacons++;
}

void radio_run(radio_t *r, uint64_t until)
{
    for (;;) {
        uint64_t now = phy_now_us();
        if (now >= until)
            return;
        if (r->fhss && !r->master && r->synced &&
            now > r->last_heard + (uint64_t)NRF24_FHSS_N * r->slot_us) {
            r->synced = 0;   /* a silent cycle: lost the master (or it rebooted on a new phase), park again */
            r->st.sync_lost++;
        }
        tune(r, now);
        if (beacon_due(r, now)) {
            send_beacon(r);
            continue;
        }
        if (r->timer_at != PROTO_NO_TIMER && now >= r->timer_at) {
            r->timer_at = PROTO_NO_TIMER;
            if (r->h.on_timer)
                r->h.on_timer(r->h.proto);
            continue;
        }
        uint64_t next = until;
        if (r->qn) {
            uint64_t t = tx_ready(r, now);
            if (t <= now) {
                tx_one(r);
                continue;
            }
            if (t < next)
                next = t;
        } else if (r->tx_active) {
            r->tx_active = 0;
            r->phy->start_rx(r->phy->ctx);
            r->in_rx = 1;
            if (r->h.on_tx_idle)
                r->h.on_tx_idle(r->h.proto);
            continue;
        }
        if (r->timer_at < next)
            next = r->timer_at;
        if (hopping(r)) {
            uint64_t b = slot_start(r, slot_of(r, now) + 1);
            if (b < next)
                next = b;
        }
        if (!r->in_rx) {
            r->phy->start_rx(r->phy->ctx);
            r->in_rx = 1;
            if (r->p->lbt && r->slot_state > 0)
                r->slot_state = 0;   /* listening ends the occupancy: the next frame needs a new CCA (a busy hop stays skipped) */
        }
        uint8_t f[32], len = 0, rpd = 0;
        uint64_t t_end = 0;
        if (r->phy->recv(r->phy->ctx, next, f, &len, &t_end, &rpd) == 1)
            rx_frame(r, f, len, t_end, rpd);
    }
}

/* ------------------------------------------------------------------ env */

static void env_send(void *ctx, const uint8_t *frame, uint8_t len)
{
    radio_t *r = ctx;
    if (len == 0 || len > 32u)
        return;
    while (r->qn == RADIO_QCAP) {   /* never drop (proto_env.h): drain without listening */
        r->st.q_full++;
        uint64_t now = phy_now_us();
        tune(r, now);
        uint64_t t = tx_ready(r, now);
        if (t > now) {
            phy_sleep_until(t);
            continue;
        }
        tx_one(r);
    }
    unsigned slot = (r->qh + r->qn++) % RADIO_QCAP;
    memcpy(r->q[slot], frame, len);
    r->qlen[slot] = len;
}

static uint64_t env_now(void *ctx)
{
    (void)ctx;
    return phy_now_us();
}

static void env_set_timer(void *ctx, uint64_t at) { ((radio_t *)ctx)->timer_at = at; }

static uint32_t env_rand32(void *ctx)
{
    (void)ctx;
    uint32_t v;
    if (getrandom(&v, sizeof v, GRND_NONBLOCK) == (ssize_t)sizeof v)
        return v;
    static uint64_t s = 0x9E3779B97F4A7C15ULL;
    s ^= phy_now_us();
    s ^= s >> 12;
    s ^= s << 25;
    s ^= s >> 27;
    return (uint32_t)((s * 2685821657736338717ULL) >> 32);
}

void radio_init(radio_t *r, phy_t *phy, int master)
{
    memset(r, 0, sizeof *r);
    r->phy = phy;
    r->p = phy->profile;
    r->fhss = phy->profile->hop;
    r->master = master;
    r->synced = master;
    r->slot_us = NRF24_FHSS_SLOT_US;
    r->hop_us = NRF24_TX_SETTLE_US + NRF24_FHSS_CCA_US;
    r->origin = (int64_t)phy_now_us();
    r->ch = phy->profile->rf_ch;
    r->cur_k = -2;
    r->beacon_k = -1;
    r->timer_at = PROTO_NO_TIMER;
    r->env.ctx = r;
    r->env.send = env_send;
    r->env.now_us = env_now;
    r->env.set_timer = env_set_timer;
    r->env.rand32 = env_rand32;
    if (r->fhss && master && getenv("TEAMC_DEBUG_SYNC"))
        fprintf(stderr, "sync MASTER origin=%lld\n", (long long)r->origin);
    if (r->fhss) {
        r->ch = 0xFF;   /* force the first tune */
        tune(r, phy_now_us());
    }
}

const proto_env_t *radio_env(radio_t *r) { return &r->env; }

void radio_set_hooks(radio_t *r, const radio_hooks_t *h) { r->h = *h; }

void radio_stop(radio_t *r)
{
    r->qn = 0;
    r->qh = 0;
    r->timer_at = PROTO_NO_TIMER;
    r->tx_active = 0;
    r->phy->start_rx(r->phy->ctx);
    r->in_rx = 1;
}
