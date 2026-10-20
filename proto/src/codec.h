/* MTP-F26 Team C - file compression, zlib API, streaming.
 *
 * The whole file is one deflate stream (best ratio; delivery is in order). The streaming calls move it in
 * CODEC_CHUNK pieces between a source and a sink, so on the Pico the 1 MB file never sits in RAM: deflate
 * reads the original from flash and writes the compressed stream to flash during the 5-minute setup; the
 * receiver inflates its received prefix from flash straight into usbm_save at STOP.
 *
 * The PC simulator links the system zlib. On the Pico, miniz provides the same z_stream API (zlib-compatible
 * names); build it with TDEFL_LESS_MEMORY=1: deflate state ~170 KB, inflate ~45 KB (32 KB window), both well
 * inside the RP2350's 520 KB. (Window bits stay at 15: miniz supports no other.) Measure time and RAM on the
 * bench (proto/README.md, "Not done yet"). */
#ifndef CODEC_H
#define CODEC_H

#include <stdint.h>

#define CODEC_CHUNK 4096u

/* Source: copy n bytes at offset off into p; sink: take n bytes for offset off. Return 0 on success. */
typedef int (*codec_src_fn)(void *ctx, uint32_t off, uint8_t *p, uint32_t n);
typedef int (*codec_sink_fn)(void *ctx, uint32_t off, const uint8_t *p, uint32_t n);

/* Compress in_len bytes from src into sink. Returns 0 on success, *out_len = compressed bytes. */
int codec_deflate_stream(uint32_t in_len, codec_src_fn src, void *sctx, codec_sink_fn sink, void *kctx,
                         int level, uint32_t *out_len);
/* Inflate as much of a (possibly truncated) stream as possible, up to out_cap bytes. Returns bytes produced. */
uint32_t codec_inflate_stream(uint32_t in_len, codec_src_fn src, void *sctx, codec_sink_fn sink, void *kctx,
                              uint32_t out_cap);

/* Convenience wrappers over memory buffers (the simulator), built on the streaming calls. */
int codec_deflate(const uint8_t *in, uint32_t n, int level, uint8_t **out, uint32_t *out_len);
uint32_t codec_inflate_prefix(const uint8_t *in, uint32_t n, uint8_t *out, uint32_t cap);
/* Complete files must reach the zlib end/checksum, consume all input and fit cap. */
int codec_inflate_complete(const uint8_t *in, uint32_t n, uint8_t *out, uint32_t cap, uint32_t *out_len);
uint32_t codec_crc32(const uint8_t *data, uint32_t n);

#endif /* CODEC_H */
