/* MTP-F26 Team C - persistent storage of the Linux node. See store.h. */
#define _GNU_SOURCE
#include "store.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#include "codec.h"

#define SLOT 64u
#define MAGIC 0x54435354u   /* "TCST" */

static void put32(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)(v >> 24);
    p[1] = (uint8_t)(v >> 16);
    p[2] = (uint8_t)(v >> 8);
    p[3] = (uint8_t)v;
}

static uint32_t get32(const uint8_t *p)
{
    return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 | (uint32_t)p[2] << 8 | p[3];
}

static void path(const store_t *s, const char *name, char *out, size_t cap)
{
    snprintf(out, cap, "%s/%s", s->dir, name);
}

/* One record: magic, seq, flags, len, crc32, committed, name, CRC-32 of the first 60 bytes. */
static void encode(uint8_t *b, const store_hdr_t *h, uint32_t seq)
{
    memset(b, 0, SLOT);
    put32(b, MAGIC);
    put32(b + 4, seq);
    b[8] = h->valid;
    b[9] = h->done;
    b[10] = h->codec;
    put32(b + 12, h->len);
    put32(b + 16, h->crc32);
    put32(b + 20, h->committed);
    memcpy(b + 24, h->name, HELLO_NAME_MAX + 1);
    put32(b + 60, codec_crc32(b, 60));
}

static int decode(const uint8_t *b, store_hdr_t *h, uint32_t *seq)
{
    if (get32(b) != MAGIC || get32(b + 60) != codec_crc32(b, 60))
        return -1;
    *seq = get32(b + 4);
    h->valid = b[8];
    h->done = b[9];
    h->codec = b[10];
    h->len = get32(b + 12);
    h->crc32 = get32(b + 16);
    h->committed = get32(b + 20);
    memcpy(h->name, b + 24, HELLO_NAME_MAX + 1);
    h->name[HELLO_NAME_MAX] = '\0';
    return 0;
}

/* Data first, then the record that points at it. Called with the lock not held. */
static void write_record(store_t *s, const store_hdr_t *h)
{
    if (h->valid)
        fdatasync(s->data_fd);
    uint8_t b[SLOT];
    s->seq++;
    encode(b, h, s->seq);
    if (pwrite(s->state_fd, b, SLOT, (off_t)(s->seq % 2u) * SLOT) == (ssize_t)SLOT)
        fdatasync(s->state_fd);
}

static void *sync_thread(void *arg)
{
    store_t *s = arg;
    for (;;) {
        struct timespec ts = {0, (long)s->sync_ms * 1000000L};
        nanosleep(&ts, NULL);
        pthread_mutex_lock(&s->mu);
        int run = s->run;
        store_hdr_t h = s->snap;
        int changed = memcmp(&h, &s->written, sizeof h) != 0;
        if (changed)
            s->written = h;
        /* Write under the lock: prepare() must not cut the data while a record for it is going out. */
        if (changed)
            write_record(s, &h);
        pthread_mutex_unlock(&s->mu);
        if (!run)
            return NULL;
    }
}

static void hdr_from_rx(store_hdr_t *h, const link_rx_store_t *rx)
{
    memset(h, 0, sizeof *h);
    h->valid = rx->valid;
    h->done = rx->done;
    h->codec = rx->codec;
    h->len = rx->len;
    h->crc32 = rx->crc32;
    h->committed = rx->committed;
    memcpy(h->name, rx->name, sizeof h->name);
}

/* link.c: a new file was announced. Invalidate the record on disk before the old data goes. */
static int st_prepare(void *ctx, uint32_t len)
{
    store_t *s = ctx;
    (void)len;
    pthread_mutex_lock(&s->mu);
    memset(&s->snap, 0, sizeof s->snap);
    s->written = s->snap;
    write_record(s, &s->snap);
    int r = ftruncate(s->data_fd, 0);
    pthread_mutex_unlock(&s->mu);
    return r;
}

static int st_commit(void *ctx, uint32_t off, const uint8_t *p, uint32_t n)
{
    store_t *s = ctx;
    if ((uint64_t)off + n > s->rx.cap)
        return -1;
    memcpy(s->rx.buf + off, p, n);
    return pwrite(s->data_fd, p, n, off) == (ssize_t)n ? 0 : -1;
}

