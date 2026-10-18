/* MTP-F26 Team C - radio layer of the Linux node: transmit queue, proto_env_t, and the D-R6 hop clock.
 *
 * The protocol modules (link.c, nm_gossip.c) see a proto_env_t: send() queues a frame, frames go out in
 * order, on_tx_idle runs when the queue has drained, and one timer per instance. radio_run() is the event
 * loop of the radio thread: it transmits what is queued when the channel allows it, listens otherwise, and
 * calls the hooks.
 *
 * Hopping profiles (TEAM_FHSS, hop = 1) follow NRF24_FHSS_HOPSEQ in slots of NRF24_FHSS_SLOT_US:
 *   - the master (the link's sender) hops on its own clock;
 *   - a slave parks on NRF24_FHSS_HOPSEQ[0] until it hears a frame there, then follows the master. Frames
 *     carry no slot number: the channel tells the slave which hop it heard, and the frame's timing bounds
 *     where the master's slot began (no frame starts before slot start + PLL settling + CCA, none ends after
 *     the slot). The estimate:
 *       acquisition       the middle of the interval the first frame allows;
 *       earlier           a frame that began earlier than the estimate allows moves it earlier at once;
 *       late arrival      the first frame came right after we tuned in, so we missed the start: the slot began
 *                         between the end of the last frame heard in the previous slot and this frame; take the
 *                         middle (the error halves every slot);
 *       later             only by the smallest offset any frame showed over RADIO_WIN_SLOTS heard slots (a
 *                         burst often waits for a fresh hop, so some frame starts right after one): never past
 *                         the true start, whatever frames were lost or bursts began mid-slot.
 *     The slave switches RADIO_GUARD_US early, so a small error still catches the master's first frame. One
 *     silent hop cycle: back to parking (a rebooted master restarts on a new phase).
 *   - the master opens hop 0 of every cycle (the parking channel) with a 1-byte beacon, PLL settling + CCA
 *     after the slot start: a parked slave acquires within one cycle (1.1 s) even while the link is silent
 *     (HELLO back-off), and exactly (the beacon's timing is the slot start). The radio layer eats it: one
 *     byte is never a protocol frame. Cost: ~0.4 ms of air per 1.1 s.
 *   - every node runs a CCA on each hop before its first frame (and again after any RX period, as the
 *     driver demands); a busy hop is skipped. A frame never crosses a hop boundary.
 */
#ifndef RADIO_H
#define RADIO_H

#include <stdint.h>

#include "phy.h"
#include "proto_env.h"

#define RADIO_QCAP 64u
#define RADIO_GUARD_US 1000u    /* slave: change channel this much before the estimated hop start */
#define RADIO_WIN_SLOTS 8u      /* slave: heard slots before the estimate may move later */
#define RADIO_BEACON 0x3Fu      /* the master's 1-byte hop-0 beacon */

typedef struct {
    void *proto;
    void (*on_frame)(void *proto, const uint8_t *f, uint8_t len, uint8_t rssi);
    void (*on_timer)(void *proto);
    void (*on_tx_idle)(void *proto);   /* may be NULL */
} radio_hooks_t;

typedef struct {
    uint32_t frames_tx, frames_rx, send_fail, lbt_busy, hops_skipped, syncs, sync_lost, q_full, beacons;
} radio_stats_t;

typedef struct {
    phy_t *phy;
    const nrf24_profile_t *p;
    int fhss, master, synced, in_rx, tx_active;
    uint32_t slot_us, hop_us;
    int64_t origin;         /* slot k starts at origin + k * slot_us (a slave's estimate of the master's) */
    uint64_t last_heard, backoff_until;
    uint8_t ch;             /* channel tuned now */
    int64_t cur_k;          /* hop slot tuned now (-1: none / parked) */
    uint64_t tune_us;       /* when we tuned to cur_k */
    uint8_t prev_ch;        /* the tuning before (frames can be read after the hop changed) */
    int64_t prev_k;
    uint64_t prev_tune_us;
    int64_t heard_k;        /* slave: slot of the last frame heard */
    uint64_t heard_end;     /* slave: end of that frame */
    int64_t win_min;        /* slave: smallest (frame start - PLL - CCA - estimated hop start) of the window */
    unsigned win_slots;     /* slave: heard slots in the window */
    int64_t beacon_k;       /* master: hop-0 slot whose beacon went out */
    int slot_state;         /* this hop: 0 = no CCA yet, 1 = clear, -1 = busy (skip it) */
    uint8_t q[RADIO_QCAP][32];
    uint8_t qlen[RADIO_QCAP];
    unsigned qh, qn;
    proto_env_t env;
    uint64_t timer_at;
    radio_hooks_t h;
    radio_stats_t st;
} radio_t;

/* master = 1 for the link's sender (and for NM, where nothing hops). */
void radio_init(radio_t *r, phy_t *phy, int master);
const proto_env_t *radio_env(radio_t *r);
void radio_set_hooks(radio_t *r, const radio_hooks_t *h);
/* Run the radio and the protocol until until_us (CLOCK_MONOTONIC us). */
void radio_run(radio_t *r, uint64_t until_us);
/* STOP: drop the queue and the timer, leave the radio listening. */
void radio_stop(radio_t *r);
/* Channel this node uses at time t (for logs and tests). */
uint8_t radio_channel_at(const radio_t *r, uint64_t t);

#endif /* RADIO_H */
