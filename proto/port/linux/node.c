/* MTP-F26 Team C - the transceiver program of the Raspberry Pi 3 box (D-H1).
 *
 * One process, started by systemd at boot (teamc-node.service), runs a whole competition round:
 *   SETUP  wait for a stick: load the largest .txt (usb_msc), deflate it, keep both on the SD card
 *          (store.h). Status LED on = a file is loaded.
 *   GO     Tx/Rx button: read the role switch (TX/RX) and the mode switch (SRI / MRM / NM), remember the
 *          round (round.state) and start the protocol on the radio:
 *            SRI, MRM: link.c sender (role TX) or receiver (role RX); SRI on --sri-profile (TEAM_250K),
 *                      MRM on --mrm-profile (TEAM_FHSS, 20 dBm hopping, the sender's clock leads);
 *            NM:       nm_gossip.c on NM_COMMON; role TX = the origin (holds the NM-file from the stick).
 *          The activity LED blinks while in Tx/Rx (rule).
 *   STOP   the button again: stop transmitting; then write what we got to the stick (the receiver's file,
 *          or NM_FILE.TXT + NM_LOG.TXT) with a read-back check. Status LED on = saved.
 * A reboot in the middle of a round (watchdog, brown-out, an "attack") resumes it without a button press:
 * the sender restarts from its stored file, the receiver from the last synced length (HELLO resume).
 *
 *   teamc-node [--radio nrf24|udp:<port>:<peer>[,<peer>]] [--stick /dev/sda] [--stick-out PATH]
 *              [--data /var/lib/teamc] [--box C1] [--sri-profile P] [--mrm-profile P] [--rt CPU]
 *              [--spidev ..] [--gpiochip ..] [--ce N] [--irq N] [--i2c /dev/i2c-1] [--out-name NAME]
 *   test options: --sim-ui tx|rx sri|mrm|nm  --go-after S  --stop-after S  --exit-after-save
 *                 --loss P --busy P --seed N (udp radio)
 */
#define _GNU_SOURCE
#include <errno.h>
#include <signal.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#include "codec.h"
#include "encoding_stream_c.h"
#include "link.h"
#include "nm_gossip.h"
#include "nm_log.h"
#include "nrf24_hal_linux.h"
#include "phy.h"
#include "radio.h"
#include "stick.h"
#include "store.h"
#include "ui.h"
#include "usb_msc.h"

#define FIRMWARE "teamc-node 0.2 (Pi 3, file/Unicode layer)"
#define MAX_FILE (4u << 20)
#define NM_FILE_NAME "NM_FILE.TXT"
#define NM_LOG_NAME "NM_LOG.TXT"

static const nrf24_profile_t *const PROFILES[] = {&NRF24_PROFILE_TEAM_250K, &NRF24_PROFILE_TEAM_1M,
                                                  &NRF24_PROFILE_NM_COMMON, &NRF24_PROFILE_TEAM_FHSS,
                                                  &NRF24_PROFILE_TEAM_20DBM_FIXED};

typedef struct {
    const char *radio, *stick, *stick_out, *data, *box, *out_name, *i2c, *gpiochip;
    const char *text_encoding, *text_bom_policy;
    const nrf24_profile_t *sri, *mrm;
    phy_nrf24_opts_t nrf;
    phy_udp_opts_t udp;
    int sim_ui, sim_role_tx, rt_cpu, exit_after_save;
    node_mode_t sim_mode;
    double go_after, stop_after;
} opts_t;

static volatile sig_atomic_t quit;
static uint64_t t_start;

static void logf_(const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    fprintf(stderr, "[%8.3f] ", (double)(phy_now_us() - t_start) / 1e6);
    vfprintf(stderr, fmt, ap);
    fputc('\n', stderr);
    va_end(ap);
}

static const char *mode_name(node_mode_t m) { return m == MODE_NM ? "NM" : m == MODE_MRM ? "MRM" : "SRI"; }

/* systemd: READY=1 at start, WATCHDOG=1 at least every WatchdogSec/2 (without libsystemd). */
static void sd_notify_msg(const char *msg)
{
    const char *p = getenv("NOTIFY_SOCKET");
    if (!p)
        return;
    struct sockaddr_un a;
    memset(&a, 0, sizeof a);
    a.sun_family = AF_UNIX;
    size_t l = strlen(p);
    if (l == 0 || l >= sizeof a.sun_path)
        return;
    memcpy(a.sun_path, p, l);
    if (a.sun_path[0] == '@')
        a.sun_path[0] = '\0';
    int fd = socket(AF_UNIX, SOCK_DGRAM | SOCK_CLOEXEC, 0);
    if (fd < 0)
        return;
    sendto(fd, msg, strlen(msg), 0, (struct sockaddr *)&a, (socklen_t)(offsetof(struct sockaddr_un, sun_path) + l));
    close(fd);
}

