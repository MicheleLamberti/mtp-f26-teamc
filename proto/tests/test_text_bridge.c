/* Exercises the real C ABI and complete-stream decompression used by teamc-node. */
#define _GNU_SOURCE
#include "encoding_stream_c.h"
#include "codec.h"
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static unsigned checks;
#define CHECK(x) do { checks++; if (!(x)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); return 1; } } while (0)

int main(void)
{
    char root[] = "/tmp/teamc_text_XXXXXX";
    CHECK(mkdtemp(root) != NULL);
    char file[128], decoded[128], next[132], error[256], report[2048];
    snprintf(file, sizeof file, "%s/cache.bin", root);
    snprintf(decoded, sizeof decoded, "%s/view.txt", root);
    snprintf(next, sizeof next, "%s.new", file);
    const uint8_t bytes[] = "123456789";
    mtp_text_file_info expected = {9, 0xcbf43926u};
    uint8_t got[64];
    CHECK(mtp_text_write_cache(file, bytes, expected, error, sizeof error) == 0);
    CHECK(mtp_text_read_verified(file, expected, got, sizeof got, error, sizeof error) == 0);
    CHECK(memcmp(got, bytes, 9) == 0);
    CHECK(mtp_text_read_verified(file, expected, got, 8, error, sizeof error) == -1);
    CHECK(error[0] != '\0');
    mtp_text_file_info wrong = expected;
    wrong.crc32 ^= 1;
    CHECK(mtp_text_read_verified(file, wrong, got, sizeof got, error, sizeof error) == -1);
    CHECK(mtp_text_write_cache(file, bytes, wrong, error, sizeof error) == -1);
    CHECK(mtp_text_read_verified(file, expected, got, sizeof got, error, sizeof error) == 0);
    FILE *reserved = fopen(next, "wb");
    CHECK(reserved != NULL);
    CHECK(fwrite("KEEP", 1, 4, reserved) == 4 && fclose(reserved) == 0);
    CHECK(mtp_text_write_cache(file, bytes, expected, error, sizeof error) == -1);
    CHECK(unlink(next) == 0);
    const uint8_t utf8[] = {0xef, 0xbb, 0xbf, 'A', '\r', '\n'};
    expected = (mtp_text_file_info){sizeof utf8, codec_crc32(utf8, sizeof utf8)};
    CHECK(mtp_text_write_cache(file, utf8, expected, error, sizeof error) == 0);
    CHECK(mtp_text_inspect(file, report, sizeof report, error, sizeof error) == 0);
    CHECK(strstr(report, "\"auto_encoding\":\"utf-8\"") != NULL);
    CHECK(mtp_text_decode_cache(file, decoded, "auto", "strict", error, sizeof error) == 0);
    mtp_text_file_info text = {3, codec_crc32(utf8 + 3, 3)};
    CHECK(mtp_text_read_verified(decoded, text, got, sizeof got, error, sizeof error) == 0);
    CHECK(memcmp(got, "A\r\n", 3) == 0);
    CHECK(mtp_text_decode_cache(file, decoded, "utf-16-le", "strict", error, sizeof error) == 0);
    CHECK(mtp_text_decode_cache(file, decoded, "not-an-encoding", "strict", error, sizeof error) == -1);
    CHECK(mtp_text_inspect(NULL, report, sizeof report, error, sizeof error) == -1);

    uint8_t source[8192], restored[8192], *compressed = NULL;
    memset(source, 'x', sizeof source);
    uint32_t n = 0, length = 0;
    CHECK(codec_deflate(source, sizeof source, 9, &compressed, &n) == 0);
    CHECK(codec_inflate_complete(compressed, n, restored, sizeof restored, &length) == 0);
    CHECK(length == sizeof source && memcmp(source, restored, length) == 0);
    CHECK(codec_inflate_complete(compressed, n - 1, restored, sizeof restored, &length) == -1);
    CHECK(codec_inflate_complete(compressed, n, restored, sizeof restored - 1, &length) == -1);
    compressed[n - 1] ^= 1;
    CHECK(codec_inflate_complete(compressed, n, restored, sizeof restored, &length) == -1);
    compressed[n - 1] ^= 1;
    uint8_t *extra = malloc(n + 1);
    CHECK(extra != NULL);
    memcpy(extra, compressed, n);
    extra[n] = 0;
    CHECK(codec_inflate_complete(extra, n + 1, restored, sizeof restored, &length) == -1);
    free(extra);
    free(compressed);
    CHECK(codec_deflate(source, 0, 9, &compressed, &n) == 0);
    CHECK(codec_inflate_complete(compressed, n, restored, sizeof restored, &length) == 0 && length == 0);
    free(compressed);

    /* All test outputs are flat, in the unique directory created above. */
    DIR *dir = opendir(root);
    CHECK(dir != NULL);
    struct dirent *entry;
    while ((entry = readdir(dir))) {
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) continue;
        char path[512];
        snprintf(path, sizeof path, "%s/%s", root, entry->d_name);
        CHECK(unlink(path) == 0);
    }
    closedir(dir);
    CHECK(rmdir(root) == 0);
    printf("C file-layer bridge and complete deflate: %u checks passed\n", checks);
    return 0;
}
