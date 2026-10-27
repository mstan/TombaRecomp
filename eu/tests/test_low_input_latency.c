/* Optional original-disc contract test: pass the owner's extracted MAIN0..4.
 * No retail bytes, cards, rendering or network are needed in this fixture. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../low_input_latency.c"

static unsigned char image[0x90000];
static uint32_t sample;
static int allowed, reads;
uint8_t psx_mod_read_byte(uint32_t pc) {
    return pc>=0x80010000u && pc<0x800a0000u?image[pc-0x80010000u]:0;
}
uint16_t psx_mod_read_half(uint32_t pc) {
    return psx_mod_read_byte(pc)|(uint16_t)psx_mod_read_byte(pc+1)<<8;
}
int psx_mod_read_digital_pad(uint32_t player,PSXModDigitalPadReader *r,
                            uint32_t legacy,uint32_t *buttons) {
    (void)r;(void)legacy;assert(player==0);++reads;
    *buttons=sample;return allowed;
}
int psx_mod_register_session_reset_plugin(const char *id,PSXModActivationCallback cb) {(void)id;(void)cb;return 1;}
int psx_mod_register_activation_plugin(const char *id,PSXModActivationCallback cb) {(void)id;(void)cb;return 1;}
int psx_mod_register_savestate_plugin(const char *id,PSXModVBlankCallback cb) {(void)id;(void)cb;return 1;}
int psx_mod_register_instruction_plugin(const char *id,uint32_t pc,uint32_t word,PSXModFunctionEntryCallback cb) {
    (void)id;(void)cb;assert(pc==0x800263b4u && word==0x03e00008u);return 1;
}
int main(int argc,char **argv) {
    if(argc<2)return 77;
    for(int language=0;language<argc-1;++language) {
        FILE *f=fopen(argv[language+1],"rb");assert(f);assert(!fseek(f,2048,SEEK_SET));
        memset(image,0,sizeof image);assert(fread(image,1,sizeof image,f)>0x163bc);fclose(f);
        image[0x8f7f0]=0;image[0x8d610]=4;image[0x8d611]=0;
        CPUState cpu;memset(&cpu,0x5a,sizeof cpu);cpu.gpr[31]=0x8001f88cu;
        CPUState before=cpu;allowed=1;reads=0;
        if(language==0) {
            for(unsigned bits=0;bits<65536;++bits) {
                cpu=before;sample=bits;read_return(&cpu,0x800263b4u);
                CPUState expected=before;expected.gpr[2]=(uint32_t)(int32_t)(int16_t)bits;
                assert(!memcmp(&cpu,&expected,sizeof cpu));
            }
            assert(reads==65536);
            allowed=0;cpu=before;read_return(&cpu,0x800263b4u);assert(!memcmp(&cpu,&before,sizeof cpu));
            allowed=1;cpu=before;cpu.gpr[31]=0;before=cpu;reads=0;
            read_return(&cpu,0x800263b4u);assert(!reads && !memcmp(&cpu,&before,sizeof cpu));
            cpu.gpr[31]=0x8001f88cu;before=cpu;image[0x8d610]=7;reads=0;
            read_return(&cpu,0x800263b4u);assert(!reads && !memcmp(&cpu,&before,sizeof cpu));
            image[0x8d610]=4;image[0x8f7f0]=0xff;reads=0;
            read_return(&cpu,0x800263b4u);assert(!reads && !memcmp(&cpu,&before,sizeof cpu));
        } else {
            read_return(&cpu,0x800263b4u);assert(!reads && !memcmp(&cpu,&before,sizeof cpu));
        }
    }
    puts("PASS EU1 reader: all 65536 returns, register preservation, unsupported languages, wrong caller, disconnect and analog fallback");
}
