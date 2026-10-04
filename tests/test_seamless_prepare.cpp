/* Local legal-disc fixture test: native setup must reproduce the independently
 * generated, MIPS-oracle-verified Python pack byte for byte. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include "mod_plugins.h"
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#include <unordered_map>
#include <vector>

struct CatalogEntry {
    const char *path;
    uint32_t lba, size;
    const char *source_sha256;
    uint32_t decoded_size;
    const char *decoded_sha256;
};
#include "../src/mods/tomba_seamless_catalog.inc"
extern "C" const char *tomba_seamless_prepare_path(int);
static std::vector<uint8_t> fixture;
static std::unordered_map<std::string,unsigned> names;
static bool corrupt;
static uint32_t le32(const uint8_t *p) {
    return uint32_t(p[0])|uint32_t(p[1])<<8|uint32_t(p[2])<<16|uint32_t(p[3])<<24;
}
extern "C" int psx_mod_read_disc_file(const char *name, void *buffer, uint32_t capacity, uint32_t *size) {
    auto it=names.find(name);
    if(it==names.end()) return 0;
    const uint8_t *record=fixture.data()+48+32*it->second;
    *size=le32(record+4);
    if(!buffer) return 1;
    if(capacity<*size) return 0;
    size_t begin=48+32*std::size(catalog)+le32(record+8);
    assert(begin+*size<=fixture.size());
    std::memcpy(buffer,fixture.data()+begin,*size);
    if(corrupt && it->second==0) static_cast<uint8_t*>(buffer)[0]^=1;
    return 1;
}
int main(int argc, char **argv) {
    if(argc!=2 || !std::getenv("TOMBA_SEAMLESS_CACHE") || std::getenv("TOMBA_SEAMLESS_PACK")) {
        std::fprintf(stderr,"Set TOMBA_SEAMLESS_CACHE to an isolated test directory, unset TOMBA_SEAMLESS_PACK, and pass the independent fixture pack.\n");
        return 2;
    }
    std::ifstream in(argv[1],std::ios::binary);
    if(!in) { std::fprintf(stderr,"Cannot open fixture: %s\n",argv[1]); return 2; }
    fixture.assign(std::istreambuf_iterator<char>(in),{});
    assert(fixture.size()>48 && !std::memcmp(fixture.data(),"TMBPK001",8));
    assert(le32(fixture.data()+8)==std::size(catalog));
    for(unsigned i=0;i<std::size(catalog);i++) {
        assert(le32(fixture.data()+48+32*i)==catalog[i].lba);
        names.emplace(catalog[i].path,i);
    }
    const char *result=tomba_seamless_prepare_path(1);
    assert(result);
    std::string path=result;
    std::ifstream built(path,std::ios::binary);
    std::vector<uint8_t> actual{std::istreambuf_iterator<char>(built),{}};
    assert(actual==fixture);
    corrupt=true;
    assert(!tomba_seamless_prepare_path(1));
    std::ifstream retained(path,std::ios::binary);
    std::vector<uint8_t> after{std::istreambuf_iterator<char>(retained),{}};
    assert(after==fixture); // failed regeneration cannot damage the valid cache
    std::puts("native first-run preparation: exact full-pack parity; changed disc rejected");
}
