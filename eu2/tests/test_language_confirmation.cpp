/* Synthetic unit memory, not a gameplay/save test. Code fixtures are read
 * from the owner's verified local files; no game bytes are compiled in. */
#include "mod_plugins.h"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>
#include <cstdio>

static uint8_t ram[2*1024*1024];
static PSXModVBlankCallback tick;
static unsigned writes;
extern "C" int psx_mod_register_vblank_plugin(const char* id, PSXModVBlankCallback callback) {
    assert(std::strcmp(id,"tombi.language-confirmation")==0);tick=callback;return 1;
}
extern "C" uint32_t psx_mod_read_word(uint32_t pc) {
    uint32_t v;std::memcpy(&v,ram+(pc&0x1fffff),4);return v;
}
static void put(uint32_t pc,uint32_t v){std::memcpy(ram+(pc&0x1fffff),&v,4);}
extern "C" void psx_mod_write_word(uint32_t pc,uint32_t v){assert(pc==0x800AF0A4u && v==1000);++writes;put(pc,v);}
static void load(const std::string& path) {
    std::ifstream stream(path,std::ios::binary);assert(stream);
    std::vector<uint8_t> bytes{std::istreambuf_iterator<char>(stream),{}};
    assert(bytes.size()>2048);std::memset(ram,0,sizeof ram);
    assert(bytes.size()-2048<sizeof ram-0x10000);
    std::memcpy(ram+0x10000,bytes.data()+2048,bytes.size()-2048);
}
int main(int argc,char**argv) {
    assert(argc==2 && tick);const std::string disc=argv[1];load(disc+"/SCES_013.31");
    for(uint32_t value:{1u,999u,1000u}){put(0x800AF0A4,value);writes=0;tick();assert(writes==1 && psx_mod_read_word(0x800AF0A4)==1000);}
    for(uint32_t value:{0u,1001u,0xffffffffu}){put(0x800AF0A4,value);writes=0;tick();assert(!writes);}
    put(0x800AF0A4,1);put(0x80011040,psx_mod_read_word(0x80011040)^1);writes=0;tick();assert(!writes);
    for(unsigned lang:{0u,5u,6u,7u,8u}){load(disc+"/EXE/MAIN"+std::to_string(lang)+".EXE");put(0x800AF0A4,1);writes=0;tick();assert(!writes);}
    std::puts("PASS: selector-only timer hold, boundary cases, complete-code mismatch and all five MAIN exclusions");
}