int store_open(store_t *s, const char *dir, unsigned sync_ms)
{
    memset(s, 0, sizeof *s);
    snprintf(s->dir, sizeof s->dir, "%s", dir);
    s->sync_ms = sync_ms ? sync_ms : 200u;
    mkdir(dir, 0755);
    char p[256];
    path(s, "rx.bin", p, sizeof p);
    s->data_fd = open(p, O_RDWR | O_CREAT | O_CLOEXEC, 0644);
    path(s, "rx.state", p, sizeof p);
    s->state_fd = open(p, O_RDWR | O_CREAT | O_CLOEXEC, 0644);
    if (s->data_fd < 0 || s->state_fd < 0)
        return -1;
    s->rx.cap = STORE_RX_CAP;
    s->rx.buf = calloc(1, s->rx.cap);
    if (!s->rx.buf)
        return -1;
    s->rx.ctx = s;
    s->rx.prepare = st_prepare;
    s->rx.commit = st_commit;

    /* The newest good record of the two slots. */
    uint8_t b[2 * SLOT];
    memset(b, 0, sizeof b);
    ssize_t got = pread(s->state_fd, b, sizeof b, 0);
    store_hdr_t best, h;
    memset(&best, 0, sizeof best);
    uint32_t best_seq = 0, seq = 0;
    int have = 0;
    for (unsigned i = 0; got > 0 && i < 2; i++)
        if ((ssize_t)((i + 1) * SLOT) <= got && decode(b + i * SLOT, &h, &seq) == 0 && (!have || seq > best_seq)) {
            best = h;
            best_seq = seq;
            have = 1;
        }
    if (have) {
        s->seq = best_seq;
        if (best.valid) {
            struct stat st;
            uint32_t size = fstat(s->data_fd, &st) == 0 ? (uint32_t)st.st_size : 0u;
            if (best.committed > size)   /* never trust more than the data file holds */
                best.committed = size - size % DATA_PAYLOAD;
            if (best.committed > s->rx.cap)
                best.committed = s->rx.cap - s->rx.cap % DATA_PAYLOAD;
            if (pread(s->data_fd, s->rx.buf, best.committed, 0) != (ssize_t)best.committed)
                best.valid = 0;
        }
        if (best.valid) {
            s->rx.valid = 1;
            s->rx.done = best.done;
            s->rx.codec = best.codec;
            s->rx.len = best.len;
            s->rx.crc32 = best.crc32;
            s->rx.committed = best.committed;
            memcpy(s->rx.name, best.name, sizeof s->rx.name);
        }
    }
    hdr_from_rx(&s->snap, &s->rx);
    s->written = s->snap;
    pthread_mutex_init(&s->mu, NULL);
    s->run = 1;
    if (pthread_create(&s->th, NULL, sync_thread, s) != 0)
        return -1;
    s->started = 1;
    return 0;
}

void store_publish(store_t *s)
{
    store_hdr_t h;
    hdr_from_rx(&h, &s->rx);
    /* Never block the radio thread behind an SD-card sync (10-100 ms): publish next time instead. */
    if (pthread_mutex_trylock(&s->mu) != 0)
        return;
    s->snap = h;
    pthread_mutex_unlock(&s->mu);
}

void store_flush(store_t *s)
{
    store_hdr_t h;
    hdr_from_rx(&h, &s->rx);
    pthread_mutex_lock(&s->mu);
    s->snap = h;
    if (memcmp(&s->snap, &s->written, sizeof s->snap)) {
        s->written = s->snap;
        write_record(s, &s->snap);
    }
    pthread_mutex_unlock(&s->mu);
}

void store_reset_rx(store_t *s)
{
    st_prepare(s, 0);
    memset(s->rx.name, 0, sizeof s->rx.name);
    s->rx.valid = s->rx.done = s->rx.codec = 0;
    s->rx.len = s->rx.crc32 = s->rx.committed = 0;
    store_publish(s);
}

void store_close(store_t *s)
{
    if (s->started) {
        store_flush(s);
        pthread_mutex_lock(&s->mu);
        s->run = 0;
        pthread_mutex_unlock(&s->mu);
        pthread_join(s->th, NULL);
        pthread_mutex_destroy(&s->mu);
    }
    if (s->data_fd >= 0)
        close(s->data_fd);
    if (s->state_fd >= 0)
        close(s->state_fd);
    free(s->rx.buf);
    s->rx.buf = NULL;
}

int store_put(store_t *s, const char *name, const void *p, uint32_t n)
{
    char tmp[256], fin[256];
    snprintf(tmp, sizeof tmp, "%s/.%s.tmp", s->dir, name);
    path(s, name, fin, sizeof fin);
    int fd = open(tmp, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
    if (fd < 0)
        return -1;
    int ok = write(fd, p, n) == (ssize_t)n && fsync(fd) == 0;
    close(fd);
    if (!ok || rename(tmp, fin) != 0) {
        unlink(tmp);
        return -1;
    }
    int dfd = open(s->dir, O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (dfd >= 0) {
        fsync(dfd);
        close(dfd);
    }
    return 0;
}

int store_get(store_t *s, const char *name, uint8_t **p, uint32_t *n)
{
    char f[256];
    path(s, name, f, sizeof f);
    int fd = open(f, O_RDONLY | O_CLOEXEC);
    if (fd < 0)
        return -1;
    struct stat st;
    if (fstat(fd, &st) || st.st_size > (off_t)(64u << 20)) {
        close(fd);
        return -1;
    }
    *n = (uint32_t)st.st_size;
    *p = malloc(*n ? *n : 1u);
    int ok = *p && read(fd, *p, *n) == (ssize_t)*n;
    close(fd);
    if (!ok) {
        free(*p);
        *p = NULL;
        return -1;
    }
    return 0;
}

void store_del(store_t *s, const char *name)
{
    char f[256];
    path(s, name, f, sizeof f);
    unlink(f);
}
