/* Diagnostic scanner: compare shared C/C++ detector output against a RAM dump.
 * Not a game test: accepts a 2 MiB developer capture, never modifies it. */
#include <stdio.h>
#include <stdlib.h>
#include "../psxrecomp/runtime/include/ws_backdrop_detect.h"
int main(int argc, char** argv) {
    if (argc != 2) return 2;
    FILE* f = fopen(argv[1], "rb");
    if (!f) return 2;
    uint32_t* words = (uint32_t*)malloc(0x200000);
    if (!words) { fclose(f); return 2; }
    if (fread(words, 1, 0x200000, f) != 0x200000) {
        fclose(f); free(words); return 2;
    }
    fclose(f);
    WsBackdropSite sites[256];
    int n = psx_ws_find_backdrop_windows(words, 0x200000 / 4, 0x80000000u, sites, 256);
    for (int i = 0; i < n; ++i) {
        printf("%08X %d %d\n", sites[i].pc, sites[i].kind, sites[i].window_cols);
        int cols = 0;
        uint32_t off = sites[i].pc - 0x80000000u;
        uint32_t lo = off > 512 ? off - 512 : 0;
        uint32_t hi = off + 516 < 0x200000 ? off + 516 : 0x200000;
        int kind = psx_ws_backdrop_kind_at(words + lo / 4, (hi - lo) / 4,
                                          lo, off, &cols);
        if (kind != sites[i].kind || cols != sites[i].window_cols) {
            fprintf(stderr, "interpreter window mismatch at %08X\n", sites[i].pc);
            free(words); return 1;
        }
    }
    free(words);
    return 0;
}
