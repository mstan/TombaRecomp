/* Resident Tomba assets, one per catalogued disc file (catalog order). */
#ifndef TOMBA_SEAMLESS_ASSETS_H
#define TOMBA_SEAMLESS_ASSETS_H
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct TombaAsset {
    uint32_t lba, size;             /* effective-disc extent */
    const uint8_t *raw;             /* whole sectors */
    uint32_t raw_len;
    const uint8_t *decoded;         /* GAM output, or NULL */
    uint32_t decoded_len, declared, codec_state;
} TombaAsset;

/* Load (verified) or build the resident pack; NULL keeps retail loading. */
const TombaAsset *tomba_seamless_prepare(uint32_t *count);
double tomba_seamless_now_ms(void);

#ifdef __cplusplus
}
#endif
#endif