static void on_signal(int sig)
{
    if (sig == SIGUSR1)
        ui_signal_press();
    else
        quit = 1;
}

/* ------------------------------------------------------------ small files */

typedef struct {
    char name[256];
    uint32_t len, crc, codec, raw_len;
} meta_t;

static int meta_put(store_t *s, const char *file, const meta_t *m)
{
    char b[400];
    int n = snprintf(b, sizeof b, "name=%s\nlen=%u\ncrc=%u\ncodec=%u\nraw_len=%u\n", m->name, m->len, m->crc,
                     m->codec, m->raw_len);
    return store_put(s, file, b, (uint32_t)n);
}

static int meta_get(store_t *s, const char *file, meta_t *m)
{
    uint8_t *p;
    uint32_t n;
    memset(m, 0, sizeof *m);
    if (store_get(s, file, &p, &n))
        return -1;
    char *t = calloc(1, n + 1u);
    memcpy(t, p, n);
    free(p);
    for (char *line = strtok(t, "\n"); line; line = strtok(NULL, "\n")) {
        if (!strncmp(line, "name=", 5))
            snprintf(m->name, sizeof m->name, "%s", line + 5);
        else
            sscanf(line, "len=%u", &m->len), sscanf(line, "crc=%u", &m->crc), sscanf(line, "codec=%u", &m->codec),
                sscanf(line, "raw_len=%u", &m->raw_len);
    }
    free(t);
    return 0;
}

typedef struct {
    int active;
    node_mode_t mode;
    int role_tx;
} round_t;

static void round_put(store_t *s, const round_t *r)
{
    char b[128];
    int n = snprintf(b, sizeof b, "active=%d\nmode=%d\nrole_tx=%d\n", r->active, (int)r->mode, r->role_tx);
    store_put(s, "round.state", b, (uint32_t)n);
}

static void round_get(store_t *s, round_t *r)
{
    uint8_t *p;
    uint32_t n;
    memset(r, 0, sizeof *r);
    if (store_get(s, "round.state", &p, &n))
        return;
    char t[128];
    uint32_t k = n < sizeof t - 1u ? n : (uint32_t)sizeof t - 1u;
    memcpy(t, p, k);
    t[k] = '\0';
    free(p);
    int mode = 0;
    sscanf(t, "active=%d\nmode=%d\nrole_tx=%d", &r->active, &mode, &r->role_tx);
    r->mode = mode == 2 ? MODE_NM : mode == 1 ? MODE_MRM : MODE_SRI;
}

/* ---------------------------------------------------------------- stick */

/* These fixed cache names belong to the application, never to the USB directory.
 * The C++ layer checks the staged file before replacing a previous cache. */
static int cache_path(store_t *st, const char *name, char *path, size_t capacity)
{
    int n = snprintf(path, capacity, "%s/%s", st->dir, name);
    return n < 0 || (size_t)n >= capacity ? -1 : 0;
}

static int cache_write(store_t *st, const char *name, const uint8_t *p, uint32_t len, uint32_t crc)
{
    char path[256], error[256];
    if (cache_path(st, name, path, sizeof path))
        return -1;
    mtp_text_file_info expected = {len, crc};
    if (mtp_text_write_cache(path, p, expected, error, sizeof error)) {
        logf_("file cache %s: %s", name, error);
        return -1;
    }
    return 0;
}

static int cache_read(store_t *st, const char *name, const meta_t *m, uint8_t **p)
{
    char path[256], error[256];
    *p = NULL;
    if (m->len > MAX_FILE || cache_path(st, name, path, sizeof path))
        return -1;
    uint8_t *bytes = malloc(m->len ? m->len : 1u);
    if (!bytes)
        return -1;
    mtp_text_file_info expected = {m->len, m->crc};
    if (mtp_text_read_verified(path, expected, bytes, m->len, error, sizeof error)) {
        logf_("file cache %s: %s", name, error);
        free(bytes);
        return -1;
    }
    *p = bytes;
    return 0;
}

/* Text is an optional view on an already verified cache. An unresolved or invalid
 * encoding never changes the original bytes or prevents their USB hand-in. */
