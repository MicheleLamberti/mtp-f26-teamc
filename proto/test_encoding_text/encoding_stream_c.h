/* C interface to the C++ file/Unicode layer. Errors never cross the C boundary. */
#ifndef MTP_ENCODING_STREAM_C_H
#define MTP_ENCODING_STREAM_C_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    uint64_t size_bytes;
    uint32_t crc32;
} mtp_text_file_info;

/* The caller owns all buffers. Zero is success, -1 is failure with an error string. */
int mtp_text_read_verified(const char *path, mtp_text_file_info expected,
                           uint8_t *data, size_t capacity, char *error, size_t error_capacity);
int mtp_text_inspect(const char *path, char *json, size_t capacity,
                      char *error, size_t error_capacity);

/* Internal application caches only: validate a new file before atomically replacing
 * path. path.new and path.new.part are reserved; existing staging files are refused.
 * A crash may leave staging files. The standalone receiver remains no-overwrite. */
int mtp_text_write_cache(const char *path, const uint8_t *data, mtp_text_file_info expected,
                          char *error, size_t error_capacity);
int mtp_text_decode_cache(const char *source, const char *destination,
                           const char *encoding, const char *bom_policy,
                           char *error, size_t error_capacity);

#ifdef __cplusplus
}
#endif
#endif
