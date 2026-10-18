/* MTP-F26 Team C - persistent storage of the Linux node, on the SD card's data partition.
 *
 * The root file system is read-only (overlayfs) so a power cut or the drop test cannot corrupt it; this
 * directory (default /var/lib/teamc) is on a small ext4 partition that is written:
 *   rx.bin / rx.state   what the receiver got (link_rx_store_t). The radio thread pwrite()s every committed
 *                       frame; a sync thread fdatasync()s the data and then records `committed` in one of
 *                       two CRC-checked slots of rx.state (alternating, so a torn write keeps the other).
 *                       After a reboot the receiver resumes from the last synced length: anything after it is
 *                       simply requested again. A new file invalidates the record before the data is cut.
 *   in.bin, in.meta     the file loaded from the stick at setup (raw), kept for NM and for reloading;
 *   tx.bin, tx.meta     what the sender transmits (deflated, or raw when that is not smaller);
 *   nm_rx.bin           the NM-file once complete (a rebooted relay keeps relaying it);
 *   round.state         the round in progress, so a reboot resumes it instead of waiting for GO.
 * Whole files are written atomically: temp file, fsync, rename, fsync of the directory.
 */
#ifndef STORE_H
#define STORE_H

#include <pthread.h>
#include <stdint.h>

#include "link.h"

#define STORE_RX_CAP (4u << 20)

typedef struct {
    uint8_t valid, done, codec;
    uint32_t len, crc32, committed;
    char name[HELLO_NAME_MAX + 1];
} store_hdr_t;

typedef struct {
    char dir[200];
    int data_fd, state_fd;
    link_rx_store_t rx;      /* give &rx to link_rx_init */
    pthread_t th;
    pthread_mutex_t mu;
    int run, started;
    store_hdr_t snap;        /* published by the radio thread (store_publish) */
    store_hdr_t written;     /* last record on disk */
    uint32_t seq;
    unsigned sync_ms;
} store_t;

/* Creates dir if needed, loads the last record and the received bytes, starts the sync thread. */
int store_open(store_t *s, const char *dir, unsigned sync_ms);
void store_close(store_t *s);
/* Radio thread: make the current receiver state visible to the sync thread (cheap; call often). */
void store_publish(store_t *s);
/* Publish and write the record now (STOP). */
void store_flush(store_t *s);
/* A new round: forget the received file. */
void store_reset_rx(store_t *s);

/* Whole files in the directory. store_get mallocs *p (caller frees); returns 0 or -1. */
int store_put(store_t *s, const char *name, const void *p, uint32_t n);
int store_get(store_t *s, const char *name, uint8_t **p, uint32_t *n);
void store_del(store_t *s, const char *name);

#endif /* STORE_H */
