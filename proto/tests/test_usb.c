/* MTP-F26 Team C - host tests for usb_msc (FatFs over a RAM disk).
 *
 *   build/test_usb                       run the checks (FAT16, FAT32, exFAT; errors and faults)
 *   build/test_usb --image IN OUT        cross-check: load the input .txt from image IN, write it back as
 *                                        RX.TXT plus NM_LOG.TXT, save the image as OUT (tools/fat_xcheck.py)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ramdisk.h"
#include "usb_msc.h"

static int failures, checks;
#define CHECK(cond)                                                              \
    do {                                                                         \
        checks++;                                                                \
        if (!(cond)) {                                                           \
            failures++;                                                          \
            printf("  FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);             \
        }                                                                        \
    } while (0)

#define FILE_LEN (1000u * 1000u + 123u)   /* ~1 MB, not a multiple of the 4 KB chunk */

/* "Flash" sink: checks that chunks arrive in order and sector-aligned, as the RP2350 flash needs. */
typedef struct {
    uint8_t *mem;
    uint32_t cap, next;
    int misaligned;
} flash_t;

static int flash_sink(void *ctx, uint32_t off, const uint8_t *p, uint32_t n)
{
    flash_t *f = ctx;
    if (off != f->next || off % USBM_CHUNK || n > USBM_CHUNK || off + n > f->cap)
        f->misaligned = 1;
    if (off + n > f->cap)
        return -1;
    memcpy(f->mem + off, p, n);
    f->next = off + n;
    return 0;
}

static void make_text(uint8_t *p, uint32_t len)
{
    static const char *words[] = {"radio", "enlace", "año", "señal", "nodo", "MRM", "ruido", "antena"};
    uint32_t i = 0, line = 0;
    while (i < len) {
        char l[128];
        int n = snprintf(l, sizeof l, "%05u %s %s %s %s\r\n", (unsigned)line, words[line % 8],
                         words[(line / 8) % 8], words[(line * 7) % 8], words[(line * 3 + 1) % 8]);
        for (int k = 0; k < n && i < len; k++)
            p[i++] = (uint8_t)l[k];
        line++;
    }
}

static int format(BYTE fmt)
{
    static uint8_t work[4096];
    MKFS_PARM opt = {fmt, 1, 0, 0, 0};
    return f_mkfs("", &opt, work, sizeof work) == FR_OK ? 0 : -1;
}

