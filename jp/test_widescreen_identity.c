/* Host-only adapter fixture, never a gameplay-state injection. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "cpu_state.h"
#include "eu_widescreen.h"
static unsigned char image[1024*1024];static size_t size;static int started,calls;
static PSXModFunctionEntryCallback callbacks[3];static uint32_t addresses[3];static unsigned count;
int psx_mod_game_started(void){return started;}
uint32_t psx_mod_read_word(uint32_t pc){size_t a=pc-0x80010000u+2048;assert(a+4<=size);return (uint32_t)image[a]|(uint32_t)image[a+1]<<8|(uint32_t)image[a+2]<<16|(uint32_t)image[a+3]<<24;}
int psx_mod_register_function_entry_plugin(const char*n,uint32_t a,PSXModFunctionEntryCallback c){(void)n;assert(count<3);addresses[count]=a;callbacks[count++]=c;return 1;}
static void callback(CPUState*c,uint32_t a){(void)c;(void)a;calls++;}
int main(int argc,char**argv){
 assert(argc==2);FILE*f=fopen(argv[1],"rb");assert(f);size=fread(image,1,sizeof image,f);fclose(f);
 assert(eu_ws_register_entry_plugin("tomba.widescreen",0x800636a4u,callback));
 assert(eu_ws_register_entry_plugin("tomba.widescreen",0x8005e08cu,callback));
 assert(eu_ws_register_entry_plugin("tomba.widescreen",0x8005a184u,callback));assert(count==3);
 assert(!eu_ws_refresh());started=1;assert(eu_ws_refresh());
 assert(eu_ws_address(0x8009bcc8u)==0x8009e508u);assert(eu_ws_address(0x800a38b8u)==0x800a6098u);
 assert(eu_ws_address(0x8005e08cu)==0x8005af80u);assert(eu_ws_address(0x80023608u)==0x800219f0u);
 assert(eu_ws_code_key(0x8004bac4u)==0x8004e4c4u);
 for(unsigned i=0;i<count;i++)callbacks[i](NULL,addresses[i]);assert(calls==3);
 memset(image+2048+0x6740,0,64);assert(!eu_ws_refresh());assert(!eu_ws_address(0x8009bcc8u));
 calls=0;for(unsigned i=0;i<count;i++)callbacks[i](NULL,addresses[i]);assert(!calls);
 puts("PASS: real Japan MAIN, HUD reverse map, callback gates and unknown-image rejection");
}