static void process_text(const opts_t *o, store_t *st, const char *base, int complete)
{
    char raw_name[64], json_name[64], text_name[64], source[256], destination[256];
    char report[2048], error[256];
    snprintf(raw_name, sizeof raw_name, "%s.bin", base);
    snprintf(json_name, sizeof json_name, "%s.encoding.json", base);
    snprintf(text_name, sizeof text_name, "%s.utf8.txt", base);
    store_del(st, json_name);
    store_del(st, text_name); /* A previous round's decoded text must not appear current. */
    if (!complete || !strcmp(o->text_encoding, "none")) {
        logf_("text %s: %s", base, complete ? "decoding disabled" : "partial file; decoding deferred");
        return;
    }
    if (cache_path(st, raw_name, source, sizeof source) ||
        cache_path(st, text_name, destination, sizeof destination))
        return;
    if (mtp_text_inspect(source, report, sizeof report, error, sizeof error)) {
        logf_("text %s: inspection failed: %s", base, error);
        return;
    }
    if (store_put(st, json_name, report, (uint32_t)strlen(report)))
        logf_("text %s: cannot save encoding report", base);
    logf_("text %s: %s", base, report);
    if (mtp_text_decode_cache(source, destination, o->text_encoding, o->text_bom_policy, error, sizeof error))
        logf_("text %s: UTF-8 view unavailable: %s", base, error);
    else
        logf_("text %s: UTF-8 view saved as %s (original bytes preserved)", base, text_name);
}

typedef struct {
    uint8_t *buf;
    uint32_t cap;
} mem_sink_t;

static int mem_sink(void *ctx, uint32_t off, const uint8_t *p, uint32_t n)
{
    mem_sink_t *m = ctx;
    if ((uint64_t)off + n > m->cap)
        return -1;
    memcpy(m->buf + off, p, n);
    return 0;
}

/* SETUP: the largest .txt on the stick -> in.bin (raw) and tx.bin (what the sender transmits). */
static int load_from_stick(const opts_t *o, store_t *st)
{
    stick_t sk;
    usbm_disk_t d;
    if (stick_open(&sk, o->stick, &d))
        return -1;
    usbm_set_disk(&d);
    usbm_t *u = calloc(1, sizeof *u);
    mem_sink_t m = {malloc(MAX_FILE), MAX_FILE};
    char name[256];
    uint32_t size = 0, count = 0, len = 0, crc = 0;
    usbm_status_t r = u && m.buf ? usbm_mount(u) : USBM_IO;
    if (r == USBM_OK)
        r = usbm_find_input(u, NM_LOG_NAME, name, sizeof name, &size, &count);
    if (r == USBM_OK)
        r = usbm_load(u, name, MAX_FILE, mem_sink, &m, &len, &crc);
    if (u && u->mounted)
        usbm_unmount(u);
    stick_close(&sk);
    free(u);
    if (r != USBM_OK) {
        logf_("setup: stick %s: %s", o->stick, usbm_strerror(r));
        free(m.buf);
        return r == USBM_NO_FILE ? 1 : -1;
    }
    meta_t in = {{0}, len, crc, CODEC_NONE, len};
    snprintf(in.name, sizeof in.name, "%s", name);
    store_del(st, "in.meta");
    store_del(st, "tx.meta");
    if (cache_write(st, "in.bin", m.buf, len, crc)) {
        free(m.buf);
        return -1;
    }

    /* One deflate stream at level 9; raw when that does not save at least 5 %. */
    uint8_t *z = NULL;
    uint32_t zlen = 0;
    meta_t tx = in;
    if (codec_deflate(m.buf, len, 9, &z, &zlen) == 0 && (uint64_t)zlen * 100u < (uint64_t)len * 95u) {
        tx.codec = CODEC_DEFLATE;
        tx.len = zlen;
        tx.crc = codec_crc32(z, zlen);
    } else {
        tx.crc = codec_crc32(m.buf, len);
    }
    if (cache_write(st, "tx.bin", tx.codec == CODEC_DEFLATE ? z : m.buf, tx.len, tx.crc) ||
        meta_put(st, "in.meta", &in) || meta_put(st, "tx.meta", &tx)) {
        store_del(st, "in.meta");
        store_del(st, "tx.meta");
        free(z);
        free(m.buf);
        return -1;
    }
    process_text(o, st, "in", 1);
    logf_("setup: loaded %s (%u B, %u .txt on the stick) -> %u B to send (%s, %.2fx)", name, len, count, tx.len,
          tx.codec == CODEC_DEFLATE ? "deflate" : "raw", tx.len ? (double)len / tx.len : 0.0);
    free(z);
    free(m.buf);
    return 0;
}

typedef struct {
    const char *name;
    const uint8_t *p;
    uint32_t n;
} out_file_t;