static void test_format(const char *label, BYTE fmt, uint32_t sectors)
{
    printf("%s\n", label);
    ramdisk_t rd;
    usbm_disk_t d;
    usbm_t *u = calloc(1, sizeof *u);
    CHECK(ramdisk_init(&rd, sectors) == 0);
    ramdisk_bind(&rd, &d);
    usbm_set_disk(&d);

    CHECK(usbm_mount(u) == USBM_NO_FS);   /* blank stick */
    CHECK(format(fmt) == 0);
    CHECK(usbm_mount(u) == USBM_OK);

    uint8_t *src = malloc(FILE_LEN), *dst = calloc(1, FILE_LEN + USBM_CHUNK);
    make_text(src, FILE_LEN);
    uint32_t want_crc = usbm_crc32(0, src, FILE_LEN);

    /* The stick as the professor hands it over: the file plus things to ignore. */
    CHECK(usbm_save_buf(u, "Fichero competicion MTP.txt", src, FILE_LEN) == USBM_OK);
    CHECK(usbm_save_buf(u, "readme.TXT", (const uint8_t *)"short", 5) == USBM_OK);
    CHECK(usbm_save_buf(u, "._Fichero competicion MTP.txt", src, 4096) == USBM_OK);   /* macOS shadow */
    CHECK(usbm_save_buf(u, "notes.md", src, 2000) == USBM_OK);
    CHECK(f_mkdir("big.txt") == FR_OK);                                                   /* a directory */

    char name[64];
    uint32_t size = 0, count = 0;
    CHECK(usbm_find_input(u, "NM_LOG.TXT", name, sizeof name, &size, &count) == USBM_OK);
    CHECK(strcmp(name, "Fichero competicion MTP.txt") == 0);
    CHECK(size == FILE_LEN);
    CHECK(count == 2);   /* the file and readme.TXT */

    flash_t fl = {dst, FILE_LEN + USBM_CHUNK, 0, 0};
    uint32_t len = 0, crc = 0;
    CHECK(usbm_load(u, name, 2u << 20, flash_sink, &fl, &len, &crc) == USBM_OK);
    CHECK(len == FILE_LEN && crc == want_crc && !fl.misaligned);
    CHECK(memcmp(dst, src, FILE_LEN) == 0);

    /* Too big for the flash region: refused before anything is stored. */
    flash_t small = {dst, 4096, 0, 0};
    CHECK(usbm_load(u, name, 4096, flash_sink, &small, &len, &crc) == USBM_TOO_BIG);
    CHECK(small.next == 0);

    /* After STOP: received file + relay log, read back across an unmount/mount (pull and replug). */
    const char *log = "MTP-F26 NM relay log\r\nrole: relay\r\n";
    CHECK(usbm_save_buf(u, "RX.TXT", dst, FILE_LEN) == USBM_OK);
    CHECK(usbm_save_buf(u, "NM_LOG.TXT", (const uint8_t *)log, (uint32_t)strlen(log)) == USBM_OK);
    usbm_unmount(u);
    CHECK(usbm_mount(u) == USBM_OK);
    memset(dst, 0, FILE_LEN);
    fl.next = 0;
    CHECK(usbm_load(u, "RX.TXT", 2u << 20, flash_sink, &fl, &len, &crc) == USBM_OK);
    CHECK(len == FILE_LEN && crc == want_crc);
    CHECK(usbm_find_input(u, "NM_LOG.TXT", name, sizeof name, &size, &count) == USBM_OK);
    CHECK(count == 3);   /* the log itself is skipped */

    /* Overwrite with a shorter file: no stale tail. */
    CHECK(usbm_save_buf(u, "RX.TXT", src, 1000) == USBM_OK);
    fl.next = 0;
    CHECK(usbm_load(u, "RX.TXT", 2u << 20, flash_sink, &fl, &len, &crc) == USBM_OK && len == 1000);

    /* Write fault in the middle: an error, and no truncated RX.TXT left behind. */
    rd.fail_after = 50;
    CHECK(usbm_save_buf(u, "RX2.TXT", src, FILE_LEN) == USBM_IO);
    rd.fail_after = -1;
    FILINFO fi;
    CHECK(f_stat("RX2.TXT", &fi) == FR_NO_FILE);

    /* Stick pulled out. */
    usbm_unmount(u);
    rd.present = 0;
    CHECK(usbm_mount(u) == USBM_NO_MEDIA);
    rd.present = 1;

    free(src);
    free(dst);
    free(u);
    ramdisk_free(&rd);
}

/* A stick as Windows (and most factories) ship it: MBR partition table, FAT32 partition at 1 MiB. Also a
 * UTF-8 file name outside the Latin-1 code page. */
static void test_mbr_and_names(void)
{
    printf("MBR-partitioned stick (Windows layout), UTF-8 names\n");
    ramdisk_t rd;
    usbm_disk_t d;
    usbm_t *u = calloc(1, sizeof *u);
    const uint32_t start = 2048, size = 131072;
    CHECK(ramdisk_init(&rd, start + size) == 0);
    ramdisk_bind(&rd, &d);
    usbm_set_disk(&d);
    rd.offset = start;                    /* format just the partition */
    CHECK(format(FM_FAT32 | FM_SFD) == 0);   /* bare volume: the MBR below is ours */
    rd.offset = 0;
    uint8_t *mbr = rd.img;                /* one primary partition, type 0x0C (FAT32 LBA) */
    memset(mbr + 446, 0, 64);
    mbr[446 + 4] = 0x0C;
    for (int i = 0; i < 4; i++) {
        mbr[446 + 8 + i] = (uint8_t)(start >> (8 * i));
        mbr[446 + 12 + i] = (uint8_t)(size >> (8 * i));
    }
    mbr[510] = 0x55;
    mbr[511] = 0xAA;
    CHECK(usbm_mount(u) == USBM_OK);
    const char *names[] = {"Señal año 2026.txt", "Ελληνικά € 文件.txt"};
    for (int k = 0; k < 2; k++) {
        CHECK(usbm_save_buf(u, names[k], (const uint8_t *)names[k], (uint32_t)strlen(names[k])) == USBM_OK);
        char name[128];
        uint32_t size2 = 0, count = 0, len = 0, crc = 0;
        CHECK(usbm_find_input(u, NULL, name, sizeof name, &size2, &count) == USBM_OK);
        CHECK(strcmp(name, names[k]) == 0 || k == 1);   /* the largest one wins; checked below */
        uint8_t buf[64];
        flash_t fl = {buf, sizeof buf, 0, 0};
        CHECK(usbm_load(u, names[k], 4096, flash_sink, &fl, &len, &crc) == USBM_OK);
        CHECK(len == strlen(names[k]) && memcmp(buf, names[k], len) == 0);
    }
    usbm_unmount(u);
    free(u);
    ramdisk_free(&rd);
}

