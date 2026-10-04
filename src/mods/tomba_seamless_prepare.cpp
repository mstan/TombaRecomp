/* One-time data preparation inside the shipped binary. This consumes the
 * mounted legal disc through the mod file service; no compiler, Python,
 * generated game C, source checkout, or external extractor is required. */
#include "mod_plugins.h"
#include "psx_sha256.h"
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>
#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#else
#include <unistd.h>
#endif

namespace {
using Bytes = std::vector<uint8_t>;
struct CatalogEntry {
    const char *path;
    uint32_t lba, size;
    const char *source_sha256;
    uint32_t decoded_size;
    const char *decoded_sha256;
};
#include "tomba_seamless_catalog.inc"

void put32(Bytes &v, uint32_t x) {
    for(unsigned i=0;i<4;i++) v.push_back(uint8_t(x>>(8*i)));
}
std::string digest(const uint8_t *p, size_t n) {
    uint8_t hash[32]; char hex[65];
    psx_sha256_compute(p,n,hash);
    for(unsigned i=0;i<32;i++) std::snprintf(hex+i*2,3,"%02x",hash[i]);
    return hex;
}
Bytes decode(const Bytes &raw, uint32_t &declared, uint32_t &state) {
    if(raw.size()<10 || std::memcmp(raw.data(),"GAM\0",4)) throw std::runtime_error("GAM header");
    declared=uint32_t(raw[4]) | uint32_t(raw[5])<<8 | uint32_t(raw[7])<<8 | uint32_t(raw[6])<<16;
    if(!declared || declared>2*1024*1024) throw std::runtime_error("GAM size");
    Bytes out; out.reserve(declared+255);
    size_t pos=10;
    unsigned bit=0, flags=raw[8] | unsigned(raw[9])<<8;
    while(out.size()<declared) {
        if(pos>=raw.size()) throw std::runtime_error("GAM literal bound");
        if(flags & (1u<<bit)) {
            if(pos+2>raw.size()) throw std::runtime_error("GAM token bound");
            unsigned distance=raw[pos++], length=raw[pos++];
            if(!distance || distance>out.size() || !length) throw std::runtime_error("GAM reference");
            while(length--) out.push_back(out[out.size()-distance]);
        } else out.push_back(raw[pos++]);
        if(++bit==16) {
            if(pos+2>raw.size()) throw std::runtime_error("GAM flags bound");
            flags=raw[pos] | unsigned(raw[pos+1])<<8; pos+=2; bit=0;
        }
    }
    state=flags | bit<<16;
    return out;
}

std::filesystem::path cache_path() {
    if(const char *p=std::getenv("TOMBA_SEAMLESS_CACHE"))
        if(*p) return std::filesystem::path(p)/"c259ec7ff6ef4163-gam-v1.pack";
    std::filesystem::path root;
#ifdef _WIN32
    if(const char *p=std::getenv("LOCALAPPDATA")) root=p;
#else
    if(const char *p=std::getenv("XDG_CACHE_HOME")) root=p;
    else if(const char *p=std::getenv("HOME")) root=std::filesystem::path(p)/".cache";
#endif
    if(root.empty()) throw std::runtime_error("No writable cache location");
    return root/"TombaRecomp"/"seamless"/"c259ec7ff6ef4163-gam-v1.pack";
}

void prepare(const std::filesystem::path &path) {
    std::fprintf(stdout,"seamless: preparing game assets from your disc (one time)\n");
    std::fflush(stdout);
    Bytes payload, entries;
    std::unordered_map<std::string,uint32_t> blobs;
    auto add=[&](const Bytes &bytes) {
        auto hash=digest(bytes.data(),bytes.size());
        auto it=blobs.find(hash);
        if(it!=blobs.end()) return it->second;
        uint32_t offset=uint32_t(payload.size());
        if(payload.size()+bytes.size()>256*1024*1024) throw std::runtime_error("Pack size limit");
        blobs.emplace(std::move(hash),offset);
        payload.insert(payload.end(),bytes.begin(),bytes.end());
        return offset;
    };
    for(const auto &item:catalog) {
        /* All final-sector padding is zero on this exact verified disc.
         * Catalog source hashes reject other editions or modified assets.
         * The offline sector probe verified padding for all 1062 entries. */
        Bytes raw((item.size+2047)&~2047u,0), decoded;
        uint32_t actual=0, declared=0, state=0;
        if(!psx_mod_read_disc_file(item.path,raw.data(),uint32_t(raw.size()),&actual) ||
           actual!=item.size || digest(raw.data(),item.size)!=item.source_sha256)
            throw std::runtime_error(std::string("Disc asset mismatch: ")+item.path);
        if(item.decoded_size) {
            decoded=decode(raw,declared,state);
            if(decoded.size()!=item.decoded_size || digest(decoded.data(),decoded.size())!=item.decoded_sha256)
                throw std::runtime_error(std::string("Decoded asset mismatch: ")+item.path);
        }
        put32(entries,item.lba); put32(entries,item.size);
        put32(entries,add(raw)); put32(entries,uint32_t(raw.size()));
        put32(entries,add(decoded)); put32(entries,uint32_t(decoded.size()));
        put32(entries,declared); put32(entries,state);
    }
    uint32_t hash=2166136261u;
    for(auto b:entries) hash=(hash^b)*16777619u;
    for(auto b:payload) hash=(hash^b)*16777619u;
    Bytes header{'T','M','B','P','K','0','0','1'};
    put32(header,uint32_t(std::size(catalog))); put32(header,uint32_t(payload.size()));
    const uint8_t sha1[]={0xc2,0x59,0xec,0x7f,0xf6,0xef,0x41,0x63,0x91,0x39,0x91,0xf4,0xe4,0xdb,0x2e,0xff,0x71,0x70,0x28,0x18};
    header.insert(header.end(),std::begin(sha1),std::end(sha1)); put32(header,hash); header.resize(48);
    std::filesystem::create_directories(path.parent_path());
    auto temporary=path;
#ifdef _WIN32
    temporary+="."+std::to_string(GetCurrentProcessId())+".tmp";
#else
    temporary+="."+std::to_string(getpid())+".tmp";
#endif
    {
        std::ofstream out(temporary,std::ios::binary|std::ios::trunc);
        out.write(reinterpret_cast<const char*>(header.data()),header.size());
        out.write(reinterpret_cast<const char*>(entries.data()),entries.size());
        out.write(reinterpret_cast<const char*>(payload.data()),payload.size());
        out.close();
        if(!out) throw std::runtime_error("Cannot write prepared asset cache");
    }
    /* Only our exact versioned cache file is replaced. An interrupted build
     * leaves .tmp unused, and the next launch retries preparation. */
#ifdef _WIN32
    if(!MoveFileExW(temporary.c_str(),path.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH))
        throw std::runtime_error("Cannot publish prepared asset cache");
#else
    std::filesystem::rename(temporary,path);
#endif
    std::fprintf(stdout,"seamless: prepared %zu assets, %zu bytes; cached at %s\n",
                 std::size(catalog),payload.size(),path.string().c_str());
}
}

extern "C" double tomba_seamless_now_ms(void) {
    return std::chrono::duration<double,std::milli>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
}

extern "C" const char *tomba_seamless_prepare_path(int rebuild) {
    static std::string path;
    try {
        if(const char *explicit_path=std::getenv("TOMBA_SEAMLESS_PACK")) {
            if(*explicit_path) { path=explicit_path; return path.c_str(); }
        }
        auto target=cache_path();
        if(rebuild || !std::filesystem::exists(target)) prepare(target);
        path=target.string();
        return path.c_str();
    } catch(const std::exception &e) {
        std::fprintf(stderr,"seamless: asset preparation failed: %s\n",e.what());
        return nullptr;
    }
}