/* SAVE: write the files to the stick (read-back checked). 0 = all saved. */
static int save_to_stick(const char *path, const out_file_t *files, unsigned n_files)
{
    stick_t sk;
    usbm_disk_t d;
    if (stick_open(&sk, path, &d))
        return -1;
    usbm_set_disk(&d);
    usbm_t *u = calloc(1, sizeof *u);
    usbm_status_t r = u ? usbm_mount(u) : USBM_IO;
    for (unsigned i = 0; r == USBM_OK && i < n_files; i++) {
        r = usbm_save_buf(u, files[i].name, files[i].p, files[i].n);
        logf_("save: %s (%u B) to %s: %s", files[i].name, files[i].n, path, usbm_strerror(r));
    }
    if (u && u->mounted)
        usbm_unmount(u);
    stick_close(&sk);
    free(u);
    if (r != USBM_OK)
        logf_("save: %s: %s", path, usbm_strerror(r));
    return r == USBM_OK ? 0 : -1;
}

/* ---------------------------------------------------------------- round */

static void h_tx_frame(void *p, const uint8_t *f, uint8_t len, uint8_t rssi)
{
    (void)rssi;
    link_tx_on_frame(p, f, len);
}
static void h_tx_timer(void *p) { link_tx_on_timer(p); }
static void h_tx_idle(void *p) { link_tx_on_tx_idle(p); }
static void h_rx_frame(void *p, const uint8_t *f, uint8_t len, uint8_t rssi) { link_rx_on_frame(p, f, len, rssi); }
static void h_rx_timer(void *p) { link_rx_on_timer(p); }
static void h_nm_frame(void *p, const uint8_t *f, uint8_t len, uint8_t rssi)
{
    (void)rssi;
    nm_on_frame(p, f, len);
}
static void h_nm_timer(void *p) { nm_on_timer(p); }

typedef struct {
    const opts_t *o;
    store_t *st;
    ui_t *ui;
    round_t round;
    phy_t phy;
    radio_t radio;
    link_tx_t tx;
    link_rx_t rx;
    nm_t nm;
    link_cfg_t cfg;
    uint8_t *tx_data;
    meta_t tx_meta;
    int nm_saved, done_logged;
    uint64_t go_us;
} run_t;

static int open_radio(run_t *R, const nrf24_profile_t *p)
{
    char err[200];
    int r = strcmp(R->o->radio, "nrf24") == 0 ? phy_nrf24_open(&R->phy, &R->o->nrf, p, err, sizeof err)
                                              : phy_udp_open(&R->phy, &R->o->udp, p, err, sizeof err);
    if (r)
        logf_("radio: %s", err);
    return r;
}

/* GO (fresh = 1) or resume after a reboot (fresh = 0). Returns 0 when the radio runs. */
static int start_round(run_t *R, int fresh)
{
    const opts_t *o = R->o;
    node_mode_t mode = R->round.mode;
    int tx = R->round.role_tx;
    const nrf24_profile_t *p = mode == MODE_NM ? &NRF24_PROFILE_NM_COMMON : mode == MODE_MRM ? o->mrm : o->sri;
    if (open_radio(R, p))
        return -1;
    R->go_us = phy_now_us();
    R->done_logged = 0;
    radio_init(&R->radio, &R->phy, tx || mode == MODE_NM);
    const proto_env_t *env = radio_env(&R->radio);
    if (p->hop)
        link_cfg_for_fhss(&R->cfg, p->bitrate_bps, NRF24_FHSS_SLOT_US);
    else
        link_cfg_for_bitrate(&R->cfg, p->bitrate_bps);
    logf_("%s %s: %s%s, profile %s", fresh ? "GO" : "resume", mode_name(mode),
          mode == MODE_NM ? (tx ? "origin" : "relay") : (tx ? "sender" : "receiver"), fresh ? "" : " (after a reboot)",
          p->name);

    if (mode == MODE_NM) {
        nm_cfg_t nc;
        nm_cfg_default(&nc);
        nm_init(&R->nm, env, &nc);
        uint8_t *f = NULL;
        uint32_t n = 0;
        meta_t in;
        int loaded = 0;
        if (tx && meta_get(R->st, "in.meta", &in) == 0 && cache_read(R->st, "in.bin", &in, &f) == 0) {
            n = in.len;
            loaded = 1;
        } else if (!tx && store_get(R->st, "nm_rx.bin", &f, &n) == 0) {
            loaded = 1;
        }
        if (loaded) {
            if (nm_set_file(&R->nm, f, n))
                logf_("NM: the file (%u B) is larger than %u chunks of %u B", n, NM_MAX_CHUNKS, NM_CHUNK);
            else
                logf_("NM: gossiping our copy (%u B)", n);
        } else if (tx) {
            logf_("NM: origin without a file: load the NM-file from a stick at setup");
        }
        free(f);
        R->nm_saved = nm_complete(&R->nm);
        radio_hooks_t h = {&R->nm, h_nm_frame, h_nm_timer, NULL};
        radio_set_hooks(&R->radio, &h);
    } else if (tx) {
        uint32_t n = 0;
        if (meta_get(R->st, "tx.meta", &R->tx_meta) || cache_read(R->st, "tx.bin", &R->tx_meta, &R->tx_data)) {
            logf_("sender without a file: load one from a stick at setup");
            R->phy.close(R->phy.ctx);
            return -1;
        }
        n = R->tx_meta.len;
        link_tx_init(&R->tx, env, &R->cfg, R->tx_data, n, R->tx_meta.crc, (uint8_t)R->tx_meta.codec, R->tx_meta.name);
        radio_hooks_t h = {&R->tx, h_tx_frame, h_tx_timer, h_tx_idle};
        radio_set_hooks(&R->radio, &h);
        link_tx_start(&R->tx);
    } else {
        if (fresh)
            store_reset_rx(R->st);
        else if (R->st->rx.valid)
            logf_("receiver: resuming %s at %u of %u B", R->st->rx.name, R->st->rx.committed, R->st->rx.len);
        link_rx_init(&R->rx, env, &R->cfg, &R->st->rx);
        radio_hooks_t h = {&R->rx, h_rx_frame, h_rx_timer, NULL};
        radio_set_hooks(&R->radio, &h);
    }
    return 0;
}

