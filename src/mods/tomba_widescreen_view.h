#ifndef TOMBA_WIDESCREEN_VIEW_H
#define TOMBA_WIDESCREEN_VIEW_H
#include <string.h>

typedef struct {
    unsigned numerator, denominator;
    int fit;
} TombaWidescreenView;

/* All choices use the same native-wide renderer. Unknown/old state defaults
 * to Fit, never to the retired fixed-16:9 squash path. */
static inline TombaWidescreenView tomba_widescreen_view(const char* value) {
    TombaWidescreenView view = {16, 9, 1};
    if (value && strcmp(value, "16:9") == 0) view.fit = 0;
    if (value && strcmp(value, "21:9") == 0) { view.numerator = 21; view.fit = 0; }
    if (value && strcmp(value, "32:9") == 0) { view.numerator = 32; view.fit = 0; }
    return view;
}
#endif
