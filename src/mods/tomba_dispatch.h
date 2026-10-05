#pragma once
#include "cpu_state.h"

typedef int (*TombaDispatchHook)(CPUState*, uint32_t);
void tomba_dispatch_register(TombaDispatchHook hook);
void tomba_dispatch_install(void);