static void progress(run_t *R)
{
    const radio_stats_t *s = &R->radio.st;
    if (R->round.mode == MODE_NM)
        logf_("NM: %s, %u chunks held of %u, %u frames sent / %u heard", nm_complete(&R->nm) ? "complete" : "partial",
              (unsigned)__builtin_popcountll(R->nm.have), R->nm.total, s->frames_tx, s->frames_rx);
    else if (R->round.role_tx)
        logf_("sender: %u of %u frames acknowledged%s; %u sent, %u retx, %u timeouts; radio %u tx %u rx, %u hops skipped",
              R->tx.base, R->tx.n_frames, R->tx.state == LTX_DONE ? " (done)" : "", R->tx.st.frames, R->tx.st.retx,
              R->tx.st.timeouts, s->frames_tx, s->frames_rx, s->hops_skipped);
    else
        logf_("receiver: %u of %u B%s; radio %u rx %u tx, syncs %u, lost %u, hops skipped %u", R->st->rx.committed,
              R->st->rx.len, R->st->rx.done ? " (complete)" : "", s->frames_rx, s->frames_tx, s->syncs, s->sync_lost,
              s->hops_skipped);
}

/* Until STOP (button) or quit. Returns 1 on STOP. */
static int run_round(run_t *R)
{
    uint64_t last_log = 0, last_wd = 0, last_bat = 0;
    for (;;) {
        uint64_t now = phy_now_us();
        radio_run(&R->radio, now + 20000u);
        now = phy_now_us();
        if (R->round.mode != MODE_NM && !R->round.role_tx)
            store_publish(R->st);
        int done = R->round.mode == MODE_NM ? nm_complete(&R->nm)
                   : R->round.role_tx    ? R->tx.state == LTX_DONE
                                         : R->st->rx.valid && R->st->rx.committed == R->st->rx.len;
        ui_leds(R->ui, (int)((now / 250000u) & 1u), done);   /* pilot light blinks while in Tx/Rx */
        if (done && !R->done_logged) {
            R->done_logged = 1;
            logf_("DONE after %.2f s of the round", (double)(now - R->go_us) / 1e6);
        }
        if (R->round.mode == MODE_NM && done && !R->nm_saved) {
            uint8_t f[NM_MAX_CHUNKS * NM_CHUNK];
            uint32_t n = nm_get_file(&R->nm, f, sizeof f);
            R->nm_saved = store_put(R->st, "nm_rx.bin", f, n) == 0;
            logf_("NM: file complete (%u B), kept on the SD card", n);
        }
        if (now - last_wd >= 1000000u) {
            sd_notify_msg("WATCHDOG=1");
            last_wd = now;
        }
        if (now - last_log >= 5000000u) {
            progress(R);
            last_log = now;
        }
        if (now - last_bat >= 10000000u) {
            int mv = ui_battery_mv(R->ui);
            if (mv > 0 && mv < 3400)
                logf_("battery LOW: %d mV (charge before the next round)", mv);
            last_bat = now;
        }
        if (ui_pressed(R->ui, now))
            return 1;
        if (quit)
            return 0;
    }
}

