/* MTP-F26 Team C - USB stick file I/O. See usb_msc.h. */
#include "usb_msc.h"

#include <string.h>

uint32_t usbm_crc32(uint32_t crc, const uint8_t *p, uint32_t n)
{
    uint32_t c = ~crc;
    for (uint32_t i = 0; i < n; i++) {
        c ^= p[i];
        for (int k = 0; k < 8; k++)
            c = (c >> 1) ^ (0xEDB88320u & (0u - (c & 1u)));
    }
    return ~c;
}

const char *usbm_strerror(usbm_status_t st)
{
    switch (st) {
    case USBM_OK: return "ok";
    case USBM_NO_MEDIA: return "no USB stick";
    case USBM_NO_FS: return "no FAT/exFAT volume";
    case USBM_NO_FILE: return "no .txt file";
    case USBM_TOO_BIG: return "file too big";
    case USBM_FULL: return "stick full";
    case USBM_IO: return "I/O error";
    case USBM_VERIFY: return "read-back mismatch";
    }
    return "?";
}

static usbm_status_t map(FRESULT fr)
{
    switch (fr) {
    case FR_OK: return USBM_OK;
    case FR_NOT_READY: return USBM_NO_MEDIA;
    case FR_NO_FILESYSTEM: return USBM_NO_FS;
    case FR_NO_FILE:
    case FR_NO_PATH: return USBM_NO_FILE;
    case FR_DENIED: return USBM_FULL;   /* f_write/f_open on a full volume or directory */
    default: return USBM_IO;
    }
}

usbm_status_t usbm_mount(usbm_t *u)
{
    u->mounted = 0;
    FRESULT fr = f_mount(&u->fs, "", 1);
    if (fr == FR_OK)
        u->mounted = 1;
    return map(fr);
}

void usbm_unmount(usbm_t *u)
{
    f_mount(NULL, "", 0);
    u->mounted = 0;
}

static int ends_with_txt(const char *s)
{
    size_t n = strlen(s);
    if (n < 4)
        return 0;
    const char *e = s + n - 4;
    return e[0] == '.' && (e[1] | 0x20) == 't' && (e[2] | 0x20) == 'x' && (e[3] | 0x20) == 't';
}

static int same_name(const char *a, const char *b)
{
    for (; *a && *b; a++, b++) {
        char x = *a, y = *b;
        if (x >= 'A' && x <= 'Z')
            x = (char)(x + 32);
        if (y >= 'A' && y <= 'Z')
            y = (char)(y + 32);
        if (x != y)
            return 0;
    }
    return *a == *b;
}

usbm_status_t usbm_find_input(usbm_t *u, const char *skip, char *name, size_t cap, uint32_t *size,
                              uint32_t *count)
{
    (void)u;
    DIR dir;
    FILINFO fi;
    uint32_t best = 0, seen = 0;
    int found = 0;
    FRESULT fr = f_opendir(&dir, "/");
    if (fr != FR_OK)
        return map(fr);
    for (;;) {
        fr = f_readdir(&dir, &fi);
        if (fr != FR_OK || fi.fname[0] == '\0')
            break;
        if ((fi.fattrib & (AM_DIR | AM_HID | AM_SYS)) || (fi.fname[0] == '.' && fi.fname[1] == '_') ||
            !ends_with_txt(fi.fname) || (skip && same_name(fi.fname, skip)))
            continue;
        seen++;
        if (fi.fsize > 0xFFFFFFFFu)
            continue;
        if (!found || (uint32_t)fi.fsize > best) {
            size_t n = strlen(fi.fname);
            if (n + 1 > cap)
                continue;
            memcpy(name, fi.fname, n + 1);
            best = (uint32_t)fi.fsize;
            found = 1;
        }
    }
    f_closedir(&dir);
    if (count)
        *count = seen;
    if (fr != FR_OK)
        return map(fr);
    if (!found)
        return USBM_NO_FILE;
    if (size)
        *size = best;
    return USBM_OK;
}

