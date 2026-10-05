/* Integration test using an owner-supplied disc, through the framework's
 * resident pack (mod_resident.cpp) with its disc and plan services replaced
 * by readers of the real image. No disc data is distributed. The catalogued
 * GAM outputs were verified separately against the original MIPS decoder
 * (tools/seamless_asset_probe.py --oracle). */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include "mod_runtime.h"
#include "psx_sha256.h"
#include "../src/mods/tomba_seamless_assets.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

struct CatalogEntry {
    const char *path;
    uint32_t lba, size;
    const char *source_sha256;
    uint32_t decoded_size;
    const char *decoded_sha256;
};
#include "../src/mods/tomba_seamless_catalog.inc"
static std::ifstream disc;
static unsigned reads;
static bool available = true;
static int patch_file = -1;   /* simulated asset mod: break one GAM header */
static std::string fingerprint = "stock-test-plan";
static const CatalogEntry *entry(const char *path) {
    for (const auto &c : catalog) if (!std::strcmp(c.path, path)) return &c;
    return nullptr;
}
namespace PSXRecompV4 {
const std::string &mod_runtime_fingerprint() { return fingerprint; }
bool mod_runtime_read_disc_file_sectors(const std::string &path, uint32_t, std::vector<uint8_t> &padded,
                                        uint32_t &lba, uint32_t &size, std::string *error) {
    ++reads;
    padded.clear();
    const CatalogEntry *c = entry(path.c_str());
    if (!available || !c) { if (error) *error = path + ": unavailable"; return false; }
    padded.resize((c->size + 2047u) & ~2047u);
    for (unsigned s = 0; s < padded.size() / 2048; s++) {
        unsigned char raw[2352];
        disc.clear();
        disc.seekg(uint64_t(c->lba + s) * 2352);
        if (!disc.read(reinterpret_cast<char *>(raw), sizeof raw) || raw[15] != 2 || (raw[18] & 0x20)) return false;
        std::memcpy(padded.data() + s * 2048u, raw + 24, 2048);
    }
    if (patch_file >= 0 && c == &catalog[patch_file]) padded[0] ^= 0xFF;
    lba = c->lba; size = c->size;
    return true;
}
}
extern "C" int psx_mod_disc_file_extent(const char *path, uint32_t *lba, uint32_t *size) {
    const CatalogEntry *c = entry(path);
    if (!c) return 0;
    *lba = c->lba; *size = c->size;
    return 1;
}
extern "C" void psx_mod_counter_add(const char *, uint32_t) {}
extern "C" uint8_t psx_mod_read_byte(uint32_t) { return 0; }
static void require(bool condition, const char *message) {
    if (!condition) { std::fprintf(stderr, "FAIL: %s\n", message); std::exit(1); }
}
static std::string hash(const uint8_t *p, size_t n) {
    uint8_t bytes[32]; char hex[65]; psx_sha256_compute(p, n, bytes);
    for (unsigned i = 0; i < 32; i++) std::snprintf(hex + 2 * i, 3, "%02x", bytes[i]);
    return hex;
}
int main(int argc, char **argv) {
    if (argc != 3) { std::fprintf(stderr, "usage: tomba-seamless-prepare-tests disc.bin scratch-directory\n"); return 2; }
    const auto cache = std::filesystem::absolute(argv[2]) /
        ("run-" + std::to_string(std::filesystem::file_time_type::clock::now().time_since_epoch().count()));
    require(!std::filesystem::exists(cache), "test requires a fresh cache directory");
#ifdef _WIN32
    _putenv_s("PSX_RESIDENT_CACHE", cache.string().c_str());
#else
    setenv("PSX_RESIDENT_CACHE", cache.string().c_str(), 1);
#endif
    disc.open(argv[1], std::ios::binary); require(bool(disc), "disc open");
    uint32_t count = 0;
    const TombaAsset *assets = tomba_seamless_prepare(&count);
    require(assets && count == std::size(catalog) && reads == std::size(catalog), "cold native preparation");
    unsigned decoded = 0, gam_index = ~0u;
    for (unsigned i = 0; i < count; i++) {
        const auto &a = assets[i];
        const auto &c = catalog[i];
        require(a.lba == c.lba && a.size == c.size && a.raw_len == ((c.size + 2047u) & ~2047u),
                "asset extent");
        require(hash(a.raw, a.raw_len) == c.source_sha256, "resident sector hash");
        if (c.decoded_size) {
            require(a.decoded && a.decoded_len == c.decoded_size &&
                    hash(a.decoded, a.decoded_len) == c.decoded_sha256 && a.declared &&
                    a.declared <= a.decoded_len, "decoded GAM matches the original decoder");
            ++decoded;
            if (gam_index == ~0u) gam_index = i;
        } else {
            require(!a.decoded && !a.decoded_len, "raw asset has no decoded output");
        }
    }
    reads = 0; available = false;
    assets = tomba_seamless_prepare(&count);
    require(assets && reads == 0, "warm launch uses the verified pack");
    std::filesystem::path pack;
    for (const auto &e : std::filesystem::recursive_directory_iterator(cache))
        if (e.path().extension() == ".pack") pack = e.path();
    require(!pack.empty(), "pack published");
    fingerprint = "changed-asset-plan";
    require(!tomba_seamless_prepare(&count), "changed mod plan cannot reuse warm stock cache");
    /* A modded GAM stream that no longer decodes is served raw; the game's own
     * decompressor handles it (no prepared output). */
    available = true; patch_file = int(gam_index);
    assets = tomba_seamless_prepare(&count);
    require(assets && !assets[gam_index].decoded && assets[gam_index].raw[0] == uint8_t('G' ^ 0xFF),
            "modded plan prepared from the effective disc");
    fingerprint = "stock-test-plan"; patch_file = -1; available = false;
    assets = tomba_seamless_prepare(&count);
    require(assets && assets[gam_index].decoded, "return to original mod plan");
    { std::fstream out(pack, std::ios::in | std::ios::out | std::ios::binary); out.seekp(1 << 20); out.put(char(0xAA)); }
    available = true; reads = 0;
    assets = tomba_seamless_prepare(&count);
    require(assets && reads == std::size(catalog), "corrupt pack rebuilt from the disc");
    { std::ofstream out(pack, std::ios::binary | std::ios::trunc); out.write("PSXRES01", 8); }
    available = false;
    require(!tomba_seamless_prepare(&count), "failed repair keeps retail loading");
    std::error_code ec;
    std::filesystem::remove_all(cache, ec);
    std::printf("PASS: cold/warm preparation, %zu sector hashes, %u decoded GAM hashes, modded stream, "
                "corruption repair, fail-closed fallback\n", std::size(catalog), decoded);
}
