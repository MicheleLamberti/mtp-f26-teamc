/* MTP-F26 Team C - Network Mode relay log. See nm_log.h. */
#include "nm_log.h"

#include <stdarg.h>
#include <stdio.h>

uint32_t nm_log_crc32(const uint8_t *p, uint32_t len)
{
    uint32_t c = 0xFFFFFFFFu;
    for (uint32_t i = 0; i < len; i++) {
        c ^= p[i];
        for (int k = 0; k < 8; k++)
            c = (c >> 1) ^ (0xEDB88320u & (0u - (c & 1u)));
    }
    return ~c;
}

typedef struct {
    char *buf;
    size_t cap, len;
    int full;
} out_t;

static void put(out_t *o, const char *fmt, ...)
{
    if (o->full)
        return;
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(o->buf + o->len, o->cap - o->len, fmt, ap);
    va_end(ap);
    if (n < 0 || (size_t)n >= o->cap - o->len)
        o->full = 1;
    else
        o->len += (size_t)n;
}

/* "12.345 s" or "never" */
static void put_time(out_t *o, uint32_t ms)
{
    if (ms == NM_NEVER)
        put(o, "never");
    else
        put(o, "%lu.%03lu s", (unsigned long)(ms / 1000u), (unsigned long)(ms % 1000u));
}

size_t nm_log_format(const nm_t *n, const nm_log_info_t *info, char *buf, size_t cap)
{
    out_t o = {buf, cap, 0, 0};
    if (cap == 0)
        return 0;
    buf[0] = '\0';
    static uint8_t file[NM_MAX_CHUNKS * NM_CHUNK];   /* static: keep it off the small Pico stack */
    uint32_t held = 0, len = nm_get_file(n, file, sizeof file);
    for (uint32_t i = 0; i < n->total; i++)
        held += (n->have >> i) & 1u;

    put(&o, "MTP-F26 NM relay log\r\n");
    put(&o, "team: %s   box: %s   firmware: %s\r\n", info->team, info->box, info->firmware);
    put(&o, "role: %s\r\n", n->tr.origin ? "origin (file loaded from USB)" : "relay");
    if (n->total == 0) {
        put(&o, "NM-file: nothing heard\r\n");
    } else if (nm_complete(n)) {
        put(&o, "NM-file: COMPLETE, id 0x%04X, %u chunks, %lu bytes, CRC-32 %08lX\r\n", n->file_id, n->total,
            (unsigned long)len, (unsigned long)nm_log_crc32(file, len));
        if (info->file_name && info->file_name[0])
            put(&o, "copy on this stick: %s\r\n", info->file_name);
    } else {
        put(&o, "NM-file: INCOMPLETE, id 0x%04X, %lu of %u chunks; missing:", n->file_id, (unsigned long)held,
            n->total);
        for (uint32_t i = 0; i < n->total; i++)
            if (!((n->have >> i) & 1u))
                put(&o, " %lu", (unsigned long)i);
        put(&o, "\r\n");
    }
    put(&o, "times from GO: first frame heard ");
    put_time(&o, n->tr.first_rx_ms);
    put(&o, ", file complete ");
    put_time(&o, n->complete_at == PROTO_NO_TIMER ? NM_NEVER : (uint32_t)((n->complete_at - n->start_at) / 1000u));
    put(&o, ", last frame heard ");
    put_time(&o, n->tr.last_rx_ms);
    put(&o, "\r\n");
    put(&o, "relayed: %lu broadcasts, %lu frames sent, first ", (unsigned long)n->st.broadcasts,
        (unsigned long)n->st.tx_frames);
    put_time(&o, n->tr.first_tx_ms);
    put(&o, ", last ");
    put_time(&o, n->tr.last_tx_ms);
    put(&o, "\r\n");
    put(&o, "heard: %lu new chunks, %lu duplicates, %lu bad CRC, %lu other file; %lu broadcasts suppressed\r\n",
        (unsigned long)n->st.rx_new, (unsigned long)n->st.rx_dup, (unsigned long)n->st.rx_bad_crc,
        (unsigned long)n->st.rx_other_file, (unsigned long)n->st.suppressed);
    if (n->total) {
        put(&o, "chunk first held (s from GO):");
        for (uint32_t i = 0; i < n->total; i++) {
            put(&o, "%s%lu:", i % 8u == 0u ? "\r\n " : " ", (unsigned long)i);
            if (n->tr.chunk_ms[i] == NM_NEVER)
                put(&o, "-");
            else
                put(&o, "%lu.%03lu", (unsigned long)(n->tr.chunk_ms[i] / 1000u),
                    (unsigned long)(n->tr.chunk_ms[i] % 1000u));
        }
        put(&o, "\r\n");
    }
    return o.full ? 0 : o.len;
}
