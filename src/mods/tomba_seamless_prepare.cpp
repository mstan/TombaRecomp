/* Tomba assets held resident through the framework's resident disc packs
 * (mod_resident.h): read once from the effective (mod-patched) disc, decoded
 * with the original GAM codec, SHA-256 verified and cached per mod plan. No
 * compiler, Python, generated game C, source checkout or external extractor is
 * involved, and the pack never holds initialized game state. */
#include "mod_plugins.h"
#include "mod_resident.h"
#include "psx_sha256.h"
#include "tomba_seamless_assets.h"
#include <chrono>
#include <cstdio>
#include <cstring>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using Bytes = std::vector<uint8_t>;
struct CatalogEntry {
    const char *path;
    uint32_t lba, size;
    const char *source_sha256;   /* whole sectors */
    uint32_t decoded_size;       /* nonzero: GAM-compressed */
    const char *decoded_sha256;
};
#include "tomba_seamless_catalog.inc"

constexpr uint32_t kGamTag = 0x444D4147u; /* 'GAMD' */
std::vector<TombaAsset> assets;

std::string digest(const uint8_t *p, size_t n) {
    uint8_t hash[32];
    char hex[65];
    psx_sha256_compute(p, n, hash);
    for (unsigned i = 0; i < 32; i++) std::snprintf(hex + i * 2, 3, "%02x", hash[i]);
    return hex;
}

/* 8003EF50: 16 flag bits, least significant first; 0 = literal, 1 =
 * (distance:u8, length:u8) copied forward with overlap. The game checks the
 * output size only after a whole token, so up to 254 bytes past the declared
 * size are produced; `state` is the decoder's final flag word and bit index. */
Bytes decode(const uint8_t *raw, size_t n, uint32_t &declared, uint32_t &state) {
    if (n < 10 || std::memcmp(raw, "GAM\0", 4)) throw std::runtime_error("GAM header");
    declared = uint32_t(raw[4]) | uint32_t(raw[5]) << 8 | uint32_t(raw[7]) << 8 | uint32_t(raw[6]) << 16;
    if (!declared || declared > 2 * 1024 * 1024) throw std::runtime_error("GAM size");
    Bytes out;
    out.reserve(declared + 255);
    size_t pos = 10;
    unsigned bit = 0, flags = raw[8] | unsigned(raw[9]) << 8;
    while (out.size() < declared) {
        if (pos >= n) throw std::runtime_error("GAM literal bound");
        if (flags & (1u << bit)) {
            if (pos + 2 > n) throw std::runtime_error("GAM token bound");
            unsigned distance = raw[pos++], length = raw[pos++];
            if (!distance || distance > out.size() || !length) throw std::runtime_error("GAM reference");
            while (length--) out.push_back(out[out.size() - distance]);
        } else {
            out.push_back(raw[pos++]);
        }
        if (++bit == 16) {
            if (pos + 2 > n) throw std::runtime_error("GAM flags bound");
            flags = raw[pos] | unsigned(raw[pos + 1]) << 8;
            pos += 2;
            bit = 0;
        }
    }
    state = flags | bit << 16;
    return out;
}

/* Original GAM files must decode to their catalogued output; a decode
 * mismatch there is a codec defect and fails preparation. A mod-changed GAM
 * file that does not decode keeps the game's own decompressor for it. */
int derive(PSXResidentSink *sink, uint32_t file, const uint8_t *data, uint32_t size, int stock, void *) {
    const auto &item = catalog[file];
    if (!item.decoded_size) return 1;
    uint32_t declared = 0, state = 0;
    Bytes out;
    try {
        out = decode(data, size, declared, state);
    } catch (const std::exception &) {
        return stock ? 0 : 1;
    }
    if (stock && (out.size() != item.decoded_size || digest(out.data(), out.size()) != item.decoded_sha256))
        return 0;
    const uint32_t meta[4] = {declared, state, uint32_t(out.size()), 0};
    return psx_resident_emit(sink, file, kGamTag, meta, out.data(), uint32_t(out.size()));
}
}  // namespace

extern "C" double tomba_seamless_now_ms(void) {
    return std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
}

extern "C" const TombaAsset *tomba_seamless_prepare(uint32_t *count) {
    static PSXResidentFile files[std::size(catalog)];
    for (size_t i = 0; i < std::size(catalog); i++)
        files[i] = {catalog[i].path, catalog[i].size, catalog[i].source_sha256};
    PSXResidentSpec spec{};
    spec.struct_size = sizeof spec;
    spec.title = "TombaRecomp";
    spec.format = "scus94236-gam-v2";
    spec.files = files;
    spec.file_count = uint32_t(std::size(files));
    spec.policy = PSX_RESIDENT_ALLOW_MODIFIED;
    spec.derive = derive;
    assets.clear();
    *count = 0;
    const PSXResidentPack *pack = psx_resident_prepare(&spec);
    if (!pack) return nullptr;
    assets.resize(std::size(catalog));
    for (uint32_t i = 0; i < assets.size(); i++) {
        auto &a = assets[i];
        a.raw = psx_resident_file(pack, i, &a.size, &a.raw_len);
        a.lba = psx_resident_file_lba(pack, i);
    }
    for (uint32_t d = 0; d < psx_resident_derived_count(pack); d++) {
        uint32_t file = 0, tag = 0, meta[4] = {}, size = 0;
        const uint8_t *p = psx_resident_derived(pack, d, &file, &tag, meta, &size);
        if (!p || tag != kGamTag || file >= assets.size()) continue;
        assets[file].decoded = p;
        assets[file].decoded_len = size;
        assets[file].declared = meta[0];
        assets[file].codec_state = meta[1];
    }
    psx_mod_counter_add("tomba.seamless.modified_files", psx_resident_modified_files(pack));
    *count = uint32_t(assets.size());
    return assets.data();
}
