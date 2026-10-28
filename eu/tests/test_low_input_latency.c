/* Optional original-disc contract test: pass owner-extracted executables.
 * No retail bytes, cards, rendering or network are needed in this fixture. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../low_input_latency.c"
static unsigned char image[0x200000];
static uint32_t sample,last_legacy;
static int allowed,reads;
uint8_t psx_mod_read_byte(uint32_t pc) {return (pc&0x1fffffffu)<sizeof image?image[pc&0x1fffffffu]:0;}
uint16_t psx_mod_read_half(uint32_t pc) {return psx_mod_read_byte(pc)|(uint16_t)psx_mod_read_byte(pc+1)<<8;}
uint32_t psx_mod_read_word(uint32_t pc) {return psx_mod_read_half(pc)|(uint32_t)psx_mod_read_half(pc+2)<<16;}
static void put(uint32_t a,uint32_t v) {for(int i=0;i<4;++i)image[(a&0x1fffffu)+i]=(uint8_t)(v>>(8*i));}
int psx_mod_read_digital_pad(uint32_t player,PSXModDigitalPadReader *r,uint32_t old,uint32_t *out) {
    (void)r;last_legacy=old;assert(player==0);++reads;*out=sample;return allowed;
}
int psx_mod_register_session_reset_plugin(const char *id,PSXModActivationCallback cb) {(void)id;(void)cb;return 1;}
int psx_mod_register_activation_plugin(const char *id,PSXModActivationCallback cb) {(void)id;(void)cb;return 1;}
int psx_mod_register_savestate_plugin(const char *id,PSXModVBlankCallback cb) {(void)id;(void)cb;return 1;}
int psx_mod_register_instruction_plugin(const char *id,uint32_t pc,uint32_t word,PSXModFunctionEntryCallback cb) {
    (void)id;(void)cb;
    for(unsigned i=0;i<sizeof input_profiles/sizeof *input_profiles;++i)
        if(input_profiles[i].hook==pc && input_profiles[i].instruction==word)return 1;
    assert(0);return 0;
}
int main(int argc,char **argv) {
    if(argc<2)return 77;
    for(int input=1;input<argc;++input) {
        FILE *f=fopen(argv[input],"rb");assert(f);assert(!fseek(f,2048,SEEK_SET));
        memset(image,0,sizeof image);assert(fread(image+0x10000,1,sizeof image-0x10000,f)>0x20000);fclose(f);
        const TombaInputProfile *p=0;
        for(unsigned i=0;i<sizeof input_profiles/sizeof *input_profiles;++i) {
            const TombaInputProfile *q=&input_profiles[i];
            if(body_hash(q->start,q->size)==q->hash && body_hash(q->extra,q->extra_size)==q->extra_hash) {p=q;break;}
        }
        assert(p);assert(psx_mod_read_word(p->hook)==p->instruction);
        if(p->kind)put(p->field1,1);
        else {image[p->field0&0x1fffffu]=0;put(p->field1,4);}
        CPUState before;memset(&before,0x5a,sizeof before);before.gpr[31]=p->caller;
        if(p->kind)before.gpr[4]=p->field0;
        allowed=1;reads=0;
        for(unsigned bit=0;bit<18;++bit) {
            sample=bit<16?1u<<bit:bit==16?0:65535;
            CPUState cpu=before,expected=before;
            expected.gpr[2]=p->kind?((sample>>8)&0xffu)|((sample&0xffu)<<8):(uint32_t)(int32_t)(int16_t)(uint16_t)sample;
            read_return(&cpu,p->hook);assert(!memcmp(&cpu,&expected,sizeof cpu));
        }
        assert(reads==18);
        /* Both verified Japanese callers reach the same original P1 store.
         * Exercise each, not just the first matching regional profile. */
        if(p->kind) {
            for(unsigned i=0;i<sizeof input_profiles/sizeof *input_profiles;++i) {
                const TombaInputProfile *q=&input_profiles[i];
                if(q->kind!=p->kind || q->hash!=p->hash || q->start!=p->start)continue;
                CPUState call=before,expected=before;
                call.gpr[31]=expected.gpr[31]=q->caller;
                sample=0xa55au;expected.gpr[2]=0x5aa5u;
                int count=reads;read_return(&call,q->hook);
                assert(reads==count+1 && !memcmp(&call,&expected,sizeof call));
            }
        }
        /* Priming/fallback receives canonical buttons while preserving the
         * original guest result when the host reader declines. */
        CPUState raw=before;raw.gpr[2]=0x1234u;CPUState original=raw;
        allowed=0;read_return(&raw,p->hook);
        assert(last_legacy==(p->kind?0x3412u:0x1234u));
        assert(!memcmp(&raw,&original,sizeof raw));
        CPUState cpu=before;allowed=0;read_return(&cpu,p->hook);assert(!memcmp(&cpu,&before,sizeof cpu));
        allowed=1;cpu=before;cpu.gpr[31]=0;CPUState bad=cpu;reads=0;
        read_return(&cpu,p->hook);assert(!reads && !memcmp(&cpu,&bad,sizeof cpu));
        if(p->kind)put(p->field1,0);else put(p->field1,7);
        cpu=before;reads=0;read_return(&cpu,p->hook);assert(!reads && !memcmp(&cpu,&before,sizeof cpu));
        if(p->kind)put(p->field1,1);else put(p->field1,4);
        image[p->start&0x1fffffu]^=1;cpu=before;reads=0;
        read_return(&cpu,p->hook);assert(!reads && !memcmp(&cpu,&before,sizeof cpu));
        printf("PASS original input ABI: %s\n",argv[input]);
    }
}
