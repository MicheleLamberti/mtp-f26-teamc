#include "encoding_stream.hpp"
#include <algorithm>
#include <array>
#include <cerrno>
#include <cctype>
#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <system_error>
#ifdef _WIN32
#include <io.h>
#include <windows.h>
#else
#include <fcntl.h>
#include <unistd.h>
#endif

namespace mtp_text {
namespace {
const std::array<std::string,5> encodings = {"utf-8", "utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be"};
struct Bom { std::vector<std::uint8_t> bytes; std::string encoding; };
const std::array<Bom,5> boms = {Bom{{0xff,0xfe,0,0}, "utf-32-le"}, Bom{{0,0,0xfe,0xff}, "utf-32-be"},
    Bom{{0xef,0xbb,0xbf}, "utf-8"}, Bom{{0xff,0xfe}, "utf-16-le"}, Bom{{0xfe,0xff}, "utf-16-be"}};
[[noreturn]] void io_error(const std::string& operation) {
    throw std::system_error(errno, std::generic_category(), operation);
}
std::uint32_t crc_update(std::uint32_t crc, const std::uint8_t* data, std::size_t size) {
    static const auto table = [] {
        std::array<std::uint32_t,256> t{};
        for (std::uint32_t i=0; i<256; ++i) {
            auto v=i;
            for (int bit=0; bit<8; ++bit) v=(v>>1)^((v&1)?0xedb88320u:0u);
            t[i]=v;
        }
        return t;
    }();
    crc ^= 0xffffffffu;
    for (std::size_t i=0; i<size; ++i) crc=table[(crc^data[i])&255]^(crc>>8);
    return crc^0xffffffffu;
}
void account(FileInfo& info, const std::uint8_t* data, std::size_t size) {
    if (size > std::numeric_limits<std::uint64_t>::max()-info.size_bytes)
        throw std::overflow_error("file size exceeds uint64");
    info.size_bytes+=size;
    info.crc32=crc_update(info.crc32,data,size);
}
void walk(const fs::path& path, std::size_t chunk, const ByteSink& sink) {
    check_chunk(chunk);
    if (!fs::is_regular_file(path)) throw std::runtime_error("source must be a regular file");
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("cannot open source file");
    std::vector<std::uint8_t> buffer(chunk);
    for (;;) {
        input.read(reinterpret_cast<char*>(buffer.data()),static_cast<std::streamsize>(buffer.size()));
        auto n=input.gcount();
        if (n>0) sink(buffer.data(),static_cast<std::size_t>(n));
        if (input.bad() || (input.fail() && !input.eof())) throw std::runtime_error("file read failed");
        if (input.eof()) break;
    }
}
std::vector<std::uint8_t> prefix(const fs::path& path) {
    std::ifstream file(path,std::ios::binary);
    if (!file) throw std::runtime_error("cannot open file prefix");
    std::vector<std::uint8_t> result(4);
    file.read(reinterpret_cast<char*>(result.data()),4);
    if (file.bad()) throw std::runtime_error("prefix read failed");
    result.resize(static_cast<std::size_t>(file.gcount()));
    return result;
}
bool starts(const std::vector<std::uint8_t>& data, const std::vector<std::uint8_t>& signature) {
    return data.size()>=signature.size() && std::equal(signature.begin(),signature.end(),data.begin());
}
bool contains(const std::vector<std::string>& v,const std::string& s) {
    return std::find(v.begin(),v.end(),s)!=v.end();
}
struct DecodeError : std::runtime_error { DecodeError():std::runtime_error("invalid or incomplete Unicode sequence"){} };

// Incremental scalar decoder; retains at most one code unit/sequence and one
// UTF-16 high surrogate. Noncharacters and NUL are valid scalar values.
class Decoder {
    unsigned width_, used_=0, remaining_=0;
    bool little_;
    std::uint32_t value_=0, minimum_=0, high_=0;
    std::function<void(std::uint32_t)> emit_;
    void scalar(std::uint32_t cp) {
        if (cp>0x10ffff || (cp>=0xd800 && cp<=0xdfff)) throw DecodeError();
        emit_(cp);
    }
public:
    Decoder(const std::string& enc, std::function<void(std::uint32_t)> emit):
        width_(enc=="utf-8"?1u:enc.find("utf-16-")==0?2u:4u),
        little_(enc.find("-le")!=std::string::npos), emit_(std::move(emit)) {
        if (std::find(encodings.begin(),encodings.end(),enc)==encodings.end())
            throw std::runtime_error("unsupported encoding");
    }
    void feed(const std::uint8_t* data,std::size_t n) {
        for (std::size_t i=0;i<n;++i) {
            std::uint32_t b=data[i];
            if (width_==1) {
                if (remaining_) {
                    if ((b&0xc0)!=0x80) throw DecodeError();
                    value_=(value_<<6)|(b&0x3f);
                    if (--remaining_==0) {
                        if (value_<minimum_) throw DecodeError();
                        scalar(value_);
                    }
                } else if (b<0x80) scalar(b);
                else if (b>=0xc2 && b<=0xdf) { value_=b&0x1f; remaining_=1; minimum_=0x80; }
                else if (b>=0xe0 && b<=0xef) { value_=b&0xf; remaining_=2; minimum_=0x800; }
                else if (b>=0xf0 && b<=0xf4) { value_=b&7; remaining_=3; minimum_=0x10000; }
                else throw DecodeError();
            } else {
                if (little_) value_|=b<<(8*used_); else value_=(value_<<8)|b;
                if (++used_==width_) {
                    auto unit=value_; value_=0; used_=0;
                    if (width_==4) scalar(unit);
                    else if (high_) {
                        if (unit<0xdc00 || unit>0xdfff) throw DecodeError();
                        scalar(0x10000+((high_-0xd800)<<10)+(unit-0xdc00)); high_=0;
                    } else if (unit>=0xd800 && unit<=0xdbff) high_=unit;
                    else scalar(unit);
                }
            }
        }
    }
    void finish() { if (remaining_ || used_ || high_) throw DecodeError(); }
};
bool valid(const fs::path& path,const std::string& enc,std::size_t skip,std::size_t chunk) {
    Decoder decoder(enc,[](std::uint32_t){});
    try {
        walk(path,chunk,[&](const std::uint8_t* p,std::size_t n) {
            auto omit=std::min(skip,n); skip-=omit;
            decoder.feed(p+omit,n-omit);
        });
        decoder.finish();
        return skip==0;
    } catch (const DecodeError&) { return false; }
}
void utf8(std::uint32_t cp,std::vector<std::uint8_t>& out) {
    if (cp<0x80) out.push_back(static_cast<std::uint8_t>(cp));
    else if (cp<0x800) {
        out.push_back(static_cast<std::uint8_t>(0xc0|(cp>>6)));
        out.push_back(static_cast<std::uint8_t>(0x80|(cp&63)));
    } else if (cp<0x10000) {
        out.push_back(static_cast<std::uint8_t>(0xe0|(cp>>12)));
        out.push_back(static_cast<std::uint8_t>(0x80|((cp>>6)&63)));
        out.push_back(static_cast<std::uint8_t>(0x80|(cp&63)));
    } else {
        out.push_back(static_cast<std::uint8_t>(0xf0|(cp>>18)));
        out.push_back(static_cast<std::uint8_t>(0x80|((cp>>12)&63)));
        out.push_back(static_cast<std::uint8_t>(0x80|((cp>>6)&63)));
        out.push_back(static_cast<std::uint8_t>(0x80|(cp&63)));
    }
}
}

void check_chunk(std::size_t n) {
    if (n<1 || n>1048576) throw std::invalid_argument("chunk size must be between 1 and 1048576 bytes");
}
FileInfo send_file(const fs::path& path,const ByteSink& sink,std::size_t chunk,const FileInfo* expected) {
    FileInfo result;
    walk(path,chunk,[&](const std::uint8_t* p,std::size_t n){sink(p,n); account(result,p,n);});
    if (expected && result!=*expected) throw std::runtime_error("source changed after preparation");
    return result;
}
FileInfo file_info(const fs::path& path,std::size_t chunk) {
    return send_file(path,[](const std::uint8_t*,std::size_t){},chunk);
}
fs::path discover(const fs::path& directory) {
    std::vector<fs::path> matches;
    for (const auto& item:fs::directory_iterator(directory)) {
        auto suffix=item.path().extension().string();
        std::transform(suffix.begin(),suffix.end(),suffix.begin(),[](unsigned char c){return static_cast<char>(std::tolower(c));});
        if (!item.is_symlink() && item.is_regular_file() && suffix==".txt") matches.push_back(item.path());
    }
    if (matches.size()!=1) throw std::runtime_error("expected one .txt file; specify a file explicitly");
    return matches[0];
}
Inspection inspect_file(const fs::path& path,std::size_t chunk) {
    Inspection r; r.file=file_info(path,chunk); auto p=prefix(path);
    for (const auto& enc:encodings) if (valid(path,enc,0,chunk)) r.valid_encodings.push_back(enc);
    for (const auto& b:boms) if (starts(p,b.bytes)) {
        r.bom_matches.push_back(b.encoding);
        if (valid(path,b.encoding,b.bytes.size(),chunk)) r.valid_bom_encodings.push_back(b.encoding);
    }
    if (!r.file.size_bytes) r.detection="empty";
    else if (!r.bom_matches.empty()) {
        auto n=r.valid_bom_encodings.size();
        r.detection=n==1?"bom":n?"ambiguous_bom":"invalid_bom";
        if (n==1) r.auto_encoding=r.valid_bom_encodings[0];
    } else {
        auto n=r.valid_encodings.size();
        r.detection=n==1?"unique_valid":n?"ambiguous":"invalid";
        if (n==1) r.auto_encoding=r.valid_encodings[0];
    }
    return r;
}
std::string select_encoding(const Inspection& r,const std::string& enc,const std::string& policy) {
    if (policy!="strict" && policy!="longest") throw std::invalid_argument("unknown BOM policy");
    if (enc!="auto") {
        if (!contains(r.valid_encodings,enc)) throw std::runtime_error("file is invalid in the declared encoding");
        return enc;
    }
    if (policy=="longest" && !r.bom_matches.empty()) {
        if (!contains(r.valid_bom_encodings,r.bom_matches[0])) throw std::runtime_error("longest BOM signature has invalid text");
        return r.bom_matches[0];
    }
    if (r.auto_encoding.empty()) throw std::runtime_error("encoding unresolved ("+r.detection+"); specify --encoding");
    return r.auto_encoding;
}
AtomicOutput::AtomicOutput(const fs::path& path):destination_(path),partial_(path) {
    partial_ += ".part";
    if (fs::exists(fs::symlink_status(destination_))) throw std::runtime_error("destination already exists");
#ifdef _WIN32
    file_=_wfopen(partial_.c_str(),L"wbx");
#else
    file_=std::fopen(partial_.c_str(),"wbx");
#endif
    if (!file_) io_error("create partial file");
    owned_=true;
}
AtomicOutput::~AtomicOutput() {
    if (file_) std::fclose(file_);
    if (owned_) { std::error_code ignored; fs::remove(partial_,ignored); }
}
void AtomicOutput::write(const std::uint8_t* data,std::size_t n) {
    if (!file_) throw std::runtime_error("output is closed");
    auto p=data; auto left=n;
    while (left) {
        auto written=std::fwrite(p,1,left,file_);
        if (!written) io_error("write file");
        left-=written; p+=written;
    }
    account(current_,data,n);
}
FileInfo AtomicOutput::finish(const FileInfo* expected) {
    if (!file_) throw std::runtime_error("output is closed");
    if (expected && current_!=*expected) throw std::runtime_error("received size or CRC-32 differs from sender metadata");
    if (std::fflush(file_)) io_error("flush file");
#ifdef _WIN32
    if (_commit(_fileno(file_))) io_error("sync file");
#else
    if (::fsync(fileno(file_))) io_error("sync file");
#endif
    auto closing=file_; file_=nullptr;
    if (std::fclose(closing)) io_error("close file");
    if (file_info(partial_)!=current_) throw std::runtime_error("saved file failed read-back validation");
#ifdef _WIN32
    if (!MoveFileExW(partial_.c_str(),destination_.c_str(),MOVEFILE_WRITE_THROUGH))
        throw std::system_error(static_cast<int>(GetLastError()),std::system_category(),"publish file");
#elif defined(__linux__)
    if (::renameat2(AT_FDCWD,partial_.c_str(),AT_FDCWD,destination_.c_str(),RENAME_NOREPLACE)) io_error("publish file");
#else
    throw std::runtime_error("publication requires Linux or Windows");
#endif
    owned_=false;
#ifdef __linux__
    auto parent=destination_.parent_path(); if (parent.empty()) parent=".";
    int directory=::open(parent.c_str(),O_RDONLY|O_DIRECTORY);
    if (directory<0) io_error("open destination directory");
    int result=::fsync(directory), saved=errno; ::close(directory); errno=saved;
    if (result) io_error("sync destination directory");
#endif
    return current_;
}
void FileReceiver::accept(std::uint64_t offset,const std::uint8_t* data,std::size_t n) {
    if (offset!=output_.size()) throw std::runtime_error("duplicate, missing or out-of-order data");
    if (n>expected_.size_bytes-output_.size()) throw std::runtime_error("received more bytes than declared");
    output_.write(data,n);
}
FileInfo receive_stream(std::FILE* source,const fs::path& path,FileInfo expected,std::size_t chunk) {
    check_chunk(chunk); FileReceiver receiver(path,expected); std::vector<std::uint8_t> buffer(chunk);
    for (;;) {
        auto n=std::fread(buffer.data(),1,buffer.size(),source);
        if (n) receiver.accept(receiver.size(),buffer.data(),n);
        if (std::ferror(source)) io_error("read stream");
        if (std::feof(source)) break;
    }
    return receiver.finish();
}
std::string decode_file(const fs::path& source,const fs::path& target,const std::string& enc,
                        const std::string& policy,bool keep_bom,std::size_t chunk) {
    auto report=inspect_file(source,chunk); auto selected=select_encoding(report,enc,policy);
    auto p=prefix(source); std::size_t skip=0;
    if (!keep_bom) for (const auto& b:boms) if (b.encoding==selected && starts(p,b.bytes)) skip=b.bytes.size();
    AtomicOutput output(target); std::vector<std::uint8_t> text;
    text.reserve(chunk*3+4);
    Decoder decoder(selected,[&](std::uint32_t cp){utf8(cp,text);});
    FileInfo observed;
    walk(source,chunk,[&](const std::uint8_t* data,std::size_t n) {
        account(observed,data,n);
        auto omit=std::min(skip,n); skip-=omit; text.clear();
        decoder.feed(data+omit,n-omit); output.write(text.data(),text.size());
    });
    decoder.finish();
    if (observed!=report.file) throw std::runtime_error("source changed during decoding");
    output.finish(); return selected;
}
std::string json_string(const std::string& value) {
    std::ostringstream out; out<<'"';
    for (unsigned char c:value) {
        if (c=='"' || c=='\\') out<<'\\'<<c;
        else if (c<32) out<<"\\u"<<std::hex<<std::setw(4)<<std::setfill('0')<<static_cast<unsigned>(c);
        else out<<c;
    }
    return out.str()+'"';
}
std::string json(const FileInfo& r) {
    std::ostringstream out;
    out<<"{\"size_bytes\":"<<r.size_bytes<<",\"crc32\":\""<<std::hex<<std::setw(8)<<std::setfill('0')<<r.crc32<<"\"}";
    return out.str();
}
std::string json(const Inspection& r) {
    auto out=json(r.file); out.pop_back();
    const auto array=[](const std::vector<std::string>& v) {
        std::string s="["; for (const auto& item:v) {if (s.size()>1) s+=","; s+=json_string(item);} return s+"]";
    };
    return out+",\"bom_matches\":"+array(r.bom_matches)+",\"valid_bom_encodings\":"+array(r.valid_bom_encodings)+
        ",\"valid_encodings\":"+array(r.valid_encodings)+",\"auto_encoding\":"+
        (r.auto_encoding.empty()?"null":json_string(r.auto_encoding))+",\"detection\":"+json_string(r.detection)+"}";
}
}
