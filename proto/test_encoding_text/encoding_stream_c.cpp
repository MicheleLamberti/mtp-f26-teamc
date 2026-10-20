#include "encoding_stream_c.h"
#include "encoding_stream.hpp"
#include <algorithm>
#include <cerrno>
#include <cstring>
#include <stdexcept>
#include <system_error>
#ifdef _WIN32
#include <windows.h>
#else
#include <fcntl.h>
#include <unistd.h>
#endif

namespace mt = mtp_text;
namespace {
template<class Fn> int checked(char *error, size_t capacity, Fn fn) noexcept {
    if (error && capacity) error[0] = '\0';
    try { fn(); return 0; }
    catch (const std::exception& e) {
        if (error && capacity) std::snprintf(error, capacity, "%s", e.what());
    } catch (...) {
        if (error && capacity) std::snprintf(error, capacity, "unknown file-layer error");
    }
    return -1;
}
mt::fs::path path_of(const char *path) {
    if (!path || !path[0]) throw std::invalid_argument("empty file path");
    return mt::fs::u8path(path);
}
mt::fs::path staging(const mt::fs::path& path) {
    auto next = path;
    next += ".new";
    return next;
}
void replace_cache(const mt::fs::path& source, const mt::fs::path& target) {
#ifdef _WIN32
    if (!MoveFileExW(source.c_str(), target.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH))
        throw std::system_error(static_cast<int>(GetLastError()), std::system_category(), "replace cache");
#elif defined(__linux__)
    if (::rename(source.c_str(), target.c_str()))
        throw std::system_error(errno, std::generic_category(), "replace cache");
    auto parent = target.parent_path();
    if (parent.empty()) parent = ".";
    int fd = ::open(parent.c_str(), O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (fd < 0) throw std::system_error(errno, std::generic_category(), "open cache directory");
    int result = ::fsync(fd), saved = errno;
    ::close(fd);
    if (result) throw std::system_error(saved, std::generic_category(), "sync cache directory");
#else
    throw std::runtime_error("cache publication requires Linux or Windows");
#endif
}
}

extern "C" int mtp_text_read_verified(const char *path, mtp_text_file_info expected,
                                       uint8_t *data, size_t capacity, char *error, size_t error_capacity) {
    return checked(error, error_capacity, [&] {
        if (expected.size_bytes > capacity || (!data && expected.size_bytes))
            throw std::invalid_argument("file exceeds destination buffer");
        const mt::FileInfo info{expected.size_bytes, expected.crc32};
        size_t offset = 0;
        mt::send_file(path_of(path), [&](const uint8_t *bytes, size_t n) {
            if (n > expected.size_bytes - offset) throw std::runtime_error("source grew after preparation");
            std::memcpy(data + offset, bytes, n);
            offset += n;
        }, 4096, &info);
    });
}
extern "C" int mtp_text_write_cache(const char *path, const uint8_t *data, mtp_text_file_info expected,
                                      char *error, size_t error_capacity) {
    return checked(error, error_capacity, [&] {
        if ((!data && expected.size_bytes) || expected.size_bytes > SIZE_MAX)
            throw std::invalid_argument("invalid source buffer");
        auto target = path_of(path), next = staging(target);
        mt::FileReceiver receiver(next, {expected.size_bytes, expected.crc32});
        for (uint64_t offset = 0; offset < expected.size_bytes;) {
            auto n = static_cast<size_t>(std::min<uint64_t>(4096, expected.size_bytes - offset));
            receiver.accept(offset, data + static_cast<size_t>(offset), n);
            offset += n;
        }
        receiver.finish();
        replace_cache(next, target);
    });
}
extern "C" int mtp_text_inspect(const char *path, char *json, size_t capacity,
                                 char *error, size_t error_capacity) {
    return checked(error, error_capacity, [&] {
        auto report = mt::json(mt::inspect_file(path_of(path)));
        if (!json || capacity <= report.size()) throw std::invalid_argument("inspection buffer too small");
        std::memcpy(json, report.c_str(), report.size() + 1);
    });
}
extern "C" int mtp_text_decode_cache(const char *source, const char *destination,
                                      const char *encoding, const char *bom_policy,
                                      char *error, size_t error_capacity) {
    return checked(error, error_capacity, [&] {
        if (!encoding || !bom_policy) throw std::invalid_argument("missing decoding policy");
        auto target = path_of(destination), next = staging(target);
        mt::decode_file(path_of(source), next, encoding, bom_policy);
        replace_cache(next, target);
    });
}