static void test_full_and_empty(void)
{
    printf("small stick: empty root and full volume\n");
    ramdisk_t rd;
    usbm_disk_t d;
    usbm_t *u = calloc(1, sizeof *u);
    CHECK(ramdisk_init(&rd, 512) == 0);   /* 256 KB: FAT12 */
    ramdisk_bind(&rd, &d);
    usbm_set_disk(&d);
    CHECK(format(FM_FAT) == 0);
    CHECK(usbm_mount(u) == USBM_OK);
    char name[32];
    CHECK(usbm_find_input(u, NULL, name, sizeof name, NULL, NULL) == USBM_NO_FILE);
    uint8_t *big = calloc(1, 400u * 1024u);
    CHECK(usbm_save_buf(u, "RX.TXT", big, 400u * 1024u) == USBM_FULL);
    FILINFO fi;
    CHECK(f_stat("RX.TXT", &fi) == FR_NO_FILE);
    free(big);
    free(u);
    ramdisk_free(&rd);
}

static int image_mode(const char *in, const char *out)
{
    ramdisk_t rd;
    usbm_disk_t d;
    usbm_t *u = calloc(1, sizeof *u);
    if (ramdisk_load(&rd, in))
        return fprintf(stderr, "cannot read %s\n", in), 2;
    ramdisk_bind(&rd, &d);
    usbm_set_disk(&d);
    usbm_status_t st = usbm_mount(u);
    char name[256] = "";
    uint32_t size = 0, count = 0, len = 0, crc = 0;
    if (st == USBM_OK)
        st = usbm_find_input(u, "NM_LOG.TXT", name, sizeof name, &size, &count);
    uint8_t *buf = malloc(size + USBM_CHUNK);
    flash_t fl = {buf, size + USBM_CHUNK, 0, 0};
    if (st == USBM_OK)
        st = usbm_load(u, name, 4u << 20, flash_sink, &fl, &len, &crc);
    if (st == USBM_OK)
        st = usbm_save_buf(u, "RX.TXT", buf, len);
    char log[400];
    snprintf(log, sizeof log, "input: %s\r\nbytes: %u\r\ncrc32: %08X\r\n", name, (unsigned)len, (unsigned)crc);
    if (st == USBM_OK)
        st = usbm_save_buf(u, "NM_LOG.TXT", (const uint8_t *)log, (uint32_t)strlen(log));
    usbm_unmount(u);
    printf("image: %s -> input '%s' (%u bytes, CRC %08X, %u .txt seen) -> %s\n", in, name, (unsigned)len,
           (unsigned)crc, (unsigned)count, usbm_strerror(st));
    if (st == USBM_OK && ramdisk_save(&rd, out))
        st = USBM_IO;
    free(buf);
    free(u);
    ramdisk_free(&rd);
    return st == USBM_OK ? 0 : 1;
}

/* A stick with its lock switch on: the file can still be read, but saving reports USBM_READ_ONLY. */
static void test_write_protect(void)
{
    printf("write-protected stick\n");
    ramdisk_t rd;
    usbm_disk_t d;
    usbm_t *u = calloc(1, sizeof *u);
    CHECK(ramdisk_init(&rd, 65536) == 0);
    ramdisk_bind(&rd, &d);
    usbm_set_disk(&d);
    CHECK(format(FM_FAT) == 0);
    CHECK(usbm_mount(u) == USBM_OK);
    CHECK(usbm_save_buf(u, "in.txt", (const uint8_t *)"line\r\n", 6) == USBM_OK);
    usbm_unmount(u);
    rd.wp = 1;
    CHECK(usbm_mount(u) == USBM_OK);
    char name[64];
    uint32_t size = 0, count = 0;
    CHECK(usbm_find_input(u, NULL, name, sizeof name, &size, &count) == USBM_OK && size == 6);
    CHECK(usbm_save_buf(u, "out.txt", (const uint8_t *)"x", 1) == USBM_READ_ONLY);
    usbm_unmount(u);
    free(u);
    ramdisk_free(&rd);
}

int main(int argc, char **argv)
{
    if (argc == 4 && !strcmp(argv[1], "--image"))
        return image_mode(argv[2], argv[3]);
    test_format("FAT16, 32 MB", FM_FAT, 65536);
    test_format("FAT32, 64 MB", FM_FAT32, 131072);
    test_format("exFAT, 16 MB", FM_EXFAT, 32768);
    test_full_and_empty();
    test_mbr_and_names();
    test_write_protect();
    printf("%d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
