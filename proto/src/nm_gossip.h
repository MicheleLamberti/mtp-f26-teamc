/* MTP-F26 Team C - Network Mode gossip (draft inter-team standard).
 *
 * No routing, addresses or positions: every node rebroadcasts all chunks of the
 * NM file it holds, on a Trickle timer (RFC 6206): interval I from imin doubling
 * to imax, one transmission point at a random time in [I/2, I), suppressed when
 * enough duplicate frames were heard in the interval. Hearing a new chunk resets
 * I to imin, so the file spreads fast and the channel goes quiet once everyone
 * has it. Frames: [0x4E][file_id:2][idx][total][data <= 25][crc16:2].
 */
#ifndef NM_GOSSIP_H
#define NM_GOSSIP_H

#include <stdint.h>

#include "frames.h"
#include "proto_env.h"

#define NM_MAX_CHUNKS 64u   /* 64 x 25 B = 1600 B: the ~0.5 KB NM file, or its 5 lines in UTF-16 */

typedef struct {
    uint32_t imin_us, imax_us;
    uint8_t k;              /* suppress when >= k x total duplicate frames heard */
} nm_cfg_t;

void nm_cfg_default(nm_cfg_t *cfg);

typedef struct {
    uint32_t tx_frames, rx_new, rx_dup, rx_bad_crc, rx_other_file, suppressed;
    uint32_t broadcasts;    /* transmission points where we sent everything we hold */
    uint32_t rx_bad_file;   /* all chunks held but the whole-file CRC-16 != file_id: started over */
} nm_stats_t;

#define NM_NEVER 0xFFFFFFFFu

/* Relay evidence for the NM log (nm_log.h): times in ms since nm_init (= GO). The rules make a team an NM
 * winner by "delivering a copy of the NM-file from at least one of their node devices"; this record shows
 * how our copy arrived and that the node relayed it. */
typedef struct {
    uint8_t origin;                    /* 1 = this node loaded the file from USB (SW corner) */
    uint32_t first_rx_ms, last_rx_ms;  /* first / last valid NM frame heard */
    uint32_t first_tx_ms, last_tx_ms;  /* first / last own broadcast */
    uint32_t chunk_ms[NM_MAX_CHUNKS];  /* when each chunk was first held */
} nm_trace_t;

typedef struct {
    const proto_env_t *env;
    nm_cfg_t cfg;
    uint16_t file_id;
    uint8_t total;          /* 0 = nothing heard yet */
    uint64_t have;          /* bit idx: chunk held */
    uint8_t data[NM_MAX_CHUNKS][NM_CHUNK];
    uint8_t clen[NM_MAX_CHUNKS];
    uint8_t active, phase;
    uint32_t interval_us, dup_count;
    uint64_t end_at;
    uint64_t complete_at;   /* PROTO_NO_TIMER until every chunk is held */
    uint64_t start_at;      /* nm_init time: GO */
    nm_stats_t st;
    nm_trace_t tr;
} nm_t;

void nm_init(nm_t *n, const proto_env_t *env, const nm_cfg_t *cfg);
/* Origin node: load the file and start gossiping. Returns -1 if it is too large. */
int nm_set_file(nm_t *n, const uint8_t *file, uint32_t len);
int nm_complete(const nm_t *n);
uint32_t nm_get_file(const nm_t *n, uint8_t *out, uint32_t cap);
void nm_on_frame(nm_t *n, const uint8_t *f, uint8_t len);
void nm_on_timer(nm_t *n);

#endif /* NM_GOSSIP_H */