static void stop_round(run_t *R)
{
    radio_stop(&R->radio);
    progress(R);
    R->phy.close(R->phy.ctx);
    if (R->round.mode != MODE_NM && !R->round.role_tx)
        store_flush(R->st);
    R->round.active = 0;
    round_put(R->st, &R->round);
    logf_("STOP");
}

/* After STOP: the receiver's file, or the NM copy and log, onto a stick. Returns when saved (or quit). */
static int save_round(run_t *R)
{
    const opts_t *o = R->o;
    const char *path = o->stick_out ? o->stick_out : o->stick;
    out_file_t files[2];
    unsigned n = 0;
    uint8_t *raw = NULL;
    char log[NM_LOG_MAX], name[HELLO_NAME_MAX * 4 + 8];
    uint8_t nmf[NM_MAX_CHUNKS * NM_CHUNK];
    if (R->round.mode == MODE_NM) {
        uint32_t len = nm_complete(&R->nm) ? nm_get_file(&R->nm, nmf, sizeof nmf) : 0;
        nm_log_info_t info = {"Team C", o->box, FIRMWARE, len ? NM_FILE_NAME : ""};
        size_t ll = nm_log_format(&R->nm, &info, log, sizeof log);
        if (len) {
            if (cache_write(R->st, "received.bin", nmf, len, codec_crc32(nmf, len)))
                return -1;
            process_text(o, R->st, "received", 1);
            files[n++] = (out_file_t){NM_FILE_NAME, nmf, len};
        }
        files[n++] = (out_file_t){NM_LOG_NAME, (const uint8_t *)log, (uint32_t)ll};
    } else if (!R->round.role_tx) {
        link_rx_store_t *s = &R->st->rx;
        uint32_t len = s->committed;
        const uint8_t *data = s->buf;
        int complete = s->valid && s->committed == s->len;
        if (complete && codec_crc32(s->buf, s->committed) != s->crc32) {
            logf_("receiver: complete stream failed CRC-32; refusing to save corrupt data");
            return -1;
        }
        if (s->codec != CODEC_NONE && s->codec != CODEC_DEFLATE) {
            logf_("receiver: unsupported codec %u", s->codec);
            return -1;
        }
        if (s->codec == CODEC_DEFLATE) {
            raw = malloc(MAX_FILE);
            if (!raw || (complete && codec_inflate_complete(s->buf, s->committed, raw, MAX_FILE, &len))) {
                logf_("receiver: cannot recover a complete deflate stream");
                free(raw);
                return -1;
            }
            if (!complete)
                len = codec_inflate_prefix(s->buf, s->committed, raw, MAX_FILE);
            data = raw;
        }
        if (o->out_name)
            snprintf(name, sizeof name, "%s", o->out_name);
        else
            snprintf(name, sizeof name, "RX_%s", s->name[0] ? s->name : "FILE.TXT");
        logf_("receiver: %u B received in order%s -> %s, %u B", s->committed, s->done ? " (complete)" : "", name, len);
        if (s->valid) {
            const char *base = complete ? "received" : "received-prefix";
            const char *cache = complete ? "received.bin" : "received-prefix.bin";
            if (!complete) {
                store_del(R->st, "received.utf8.txt");
                store_del(R->st, "received.encoding.json");
            }
            if (cache_write(R->st, cache, data, len, codec_crc32(data, len))) {
                free(raw);
                return -1;
            }
            process_text(o, R->st, base, complete);
            files[n++] = (out_file_t){name, data, len};
        }
    }
    if (!n) {
        free(raw);
        return 0;   /* the sender has nothing to hand in */
    }
    logf_("save: plug in the stick (%s)", path);
    int saved = 0, tried = 0;
    while (!quit && !saved) {
        uint64_t now = phy_now_us();
        ui_leds(R->ui, 0, (int)((now / 100000u) & 1u));   /* fast blink: waiting for a stick */
        if (stick_present(path) && !tried) {
            saved = save_to_stick(path, files, n) == 0;
            tried = !saved;   /* failed (full, locked): wait for another stick */
        } else if (!stick_present(path)) {
            tried = 0;
        }
        if (ui_pressed(R->ui, now)) {
            logf_("save: skipped by the button");
            break;
        }
        sd_notify_msg("WATCHDOG=1");
        usleep(200000);
    }
    if (saved) {
        logf_("save: done, the stick can be removed");
        ui_leds(R->ui, 0, 1);
    }
    free(raw);
    return saved ? 0 : -1;
}

/* ---------------------------------------------------------------- main */

