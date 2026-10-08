#include "mod_plugins.h"
#include <stdio.h>
PSX_MOD_CONSTRUCTOR(tomba_geometry_build_identity) {
    fprintf(stdout, "tomba geometry implementation: %s\n", TOMBA_GEOMETRY_IMPL);
}
