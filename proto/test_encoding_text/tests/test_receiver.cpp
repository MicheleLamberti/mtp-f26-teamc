#include "../encoding_stream.hpp"
#include <chrono>
#include <fstream>
#include <iostream>
#include <stdexcept>

namespace mt=mtp_text;
void require(bool condition) { if (!condition) throw std::runtime_error("check failed"); }
template<class Fn> void fails(Fn fn) { bool failed=false; try {fn();} catch (const std::exception&) {failed=true;} require(failed); }
int main() {
    auto root=mt::fs::temp_directory_path()/("mtp_cpp_"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    mt::fs::create_directory(root);
    try {
        auto source=root/"source";
        { std::ofstream f(source,std::ios::binary); f<<"123456789"; }
        auto expected=mt::file_info(source,1);
        require(expected.size_bytes==9 && expected.crc32==0xcbf43926u);
        const auto* bytes=reinterpret_cast<const std::uint8_t*>("123456789");
        {
            mt::FileReceiver receiver(root/"out",expected);
            fails([&]{receiver.accept(1,bytes,1);});
            receiver.accept(0,bytes,2);
            fails([&]{receiver.accept(0,bytes,2);});
            fails([&]{receiver.accept(2,bytes,8);});
            fails([&]{receiver.finish();});
            receiver.accept(2,bytes+2,7);
            require(receiver.finish()==expected);
        }
        require(mt::file_info(root/"out")==expected);
        fails([&]{mt::FileReceiver receiver(root/"out",expected);});
        { std::ofstream f(root/"reserved.part"); f<<"KEEP"; }
        fails([&]{mt::FileReceiver receiver(root/"reserved",expected);});
        require(mt::file_info(root/"reserved.part").size_bytes==4);
        {
            mt::FileReceiver receiver(root/"race",expected); receiver.accept(0,bytes,9);
            { std::ofstream f(root/"race"); f<<"KEEP"; }
            fails([&]{receiver.finish();});
        }
        require(mt::file_info(root/"race").size_bytes==4);
        require(!mt::fs::exists(root/"race.part"));
        {
            mt::FileReceiver receiver(root/"short",expected); receiver.accept(0,bytes,1);
            fails([&]{receiver.finish();});
        }
        require(!mt::fs::exists(root/"short") && !mt::fs::exists(root/"short.part"));
        fails([&]{mt::file_info(source,0);});
        fails([&]{mt::file_info(source,1048577);});
        mt::FileInfo wrong=expected; wrong.crc32^=1;
        fails([&]{mt::send_file(source,[](const std::uint8_t*,std::size_t){},3,&wrong);});
        mt::fs::create_directory(root/"discovery");
        fails([&]{mt::discover(root/"discovery");});
        { std::ofstream f(root/"discovery"/"one.TXT"); f<<"a"; }
        require(mt::discover(root/"discovery").filename()=="one.TXT");
        { std::ofstream f(root/"discovery"/"two.txt"); f<<"b"; }
        fails([&]{mt::discover(root/"discovery");});
        mt::fs::remove_all(root);
        std::cout<<"C++ receiver and file-discovery checks passed\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr<<e.what()<<"; retained test directory: "<<root<<'\n'; return 1;
    }
}