static const nrf24_profile_t *profile_by_name(const char *n)
{
    for (unsigned i = 0; i < sizeof PROFILES / sizeof PROFILES[0]; i++)
        if (!strcmp(n, PROFILES[i]->name))
            return PROFILES[i];
    return NULL;
}

static void usage(void)
{
    fprintf(stderr, "usage: teamc-node [--radio nrf24|udp:PORT:PEER[,PEER]] [--stick DEV] [--stick-out DEV] [--data DIR]\n"
                    "  [--box NAME] [--sri-profile P] [--mrm-profile P] [--out-name NAME] [--rt CPU] [--i2c DEV]\n"
                    "  [--spidev DEV] [--spi-hz HZ] [--gpiochip DEV] [--ce N] [--irq N]\n"
                    "  [--text-encoding auto|none|utf-8|utf-16-le|utf-16-be|utf-32-le|utf-32-be]\n"
                    "  [--text-bom-policy strict|longest] (decoded UTF-8 copies stay on the SD card)\n"
                    "  tests: [--sim-ui tx|rx sri|mrm|nm] [--go-after S] [--stop-after S] [--exit-after-save]\n"
                    "         [--loss P] [--busy P] [--seed N]\n");
}

static int parse(opts_t *o, int argc, char **argv)
{
    memset(o, 0, sizeof *o);
    o->radio = "nrf24";
    o->stick = "/dev/sda";
    o->data = "/var/lib/teamc";
    o->box = "C1";
    o->text_encoding = "auto";
    o->text_bom_policy = "strict";
    o->gpiochip = "/dev/gpiochip0";
    o->i2c = "/dev/i2c-1";
    o->sri = &NRF24_PROFILE_TEAM_250K;
    o->mrm = &NRF24_PROFILE_TEAM_FHSS;
    /* SPI at 4 MHz (3.9 MHz with core_freq=250): rev B's ribbon returns the SPI current on pins 6/9/14 only
       (hw/teamc-carrier-lab, review 23-Oct); a 32-byte frame still moves in ~70 us. --spi-hz after T2. */
    o->nrf = (phy_nrf24_opts_t){"/dev/spidev0.0", "/dev/gpiochip0", 4000000u, 22u, 24};
    o->udp.seed = 1;
    o->rt_cpu = -1;
    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        if (!strcmp(a, "--exit-after-save")) {
            o->exit_after_save = 1;
            continue;
        }
        if (i + 1 >= argc)
            return -1;
        const char *v = argv[++i];
        if (!strcmp(a, "--radio")) {
            o->radio = v;
            o->udp.spec = v;
        } else if (!strcmp(a, "--stick")) {
            o->stick = v;
        } else if (!strcmp(a, "--stick-out")) {
            o->stick_out = v;
        } else if (!strcmp(a, "--data")) {
            o->data = v;
        } else if (!strcmp(a, "--box")) {
            o->box = v;
        } else if (!strcmp(a, "--out-name")) {
            o->out_name = v;
        } else if (!strcmp(a, "--text-encoding")) {
            if (strcmp(v, "auto") && strcmp(v, "none") && strcmp(v, "utf-8") && strcmp(v, "utf-16-le") &&
                strcmp(v, "utf-16-be") && strcmp(v, "utf-32-le") && strcmp(v, "utf-32-be"))
                return -1;
            o->text_encoding = v;
        } else if (!strcmp(a, "--text-bom-policy")) {
            if (strcmp(v, "strict") && strcmp(v, "longest"))
                return -1;
            o->text_bom_policy = v;
        } else if (!strcmp(a, "--i2c")) {
            o->i2c = v;
        } else if (!strcmp(a, "--rt")) {
            o->rt_cpu = atoi(v);
        } else if (!strcmp(a, "--spidev")) {
            o->nrf.spidev = v;
        } else if (!strcmp(a, "--spi-hz")) {
            unsigned long hz = strtoul(v, NULL, 0);
            if (hz < 100000ul || hz > 10000000ul)   /* nRF24L01+: SPI up to 10 MHz */
                return -1;
            o->nrf.spi_hz = (uint32_t)hz;
        } else if (!strcmp(a, "--gpiochip")) {
            o->gpiochip = v;
            o->nrf.gpiochip = v;
        } else if (!strcmp(a, "--ce")) {
            o->nrf.ce_gpio = (unsigned)atoi(v);
        } else if (!strcmp(a, "--irq")) {
            o->nrf.irq_gpio = atoi(v);
        } else if (!strcmp(a, "--sri-profile") || !strcmp(a, "--mrm-profile")) {
            const nrf24_profile_t *p = profile_by_name(v);
            if (!p)
                return -1;
            if (a[2] == 's')
                o->sri = p;
            else
                o->mrm = p;
        } else if (!strcmp(a, "--sim-ui")) {
            if (i + 1 >= argc)
                return -1;
            const char *m = argv[++i];
            o->sim_ui = 1;
            o->sim_role_tx = !strcmp(v, "tx");
            o->sim_mode = !strcmp(m, "nm") ? MODE_NM : !strcmp(m, "mrm") ? MODE_MRM : MODE_SRI;
        } else if (!strcmp(a, "--go-after")) {
            o->go_after = atof(v);
        } else if (!strcmp(a, "--stop-after")) {
            o->stop_after = atof(v);
        } else if (!strcmp(a, "--loss")) {
            o->udp.loss = atof(v);
        } else if (!strcmp(a, "--busy")) {
            o->udp.busy = atof(v);
        } else if (!strcmp(a, "--seed")) {
            o->udp.seed = (uint32_t)strtoul(v, NULL, 0);
        } else {
            return -1;
        }
    }
    return 0;
}