usbm_status_t usbm_load(usbm_t *u, const char *name, uint32_t max_len, usbm_sink_fn sink, void *ctx,
                        uint32_t *len, uint32_t *crc32)
{
    FRESULT fr = f_open(&u->fil, name, FA_READ);
    if (fr != FR_OK)
        return map(fr);
    usbm_status_t st = USBM_OK;
    FSIZE_t size = f_size(&u->fil);
    uint32_t off = 0, crc = 0;
    if (size > max_len) {
        st = USBM_TOO_BIG;
        goto out;
    }
    while (off < size) {
        UINT want = (UINT)(size - off < USBM_CHUNK ? size - off : USBM_CHUNK), got = 0;
        fr = f_read(&u->fil, u->buf, want, &got);
        if (fr != FR_OK || got != want) {
            st = fr != FR_OK ? map(fr) : USBM_IO;
            goto out;
        }
        if (sink(ctx, off, u->buf, got)) {
            st = USBM_IO;
            goto out;
        }
        crc = usbm_crc32(crc, u->buf, got);
        off += got;
    }
out:
    f_close(&u->fil);
    if (len)
        *len = off;
    if (crc32)
        *crc32 = crc;
    return st;
}

static usbm_status_t crc_of_file(usbm_t *u, const char *name, uint32_t len, uint32_t *crc)
{
    FRESULT fr = f_open(&u->fil, name, FA_READ);
    if (fr != FR_OK)
        return map(fr);
    usbm_status_t st = USBM_OK;
    uint32_t c = 0, off = 0;
    if (f_size(&u->fil) != len)
        st = USBM_VERIFY;
    while (st == USBM_OK && off < len) {
        UINT want = len - off < USBM_CHUNK ? len - off : USBM_CHUNK, got = 0;
        fr = f_read(&u->fil, u->buf, want, &got);
        if (fr != FR_OK || got != want)
            st = fr != FR_OK ? map(fr) : USBM_VERIFY;
        else {
            c = usbm_crc32(c, u->buf, got);
            off += got;
        }
    }
    f_close(&u->fil);
    *crc = c;
    return st;
}

usbm_status_t usbm_save(usbm_t *u, const char *name, uint32_t len, usbm_source_fn source, void *ctx,
                        uint32_t *crc32)
{
    /* Write "<name>.part", verify it, then rename: the final name only ever holds a complete, verified file,
     * even if the stick fails or is pulled half-way. */
    char tmp[FF_MAX_LFN + 1];
    size_t nl = strlen(name);
    if (nl + 5 > FF_MAX_LFN)
        return USBM_IO;
    memcpy(tmp, name, nl);
    memcpy(tmp + nl, ".part", 6);
    FRESULT fr = f_open(&u->fil, tmp, FA_CREATE_ALWAYS | FA_WRITE);
    if (fr != FR_OK)
        return map(fr);
    usbm_status_t st = USBM_OK;
    uint32_t off = 0, crc = 0;
    while (off < len) {
        UINT n = len - off < USBM_CHUNK ? len - off : USBM_CHUNK, put = 0;
        if (source(ctx, off, u->buf, n)) {
            st = USBM_IO;
            break;
        }
        fr = f_write(&u->fil, u->buf, n, &put);
        if (fr != FR_OK || put != n) {
            st = fr != FR_OK ? map(fr) : USBM_FULL;   /* short write = volume full */
            break;
        }
        crc = usbm_crc32(crc, u->buf, n);
        off += n;
    }
    fr = f_close(&u->fil);   /* flushes the data and the directory entry */
    if (st == USBM_OK && fr != FR_OK)
        st = map(fr);
    if (crc32)
        *crc32 = crc;
    uint32_t back = 0;
    if (st == USBM_OK) {
        st = crc_of_file(u, tmp, len, &back);
        if (st == USBM_OK && back != crc)
            st = USBM_VERIFY;
    }
    if (st == USBM_OK) {
        fr = f_unlink(name);   /* replace an older copy */
        if (fr != FR_OK && fr != FR_NO_FILE)
            st = map(fr);
    }
    if (st == USBM_OK && (fr = f_rename(tmp, name)) != FR_OK)
        st = map(fr);
    if (st != USBM_OK)
        f_unlink(tmp);   /* best effort: the stick may be gone */
    return st;
}

typedef struct {
    const uint8_t *p;
} memsrc_t;

static int mem_source(void *ctx, uint32_t off, uint8_t *p, uint32_t n)
{
    memcpy(p, ((const memsrc_t *)ctx)->p + off, n);
    return 0;
}

usbm_status_t usbm_save_buf(usbm_t *u, const char *name, const uint8_t *data, uint32_t len)
{
    memsrc_t m = {data};
    return usbm_save(u, name, len, mem_source, &m, NULL);
}
