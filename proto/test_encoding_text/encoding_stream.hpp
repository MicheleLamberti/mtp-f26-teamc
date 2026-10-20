#pragma once
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <functional>
#include <string>
#include <vector>

namespace mtp_text {
namespace fs = std::filesystem;
struct FileInfo {
    std::uint64_t size_bytes = 0;
    std::uint32_t crc32 = 0;
    bool operator==(const FileInfo& b) const { return size_bytes == b.size_bytes && crc32 == b.crc32; }
    bool operator!=(const FileInfo& b) const { return !(*this == b); }
};
struct Inspection {
    FileInfo file;
    std::vector<std::string> bom_matches, valid_bom_encodings, valid_encodings;
    std::string auto_encoding, detection;
};
using ByteSink = std::function<void(const std::uint8_t*, std::size_t)>;
void check_chunk(std::size_t size);
FileInfo file_info(const fs::path& path, std::size_t chunk = 4096);
fs::path discover(const fs::path& directory);
Inspection inspect_file(const fs::path& path, std::size_t chunk = 4096);
std::string select_encoding(const Inspection&, const std::string& encoding = "auto",
                            const std::string& bom_policy = "strict");
FileInfo send_file(const fs::path&, const ByteSink&, std::size_t chunk = 4096,
                   const FileInfo* expected = nullptr);

// Final publication never overwrites an existing final or .part file.
class AtomicOutput {
public:
    explicit AtomicOutput(const fs::path& destination);
    ~AtomicOutput();
    AtomicOutput(const AtomicOutput&) = delete;
    AtomicOutput& operator=(const AtomicOutput&) = delete;
    void write(const std::uint8_t* data, std::size_t size);
    FileInfo finish(const FileInfo* expected = nullptr);
    std::uint64_t size() const { return current_.size_bytes; }
private:
    fs::path destination_, partial_;
    std::FILE* file_ = nullptr;
    bool owned_ = false;
    FileInfo current_;
};
class FileReceiver {
public:
    FileReceiver(const fs::path& path, FileInfo expected) : output_(path), expected_(expected) {}
    void accept(std::uint64_t offset, const std::uint8_t* data, std::size_t size);
    FileInfo finish() { return output_.finish(&expected_); }
    std::uint64_t size() const { return output_.size(); }
private:
    AtomicOutput output_;
    FileInfo expected_;
};
FileInfo receive_stream(std::FILE* source, const fs::path&, FileInfo expected, std::size_t chunk = 4096);
std::string decode_file(const fs::path& source, const fs::path& destination,
                        const std::string& encoding = "auto", const std::string& bom_policy = "strict",
                        bool keep_bom = false, std::size_t chunk = 4096);
std::string json(const FileInfo&);
std::string json(const Inspection&);
std::string json_string(const std::string&);
}
