#include "encoding_stream.hpp"
#include <cerrno>
#include <iostream>
#include <map>
#include <memory>
#include <stdexcept>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

namespace mt = mtp_text;
std::uint64_t number(const std::string& text,int base=10) {
    if (text.empty() || text.find_first_not_of(base==10?"0123456789":"0123456789abcdefABCDEF")!=std::string::npos)
        throw std::invalid_argument("invalid numeric argument");
    return std::stoull(text,nullptr,base);
}
int main(int argc,char** argv) {
    try {
        if (argc<2 || std::string(argv[1])=="--help") {
            std::cout<<"encoding_stream inspect FILE | discover DIRECTORY\n"
                "encoding_stream send FILE STREAM | copy FILE OUTPUT\n"
                "encoding_stream receive STREAM OUTPUT --size N --crc32 HEX\n"
                "encoding_stream decode FILE UTF8_OUTPUT [--encoding auto|utf-8|utf-16-le|utf-16-be|utf-32-le|utf-32-be]\n"
                "Options: --chunk-size 4096, --bom-policy strict|longest, --keep-bom\n"
                "Use - for send's STREAM stdout or receive's STREAM stdin. Metadata is separate from raw bytes.\n";
            return argc<2?2:0;
        }
        std::string command=argv[1]; std::vector<std::string> positional;
        std::map<std::string,std::string> options={{"--chunk-size","4096"},{"--encoding","auto"},{"--bom-policy","strict"}};
        bool keep=false;
        for (int i=2;i<argc;++i) {
            std::string arg=argv[i];
            if (arg=="--keep-bom") keep=true;
            else if (arg.rfind("--",0)==0) {
                if (arg!="--chunk-size" && arg!="--encoding" && arg!="--bom-policy" && arg!="--size" && arg!="--crc32")
                    throw std::invalid_argument("unknown option");
                if (++i>=argc) throw std::invalid_argument("missing option value");
                options[arg]=argv[i];
            } else positional.push_back(arg);
        }
        bool single=command=="inspect" || command=="discover";
        if ((!single && command!="send" && command!="receive" && command!="copy" && command!="decode") || positional.size()!=(single?1u:2u))
            throw std::invalid_argument("invalid command; use --help");
        auto chunk_value=number(options["--chunk-size"]);
        if (chunk_value>1048576) throw std::invalid_argument("chunk size too large");
        auto chunk=static_cast<std::size_t>(chunk_value); mt::check_chunk(chunk);
        auto source=mt::fs::u8path(positional[0]);
        if (command=="inspect") std::cout<<mt::json(mt::inspect_file(source,chunk))<<'\n';
        else if (command=="discover") std::cout<<"{\"file\":"<<mt::json_string(mt::discover(source).u8string())<<"}\n";
        else {
            auto target=mt::fs::u8path(positional[1]);
            if (command=="decode") {
                auto encoding=mt::decode_file(source,target,options["--encoding"],options["--bom-policy"],keep,chunk);
                std::cout<<"{\"encoding\":"<<mt::json_string(encoding)<<"}\n";
            } else if (command=="send") {
                auto expected=mt::file_info(source,chunk);
                if (positional[1]=="-") {
#ifdef _WIN32
                    _setmode(_fileno(stdout),_O_BINARY);
#endif
                    auto sent=mt::send_file(source,[](const std::uint8_t* p,std::size_t n) {
                        while (n) {auto done=std::fwrite(p,1,n,stdout); if (!done) throw std::runtime_error("stdout write failed"); p+=done; n-=done;}
                    },chunk,&expected);
                    if (std::fflush(stdout)) throw std::runtime_error("stdout flush failed");
                    std::cerr<<mt::json(sent)<<'\n';
                } else {
                    mt::AtomicOutput output(target);
                    mt::send_file(source,[&](const std::uint8_t* p,std::size_t n){output.write(p,n);},chunk,&expected);
                    std::cout<<mt::json(output.finish(&expected))<<'\n';
                }
            } else {
                mt::FileInfo expected;
                if (command=="copy") expected=mt::file_info(source,chunk);
                else {
                    if (!options.count("--size") || !options.count("--crc32") || options["--crc32"].size()!=8)
                        throw std::invalid_argument("receive requires --size N --crc32 XXXXXXXX");
                    expected={number(options["--size"]),static_cast<std::uint32_t>(number(options["--crc32"],16))};
                }
                std::FILE* input=stdin;
                if (positional[0]!="-") {
#ifdef _WIN32
                    input=_wfopen(source.c_str(),L"rb");
#else
                    input=std::fopen(source.c_str(),"rb");
#endif
                    if (!input) throw std::runtime_error("cannot open stream");
                }
#ifdef _WIN32
                else _setmode(_fileno(stdin),_O_BINARY);
#endif
                std::unique_ptr<std::FILE,decltype(&std::fclose)> owned(input==stdin?nullptr:input,&std::fclose);
                std::cout<<mt::json(mt::receive_stream(input,target,expected,chunk))<<'\n';
            }
        }
        return 0;
    } catch (const std::exception& error) {std::cerr<<"error: "<<error.what()<<'\n'; return 2;}
}