int main(int argc, char **argv)
{
    opts_t o;
    if (parse(&o, argc, argv)) {
        usage();
        return 2;
    }
    t_start = phy_now_us();
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_handler = on_signal;
    sigaction(SIGUSR1, &sa, NULL);
    sigaction(SIGTERM, &sa, NULL);
    sigaction(SIGINT, &sa, NULL);

    store_t st;
    if (store_open(&st, o.data, 200)) {
        logf_("cannot open the data directory %s: %s", o.data, strerror(errno));
        return 1;
    }
    ui_t ui;
    char err[200];
    if (o.sim_ui) {
        ui_open_sim(&ui, o.sim_role_tx, o.sim_mode);
        if (o.go_after > 0)
            ui_sim_press_at(&ui, t_start + (uint64_t)(o.go_after * 1e6));
        if (o.stop_after > 0)
            ui_sim_press_at(&ui, t_start + (uint64_t)(o.stop_after * 1e6));
    } else if (ui_open_gpio(&ui, o.gpiochip, err, sizeof err)) {
        logf_("ui: %s", err);
        return 1;
    }
    if (ui_battery_open(&ui, o.i2c) == 0)
        logf_("battery: %d mV", ui_battery_mv(&ui));
    if (o.rt_cpu >= 0) {   /* after the store's sync thread exists: only this (radio) thread is real-time */
        nrf24_linux_t lx;
        memset(&lx, 0, sizeof lx);
        if (nrf24_linux_realtime(&lx, o.rt_cpu, 80))
            logf_("warning: %s", lx.err);
    }
    logf_("%s, box %s, data %s, stick %s, radio %s", FIRMWARE, o.box, o.data, o.stick, o.radio);
    sd_notify_msg("READY=1");

    run_t *R = calloc(1, sizeof *R);
    R->o = &o;
    R->st = &st;
    R->ui = &ui;
    round_get(&st, &R->round);
    int resume = R->round.active;
    int rc = 0;
    while (!quit) {
        if (!resume) {   /* SETUP */
            meta_t in;
            int loaded = meta_get(&st, "in.meta", &in) == 0, stick_seen = 0;
            logf_("setup: %s; waiting for GO", loaded ? in.name : "no file loaded");
            for (;;) {
                uint64_t now = phy_now_us();
                int present = stick_present(o.stick);
                if (present && !stick_seen) {
                    stick_seen = 1;
                    int result = load_from_stick(&o, &st);
                    loaded = result == 0 || meta_get(&st, "in.meta", &in) == 0;
                } else if (!present) {
                    stick_seen = 0;
                }
                ui_leds(&ui, 0, loaded);
                sd_notify_msg("WATCHDOG=1");
                if (ui_pressed(&ui, now) || quit)
                    break;
                usleep(50000);
            }
            if (quit)
                break;
            R->round.active = 1;
            R->round.mode = ui_mode(&ui);
            R->round.role_tx = ui_role_tx(&ui);
            round_put(&st, &R->round);
        }
        if (start_round(R, !resume)) {
            R->round.active = 0;
            round_put(&st, &R->round);
            resume = 0;
            if (o.exit_after_save) {
                rc = 1;
                break;
            }
            continue;
        }
        resume = 0;
        if (!run_round(R))
            break;   /* quit: the round stays active, so the next start resumes it */
        stop_round(R);
        int save_result = save_round(R);
        free(R->tx_data);
        R->tx_data = NULL;
        if (o.exit_after_save) {
            rc = save_result ? 1 : 0;
            break;
        }
    }
    ui_close(&ui);
    store_close(&st);
    free(R);
    return rc;
}
