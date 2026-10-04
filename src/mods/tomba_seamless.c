/* SCUS-94236 resident-loader spike. No clock, CD latency, scheduler or audio
 * pacing changes. A request is completed only after its real resource writes.
 * The shipped binary prepares the asset pack once from the owner's disc. */
#include "mod_plugins.h"
#include "cpu_state.h"
#include "bios_hle.h"
#include "gpu.h"
#include "spu.h"
#include "memcard.h"
#include "dirty_ram_interp.h"
#include "psx_cycles.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    uint32_t lba, size, raw, raw_len, decoded, decoded_len, declared, codec_state;
} Asset;
static unsigned char *pack, *data;
static Asset *assets;
static uint32_t asset_count, data_len;
static int (*previous_hook)(CPUState *, uint32_t);
static unsigned batches, fallbacks, frame;
static unsigned last_batch_frame;
static int trace;
static int retail_reverb;
extern const char *tomba_seamless_prepare_path(int rebuild);
extern double tomba_seamless_now_ms(void);
extern uint8_t *memory_get_ram_ptr(void);

static uint32_t r32(uint32_t a) { return psx_mod_read_word(a); }
static uint16_t r16(uint32_t a) { return psx_mod_read_half(a); }
static uint8_t r8(uint32_t a) { return psx_mod_read_byte(a); }
static void w32(uint32_t a, uint32_t v) { psx_mod_write_word(a, v); }
static void w16(uint32_t a, uint16_t v) { psx_mod_write_half(a, v); }
static void w8(uint32_t a, uint8_t v) { psx_mod_write_byte(a, v); }
#include "tomba_seamless_spu.h"
static uint32_t u32(const unsigned char *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static int ram(uint32_t a, uint32_t n) {
    return a >= 0x80010000u && a <= 0x80200000u && n <= 0x80200000u-a;
}
static void copy_to_ram(uint32_t a, const unsigned char *p, uint32_t n) {
    /* Outside the static image, a bulk asset copy can invalidate by page.
     * Touch every affected page through the normal store boundary so watched
     * overlay generations advance too (the dirty bitmap alone is not enough).
     * Static text/data retains the full store path and its image guard. */
    if(n>=64 && a>=0x80098000u && ram(a,n)) {
        uint32_t phys=a&0x1FFFFFFFu;
        memcpy(memory_get_ram_ptr()+phys,p,n);
        dirty_ram_mark_executable_range(phys,n);
        for(uint32_t q=a;q<a+n;q=(q&~255u)+256)
            w8(q,p[q-a]);
        return;
    }
    while (n && (a & 3)) { w8(a++, *p++); --n; }
    while (n >= 4) { w32(a, u32(p)); a += 4; p += 4; n -= 4; }
    while (n--) w8(a++, *p++);
}
static unsigned bcd(unsigned x) { return (x >> 4)*10 + (x & 15); }
static const Asset *find_asset(unsigned id) {
    if (id > 2048) return NULL;
    uint32_t p = 0x800791A0u + id*8;
    uint32_t lba = (bcd(r8(p))*60 + bcd(r8(p+1)))*75 + bcd(r8(p+2));
    if (lba < 150) return NULL;
    lba -= 150;
    for (unsigned i = 0; i < asset_count; ++i)
        if (assets[i].lba == lba && assets[i].size == r32(p+4)) return assets+i;
    return NULL;
}

/* Only synchronous leaf services are called here, never the game's thread
 * wrappers. Preserve caller registers but keep hardware/deadline side effects. */
static uint32_t guest(CPUState *cpu, uint32_t pc, uint32_t ra,
                      uint32_t a0, uint32_t a1, uint32_t a2) {
    uint32_t regs[32], saved_pc=cpu->pc, hi=cpu->hi, lo=cpu->lo;
    memcpy(regs, cpu->gpr, sizeof(regs));
    cpu->gpr[4]=a0; cpu->gpr[5]=a1; cpu->gpr[6]=a2; cpu->gpr[31]=ra;
    psx_dispatch_call(cpu, pc, ra);
    uint32_t result=cpu->gpr[2];
    memcpy(cpu->gpr, regs, sizeof(regs));
    cpu->pc=saved_pc; cpu->hi=hi; cpu->lo=lo;
    return result;
}

typedef struct { const Asset *asset; uint32_t queue, desc, dest, scratch, raw_dest; unsigned mode, type; } Request;

static int plan_request(unsigned index, Request *r) {
    r->queue=0x8009E748u+index*8;
    r->desc=r32(r->queue); r->dest=r32(r->queue+4);
    if (!ram(r->desc,20)) return 0;
    r->asset=find_asset(r16(r->desc));
    if (!r->asset) return 0;
    uint32_t flags=r32(r->desc+16);
    r->mode=flags&15; r->type=r8(r->desc+3);
    r->scratch=(flags&16) ? 0x800B3188u : 0x800A3348u;
    if (r->mode>4) return 0;
    r->raw_dest=(r->mode==0 || r->mode==3) ? r->scratch : r->dest;
    if (!ram(r->raw_dest,r->asset->raw_len)) return 0;
    if (r->mode==1 || r->mode==3) {
        if (!r->asset->decoded_len || !ram(r->mode==1 ? r->scratch : r->dest,r->asset->decoded_len)) return 0;
    }
    if (r->mode==0 && (r->type&0xF0)!=0x10 && (r->type&0xF0)!=0x90) return 0;
    if (r->mode==1 || (r->mode==0 && (r->type&0xF0)==0x10)) {
        unsigned width=r16(r->desc+12), height=r16(r->desc+14);
        if (!width || width>1024 || !height || height>512 ||
            width*height*2 > (r->mode==1 ? r->asset->decoded_len : r->asset->raw_len)) return 0;
    }
    /* Sound tables are offsets into the raw bank. Validate before any write. */
    if ((r->type&0xF0)==0x90 && r->mode!=3 && r->mode!=1) {
        /* This adapter owns synchronous DMA-style banks only. A custom
         * transfer callback or PIO transfer has additional semantics. */
        if(r32(0x80097C64u) || r32(0x80097C80u) || r32(0x80097C70u)!=3) return 0;
        const unsigned char *p=data+r->asset->raw;
        unsigned n=r->asset->size, slot=r->type&15;
        if(slot==15) slot=0;
        if(n<36 || !ram(r->dest,n) || r->dest!=r->raw_dest) return 0;
        uint32_t samples=u32(p), headers=u32(p+4);
        if(samples>n-4 || headers>n-32) return 0;
        unsigned sh=u32(p+headers), ss=u32(p+samples);
        if(sh<4 || ss<4 || sh%4 || ss%4 || sh>n-headers || ss>n-samples) return 0;
        unsigned nh=sh/4-1, ns=ss/4-1;
        if(!nh || ns<nh || slot+ns>44 || slot+nh>44) return 0;
        for(unsigned i=0;i<=ns;i++) if(u32(p+samples+4*i)>n-samples) return 0;
        for(unsigned i=0;i<nh;i++) if(u32(p+headers+4*i)>n-headers-32) return 0;
        for(unsigned i=0;i<ns;i++) if(u32(p+samples+4*i)>u32(p+samples+4*(i+1))) return 0;
        if(r16(r->desc+14)>15) return 0;
        uint32_t spu_addr=r32(0x80077D50u+r16(r->desc+14)*8);
        if((spu_addr&7) || spu_addr<0x1010 || spu_addr>=0x80000) return 0;
        for(unsigned i=0;i<nh;i++) {
            uint32_t src=samples+u32(p+samples+4*i);
            uint32_t end=samples+u32(p+samples+4*(i+1==nh ? ns : i+1));
            uint32_t len=(end-src+63)&~63u;
            if(end-src>0x7EFF0 || src>r->asset->raw_len || len>r->asset->raw_len-src ||
               len>0x80000-spu_addr) return 0;
            spu_addr+=end-src;
        }
    }
    return 1;
}

static void install_sound(CPUState *cpu, const Request *r) {
    unsigned slot=r->type&15;
    if(slot==15) slot=0;
    uint32_t samples=r->dest+r32(r->dest), headers=r->dest+r32(r->dest+4);
    unsigned nh=(r32(headers)>>2)-1, ns=(r32(samples)>>2)-1;
    for(unsigned i=0;i<nh;i++) {
        int handle=(int16_t)r16(0x1F8003A8u+2*(slot+i));
        if(handle!=-1) guest(cpu,0x80073B54u,0x80021958u,(uint32_t)handle,0,0);
    }
    for(unsigned i=0;i<nh;i++) w32(0x8009C758u+4*(slot+i),headers+r32(headers+4*i));
    for(unsigned i=0;i<ns;i++) w32(0x8009C658u+4*(slot+i),samples+r32(samples+4*i));
    uint32_t spu_addr=r32(0x80077D50u+r16(r->desc+14)*8);
    for(unsigned i=0;i<nh;i++) {
        uint32_t src=r32(0x8009C658u+4*(slot+i));
        uint32_t end=(i+1==nh) ? samples+r32(samples+4*ns) : r32(0x8009C658u+4*(slot+i+1));
        /* Same sample writes as SpuWrite's 64-byte DMA blocks, completed
         * synchronously. Preserve library transfer state and use the SPU's
         * write path (including IRQ checks), without pumping DMA wait loops. */
        uint32_t bytes=(end-src+63)&~63u;
        w16(0x80097C60u,(uint16_t)(spu_addr>>3));
        w32(0x80097C98u,0); w32(0x80097C9Cu,src); w32(0x80097CA0u,bytes/64);
        spu_write(0x1F801DA6u,spu_addr>>3);
        uint16_t ctrl=spu_ctrl_read();
        spu_write(0x1F801DAAu,(ctrl&~0x30u)|0x20u);
        for(uint32_t j=0;j<bytes;j+=4) spu_dma_write(r32(src+j));
        spu_write(0x1F801DAAu,ctrl&~0x30u);
        w32(0x80097C7Cu,1);
        uint32_t handle=guest(cpu,0x80073CA8u,0x80021A94u,r32(0x8009C758u+4*(slot+i)),0xFFFFFFFFu,spu_addr);
        w16(0x1F8003A8u+2*(slot+i),(uint16_t)handle);
        guest(cpu,0x80073BD8u,0x80021AB4u,(uint32_t)(int32_t)(int16_t)handle,0,0);
        spu_addr+=end-src;
    }
}

static int install_batch(CPUState *cpu) {
    unsigned begin=r32(0x1F8002A0u), end=r32(0x1F80029Cu), count=0;
    Request requests[128];
    if(begin>=128 || end>=128 || begin==end || r16(0x801FD8E0u)) {
        ++fallbacks;
        fprintf(stdout,"seamless: queue fallback frame=%u begin=%u end=%u busy=%u\n",
                frame,begin,end,r16(0x801FD8E0u));
        return 0;
    }
    for(unsigned i=begin;i!=end;i=(i+1)&127) {
        if(!plan_request(i,requests+count)) {
            fprintf(stdout,"seamless: fallback frame=%u queue=%u desc=%08X id=%u flags=%X type=%X\n",frame,i,r32(0x8009E748u+i*8),r16(r32(0x8009E748u+i*8)),r32(r32(0x8009E748u+i*8)+16),r8(r32(0x8009E748u+i*8)+3));
            ++fallbacks; return 0;
        }
        ++count;
    }
    double start=tomba_seamless_now_ms(); uint64_t start_cycles=psx_get_cycle_count();
    /* A raw bank/overlay can reuse a previous frame's packet arena too.
     * Drain submitted work before the first RAM write, not only before a
     * texture upload after its scratch data has already been replaced. */
    guest(cpu,0x8005EB54u,0x8000FB00u,0,0,0);
    w8(0x1F8001CEu,0); w32(0x8009C8B0u,0);
    for(unsigned i=0;i<count;i++) {
        const Request *r=requests+i; const Asset *a=r->asset;
        double file_start=trace ? tomba_seamless_now_ms() : 0; unsigned file_frame=frame;
        w32(0x1F800288u,r->queue); w32(0x1F80028Cu,r->desc);
        w32(0x1F800290u,r->raw_dest); w32(0x1F800294u,a->raw_len/2048);
        copy_to_ram(r->raw_dest,data+a->raw,a->raw_len);
        if(r->mode==1 || r->mode==3) {
            copy_to_ram(r->mode==1 ? r->scratch : r->dest,data+a->decoded,a->decoded_len);
            w32(0x1F800070u,a->declared); w32(0x1F800074u,a->decoded_len);
            w16(0x8009B0CCu,(uint16_t)a->codec_state); w8(0x8009B0C8u,(uint8_t)(a->codec_state>>16));
        }
        if(r->mode==1 || (r->mode==0 && (r->type&0xF0)==0x10)) {
            /* Drain earlier PsyQ commands before installing this rectangle.
             * The native GP0 upload consumes the data before scratch reuse. */
            guest(cpu,0x8005EB54u,0x80021848u,0,0,0);
            gpu_set_gp0_source(r->scratch);
            gpu_write_gp1(0x04000000u);
            gpu_write_gp0(0x01000000u); /* PsyQ LoadImage invalidates the texture cache. */
            gpu_write_gp0(0xA0000000u);
            gpu_write_gp0(r32(r->desc+8));
            gpu_write_gp0(r32(r->desc+12));
            unsigned words=(r16(r->desc+12)*r16(r->desc+14)+1)/2;
            for(unsigned j=0;j<words;j++) {
                gpu_set_gp0_source(r->scratch+4*j);
                gpu_write_gp0(r32(r->scratch+4*j));
            }
            if(words>=16) gpu_write_gp1(0x04000002u);
        } else if((r->type&0xF0)==0x90 && r->mode!=3) install_sound(cpu,r);
        w32(0x1F8002A0u,(begin+i+1)&127);
        if(trace) fprintf(stdout,"seamless: file id=%u mode=%u type=%02X frames=%u..%u ms=%.3f\n",r16(r->desc),r->mode,r->type,file_frame,frame,tomba_seamless_now_ms()-file_start);
    }
    w8(0x1F8001CEu,1);
    ++batches;
    last_batch_frame=frame;
    fprintf(stdout,"seamless: batch=%u frame=%u files=%u ms=%.3f cycles=%llu area=%u/%u fallbacks=%u\n",batches,frame,count,tomba_seamless_now_ms()-start,(unsigned long long)(psx_get_cycle_count()-start_cycles),r16(0x8009BCC8u),r16(0x8009BCCAu),fallbacks);
    fflush(stdout);
    cpu->gpr[2]=1;
    return 1;
}

/* Tomba's read-only save-file service. The card subsystem already owns the
 * live bytes, including unsaved writes; read that image, never a stale disk
 * copy. Retail checksum validation and deserialization still run afterward.
 * This deliberately supports only Tomba's single-block save files. */
static int read_save(CPUState *cpu) {
    char name[26];
    if(cpu->gpr[6]!=0 || cpu->gpr[7]!=0xC00 || !ram(cpu->gpr[4],sizeof name) ||
       !ram(cpu->gpr[5],0xC00)) return 0;
    for(unsigned i=0;i<sizeof name;i++) name[i]=(char)r8(cpu->gpr[4]+i);
    if(name[25] || strncmp(name,"bu",2) || (name[2]!='0' && name[2]!='1') ||
       strncmp(name+3,"0:BASCUS-94236TOMBA-",20) || name[23]<'0' || name[23]>'9' ||
       name[24]<'0' || name[24]>'9') return 0;
    int card=name[2]-'0';
    uint8_t sector[128], bytes[0xC00];
    if(!memcard_is_present(card)) return 0;
    for(int block=1;block<=15;block++) {
        if(memcard_read_sector(card,block,sector)!=0) return 0;
        if(sector[0]!=0x51 || memcmp(sector+10,name+5,20)) continue;
        if(u32(sector+4)!=8192 || sector[8]!=0xFF || sector[9]!=0xFF) return 0;
        uint8_t checksum=0;
        for(unsigned i=0;i<127;i++) checksum^=sector[i];
        if(checksum!=sector[127]) return 0;
        for(unsigned i=0;i<sizeof bytes/128;i++)
            if(memcard_read_sector(card,block*64+(int)i,bytes+i*128)!=0) return 0;
        copy_to_ram(cpu->gpr[5],bytes,sizeof bytes);
        cpu->gpr[2]=0;
        fprintf(stdout,"seamless: save read card=%d block=%d bytes=%zu frame=%u\n",card,block,sizeof bytes,frame);
        return 1;
    }
    return 0;
}

/* SpuClearReverbWorkArea's actual writes, with its allocation guard intact.
 * The original sends the same 1 KiB buffer in small DMA jobs and waits for
 * each completion. Install those bytes directly through the existing SPU
 * write path. No music, envelope, sequencer or audio-output clock is advanced.
 * Mode setup and its temporary reverb disable remain in the retail caller. */
static int clear_reverb(CPUState *cpu) {
    unsigned mode=cpu->gpr[4];
    if(mode>=10 || r32(0x80097C70u)!=3 || r32(0x80097C64u) || r32(0x80097C80u) ||
       r32(0x80076400u)!=0x27BDFFC8u || (spu_ctrl_read()&0x80)) return 0;
    uint32_t units=r32(0x80097CB0u+4*mode);
    if(units>0x10000u) return 0;
    uint32_t begin=(mode ? units : 0xFFF0u)<<3;
    if(begin<0x1010u || begin>=0x80000u) return 0;
    if(guest(cpu,0x800758C0u,0x8000FC00u,units,0,0)) {
        cpu->gpr[2]=0xFFFFFFFFu; return 1;
    }
    tomba_reverb_transfer(begin);
    cpu->gpr[2]=0;
    return 1;
}

static int dispatch(CPUState *cpu, uint32_t phys) {
    if(!psx_mod_game_started() || r32(0x80021340u)!=0x27BDFF98u)
        return previous_hook ? previous_hook(cpu,phys) : 0;
    /* The exit actor's movement step can finish after its fade. In retail
     * it then spends a whole tick entering a pure fade-completion check.
     * Complete that already-ready check now; movement still runs once. */
    if(phys==0x2CFF4u && cpu->gpr[31]!=0x8000F900u &&
       ram(cpu->gpr[4],0x80) && r8(cpu->gpr[4]+6)==2 && !r8(0x8009BCA0u) &&
       r32(0x8002CFF4u)==0x3C02800Au && r32(0x8002D484u)==0x3C03800Au) {
        uint32_t actor=cpu->gpr[4], t=r32(0x1F8001D4u);
        unsigned state=r16(t+0x4C);
        if(r16(t+0x48)==1 && r16(t+0x4A)==1 && state>=1 && state<=6 && state!=3) {
            uint32_t result=guest(cpu,0x8002CFF4u,0x8000F900u,actor,0,0);
            if(r8(actor+6)==3 && r8(0x8009BCDDu)==1 && !r8(0x8009BCA0u) &&
               r16(t+0x4C)==state) {
                result=guest(cpu,0x8002CFF4u,0x8000F900u,actor,0,0);
                if(trace) {
                    fprintf(stdout,"seamless: exit movement complete frame=%u actor=%X state=%u..%u\n",
                            frame,actor,state,r16(t+0x4C));
                    fflush(stdout);
                }
            }
            cpu->gpr[2]=result; return 1;
        }
    }
    /* The final opening-logo tick builds old primitives immediately before
     * enqueuing the title's replacement assets. They would outlive their
     * packet storage with immediate installation, just like an area exit. */
    if(phys==0xE7D74u && cpu->gpr[31]==0x80019BC0u &&
       r32(0x800E7D5Cu)==0x3C02800Fu && r32(0x800E7D74u)==0x27BDFFE8u) {
        uint32_t t=r32(0x1F8001D4u);
        if(!r16(t+0x48) && r16(t+0x4A)==5 && r16(t+0x58)==1) return 1;
    }
    if(trace && phys==0x76400u && cpu->gpr[31]!=0x8000FD00u && cpu->gpr[4]<10) {
        unsigned mode=cpu->gpr[4];
        uint32_t begin=(mode ? r32(0x80097CB0u+4*mode) : 0xFFF0u)<<3;
        uint32_t before[48]; for(unsigned i=0;i<48;i++) before[i]=r32(0x80097C40u+4*i);
        uint16_t ctrl=spu_ctrl_read(), addr=(uint16_t)spu_read(0x1F801DA6u);
        double start=tomba_seamless_now_ms(); uint64_t cycles=psx_get_cycle_count(); unsigned f=frame;
        uint32_t result;
        if(retail_reverb || !clear_reverb(cpu))
            result=guest(cpu,0x80076400u,0x8000FD00u,mode,0,0);
        else result=cpu->gpr[2];
        unsigned nonzero=0;
        if(begin<0x80000) for(unsigned i=begin;i<0x80000;i++) nonzero+=spu_get_ram()[i]!=0;
        fprintf(stdout,"seamless: reverb oracle mode=%u begin=%X result=%d nonzero=%u ctrl=%X..%X addr=%X..%X frames=%u..%u ms=%.3f cycles=%llu\n",
                mode,begin,(int)result,nonzero,ctrl,spu_ctrl_read(),addr,spu_read(0x1F801DA6u),f,frame,
                tomba_seamless_now_ms()-start,(unsigned long long)(psx_get_cycle_count()-cycles));
        for(unsigned i=0;i<48;i++) if(before[i]!=r32(0x80097C40u+4*i))
            fprintf(stdout,"seamless: reverb global %08X %08X -> %08X\n",0x80097C40u+4*i,before[i],r32(0x80097C40u+4*i));
        fflush(stdout);cpu->gpr[2]=result;return 1;
    }
    if(phys==0x76400u && cpu->gpr[31]!=0x8000FD00u && !retail_reverb) {
        if(clear_reverb(cpu)) return 1;
        ++fallbacks;
        fprintf(stdout,"seamless: reverb fallback frame=%u mode=%u\n",frame,cpu->gpr[4]);
    }
    /* An ordinary exit has already committed to state 7 before its old
     * scene's render call. The parent adapter installs and draws the new
     * scene in this same tick. Do not enqueue old primitives referencing
     * the packet arena and textures that that installation will replace. */
    if(phys==0x46264u && cpu->gpr[31]>=0x8001B2B4u && cpu->gpr[31]<0x8001CAC0u) {
        uint32_t t=r32(0x1F8001D4u);
        if(r16(t+0x48)==1 && r16(t+0x4A)==1 && r16(t+0x4C)==7 && !r16(t+0x4E))
            return 1;
    }
    if(trace && cpu->gpr[31]!=0x8000FE00u &&
       (phys==0x1758Cu || phys==0x17AE0u || phys==0x243E8u || phys==0x246B0u ||
        phys==0x28EF4u || phys==0x59F7Cu || phys==0x2065Cu || phys==0x210A8u ||
        phys==0x6BB4Cu || phys==0x6B898u || phys==0x7594Cu ||
        phys==0x73CA8u || phys==0x73B54u || phys==0x73BD8u ||
        (batches && frame-last_batch_frame<=2 &&
         (phys==0x1B5A8u || phys==0x1C2E8u || phys==0x46264u ||
          phys==0x1DE24u || phys==0x3C78Cu || phys==0x11AF40u)))) {
        double start=tomba_seamless_now_ms(); uint64_t cycles=psx_get_cycle_count(); unsigned f=frame;
        uint32_t result=guest(cpu,0x80000000u|phys,0x8000FE00u,cpu->gpr[4],cpu->gpr[5],cpu->gpr[6]);
        fprintf(stdout,"seamless: init pc=%05X frames=%u..%u ms=%.3f cycles=%llu\n",
                phys,f,frame,tomba_seamless_now_ms()-start,(unsigned long long)(psx_get_cycle_count()-cycles));
        fflush(stdout);
        cpu->gpr[2]=result;
        return 1;
    }
    /* Some areas defer the fade actor's pure initialization until their
     * first update. Run that setup and its first fade step together, just
     * as areas whose actor is initialized by 59F7C already do. */
    if(phys==0x5AF70u && cpu->gpr[31]==0x8005A0CCu && ram(cpu->gpr[4],0x3C) &&
       !r8(cpu->gpr[4]+4) && r32(0x8005AF70u)==0x90830004u) {
        uint32_t a=cpu->gpr[4];
        guest(cpu,0x8005AF70u,0x8000FF00u,a,0,0);
        if(r8(a+4)==1) guest(cpu,0x8005AF70u,0x8000FF00u,a,0,0);
        return 1;
    }
    /* Pure array clearing from the scene-reset helpers. Preserve the retail
     * function's return and argument-register results, with no emulated
     * byte-at-a-time loop. This does not run or advance any scene scripts. */
    if(phys==0x5B814u && cpu->gpr[31]>=0x800177D8u && cpu->gpr[31]<0x80018248u &&
       (int32_t)cpu->gpr[6]>0 && ram(cpu->gpr[4],cpu->gpr[6]) &&
       r32(0x8005B814u)==0x10800009u) {
        unsigned char fill[256]; memset(fill,(uint8_t)cpu->gpr[5],sizeof fill);
        uint32_t begin=cpu->gpr[4], count=cpu->gpr[6];
        for(uint32_t i=0;i<count;) {
            uint32_t n=count-i<sizeof fill ? count-i : sizeof fill;
            copy_to_ram(begin+i,fill,n); i+=n;
        }
        cpu->gpr[2]=begin; cpu->gpr[4]=begin+count; cpu->gpr[6]=0;
        return 1;
    }
    /* Interpreted overlay-to-overlay calls stay inside the interpreter and
     * do not reach the dispatch hook. Two guarded JAL bridges route those
     * calls through existing compiled entry points, distinguished by the
     * exact original return PC. The overlay implementations remain intact. */
    if((phys==0x5B45Cu || (phys==0xB0u && cpu->gpr[9]==0x34u)) && cpu->gpr[31]==0x800E8964u &&
       r32(0x800E895Cu)==(0x0C000000u|(0x8005B45Cu>>2&0x03FFFFFFu))) {
        if(read_save(cpu)) return 1;
        ++fallbacks;
        fprintf(stdout,"seamless: save read fallback frame=%u\n",frame);
        cpu->gpr[2]=guest(cpu,0x800E7ACCu,0x800E8964u,cpu->gpr[4],cpu->gpr[5],cpu->gpr[6]);
        return 1;
    }
    if((phys==0x5B43Cu || (phys==0xB0u && cpu->gpr[9]==0x32u)) && cpu->gpr[31]==0x800E9258u &&
       r32(0x800E9250u)==(0x0C000000u|(0x8005B43Cu>>2&0x03FFFFFFu)))
        phys=0xE7ECCu;
    /* Overlay addresses are meaningful only for the verified menu image. */
    if(phys>=0xE7388u && phys<0xF62E0u && r32(0x800E7ACCu)==0x27BDFFD0u &&
       r32(0x800E7ECCu)==0x27BDFF68u && r32(0x800E9438u)==0x27BDFFE8u) {
        if(phys==0xE7ACCu && cpu->gpr[31]==0x800E8964u && read_save(cpu)) return 1;
        if(phys==0xE7ECCu && cpu->gpr[31]!=0x8000FF00u && cpu->gpr[4]==0x800A3940u &&
           !r16(0x800A395Cu)) {
            uint32_t result=guest(cpu,0x800E7ECCu,0x8000FF00u,cpu->gpr[4],cpu->gpr[5],cpu->gpr[6]);
            if(!result && r8(0x800A3942u)==9) {
                w16(0x800A3946u,1); /* cosmetic four-frame pre-read delay */
                result=guest(cpu,0x800E7ECCu,0x8000FF00u,cpu->gpr[4],cpu->gpr[5],cpu->gpr[6]);
                if(!result && r8(0x800A3942u)==10)
                    result=guest(cpu,0x800E7ECCu,0x8000FF00u,cpu->gpr[4],cpu->gpr[5],cpu->gpr[6]);
            }
            cpu->gpr[2]=result;
            return 1;
        }
        if(phys==0xE9EF8u) {
            uint32_t t=r32(0x1F8001D4u);
            if(r16(t+0x48)==2 && r16(t+0x4A)==3) return 1;
        }
    }
    /* Collapse only one-shot setup/completion states. Every original state
     * still executes its initialization; running gameplay is never looped.
     * The real epilogue PC is the nested call's return contract and bypass
     * discriminator, so no host recursion flag can survive a state restore. */
    if(phys==0x1A670u && cpu->gpr[31]!=0x8001A764u) {
        uint32_t t=r32(0x1F8001D4u);
        for(unsigned step=0;step<3 && r16(t+0x48)==0;step++) {
            unsigned old=r16(t+0x4A);
            guest(cpu,0x8001A670u,0x8001A764u,0,0,0);
            if(r16(t+0x4A)==old && r16(t+0x48)==0) break;
        }
        if(r16(t+0x48)==1 && r16(t+0x4A)==0)
            guest(cpu,0x8001A9F0u,0x8001A9B0u,0,0,0);
        return 1;
    }
    if(phys==0x1A774u && cpu->gpr[31]!=0x8001A944u) {
        uint32_t t=r32(0x1F8001D4u);
        if(r32(0x800E7ACCu)==0x27BDFFD0u && r32(0x800E7ECCu)==0x27BDFF68u &&
           r32(0x800E9438u)==0x27BDFFE8u) {
            if(r32(0x800E895Cu)==(0x0C000000u|(0x800E7ACCu>>2&0x03FFFFFFu)))
                psx_mod_write_code_word(0x800E895Cu,0x0C000000u|(0x8005B45Cu>>2&0x03FFFFFFu));
            if(r32(0x800E9250u)==(0x0C000000u|(0x800E7ECCu>>2&0x03FFFFFFu)))
                psx_mod_write_code_word(0x800E9250u,0x0C000000u|(0x8005B43Cu>>2&0x03FFFFFFu));
        }
        guest(cpu,0x8001A774u,0x8001A944u,0,0,0);
        if(r16(t+0x48)==2 && r16(t+0x4A)==3) {
            guest(cpu,0x8001A774u,0x8001A944u,0,0,0);
            if(r16(t+0x48)==1 && r16(t+0x4A)==1)
                guest(cpu,0x8001AC00u,0x8001A9C0u,0,0,0);
        }
        return 1;
    }
    if(phys==0x1A9F0u && cpu->gpr[31]!=0x8001ABF0u) {
        uint32_t t=r32(0x1F8001D4u);
        for(unsigned step=0;step<8 && r16(t+0x4A)==0;step++) {
            unsigned old=r16(t+0x4C), failed=fallbacks;
            if(old==3 && r8(0x1F8001CEu)) w16(t+0x4C,4);
            else guest(cpu,0x8001A9F0u,0x8001ABF0u,0,0,0);
            if(failed!=fallbacks || r16(t+0x4C)==old || r8(0x1F8001CCu)) break;
        }
        if(r16(t+0x4A)==1 && r16(t+0x4C)==1 && r16(t+0x4E)==0)
            guest(cpu,0x8001AC00u,0x8001A9C0u,0,0,0);
        return 1;
    }
    if(phys==0x1AC00u && cpu->gpr[31]!=0x8001AD0Cu) {
        uint32_t t=r32(0x1F8001D4u);
        double started=tomba_seamless_now_ms(); unsigned start_frame=frame, start_batches=batches;
        uint64_t start_cycles=psx_get_cycle_count();
        unsigned old=r16(t+0x4C), sub=r16(t+0x4E), failed=fallbacks;
        guest(cpu,0x8001AC00u,0x8001AD0Cu,0,0,0);
        unsigned next=r16(t+0x4C);
        /* An exit can request state 7 during this tick. Complete that
         * request before the scheduler presents, rather than spending a
         * whole tick in the already-finished outgoing scene. */
        if(failed==fallbacks && old>=1 && old<=6 && old!=3 && next==7 &&
           r16(t+0x4E)==0) {
            guest(cpu,0x8001AC00u,0x8001AD0Cu,0,0,0);
            old=7; sub=0; next=r16(t+0x4C);
        }
        /* States 1/2/4/5/6 have a one-shot scene initializer followed by
         * their ordinary tick/draw state. State 3 is a menu, not this path. */
        if(failed==fallbacks && r8(0x1F8001CEu) && (old==7 || old==0) &&
           next>=1 && next<=6 && next!=3 && r16(t+0x4E)==0) {
            guest(cpu,0x8001AC00u,0x8001AD0Cu,0,0,0);
            old=next; sub=0;
        }
        if(failed==fallbacks && old>=1 && old<=6 && old!=3 && sub==0 &&
           r16(t+0x4C)==old && r16(t+0x4E)==1)
            guest(cpu,0x8001AC00u,0x8001AD0Cu,0,0,0);
        if(start_batches!=batches) {
            fprintf(stdout,"seamless: scene frames=%u..%u ms=%.3f cycles=%llu area=%u/%u phase=%u/%u fallbacks=%u\n",
                    start_frame,frame,tomba_seamless_now_ms()-started,(unsigned long long)(psx_get_cycle_count()-start_cycles),r16(0x8009BCC8u),r16(0x8009BCCAu),
                    r16(t+0x4C),r16(t+0x4E),fallbacks);
            fflush(stdout);
        }
        return 1;
    }
    if(phys==0x1B0A4u && cpu->gpr[31]!=0x8001B2A4u && !r8(0x1F8001B4u)) {
        uint32_t t=r32(0x1F8001D4u);
        if(r16(t+0x4E)<=3) {
            for(unsigned step=0;step<4 && r16(t+0x4E)<=3;step++) {
                unsigned old=r16(t+0x4E), failed=fallbacks;
                guest(cpu,0x8001B0A4u,0x8001B2A4u,0,0,0);
                if(failed!=fallbacks || r16(t+0x4E)==old) break;
            }
            return 1;
        }
    }
    if(phys==0x1CFCCu && cpu->gpr[31]!=0x8001D28Cu) {
        uint32_t t=r32(0x1F8001D4u);
        for(unsigned step=0;step<4 && r16(t+0x4E)<4;step++) {
            unsigned old=r16(t+0x4E), failed=fallbacks;
            guest(cpu,0x8001CFCCu,0x8001D28Cu,0,0,0);
            if(failed!=fallbacks || r16(t+0x4E)==old) break;
        }
        /* Once the queue completed, the parent's 1DC/1DE handoff runs. */
        if(!r8(0x1F8001CEu)) guest(cpu,0x8001CFCCu,0x8001D28Cu,0,0,0);
        return 1;
    }
    if(trace && (phys==0x1758Cu || phys==0x17AE0u || phys==0x243E8u || phys==0x246B0u ||
       phys==0x28EF4u || phys==0x59F7Cu || phys==0x2065Cu ||
       phys==0x1CFCCu || phys==0x1CE80u || phys==0x1CA84u || phys==0x222B8u ||
       phys==0x1DE24u || phys==0x21C24u || phys==0x21CC8u)) {
        uint32_t thread=r32(0x1F8001D4u);
        fprintf(stdout,"seamless: call frame=%u pc=%05X ra=%08X args=%X,%X,%X thread=%08X phase=%u/%u ui=%u/%u\n",
            frame,phys,cpu->gpr[31],cpu->gpr[4],cpu->gpr[5],cpu->gpr[6],thread,
            r16(thread+0x48),r16(thread+0x4E),r8(0x8009BCCFu),r8(0x8009BCE9u));
        fflush(stdout);
    }
    if(phys==0x17154u && cpu->gpr[4]==2 && cpu->gpr[5]==0x80021340u &&
       psx_mod_game_started() && r32(0x80021340u)==0x27BDFF98u && install_batch(cpu)) return 1;
    return previous_hook ? previous_hook(cpu,phys) : 0;
}
static void tick(void) {
    ++frame;
    if(pack && g_psx_bios_hle_hook!=dispatch) {
        previous_hook=g_psx_bios_hle_hook;
        g_psx_bios_hle_hook=dispatch;
    }
}
static int load_pack(const char *path) {
    FILE *f=fopen(path,"rb");
    if(!f) return 0;
    fseek(f,0,SEEK_END); long size=ftell(f); rewind(f);
    if(size<48 || size>256*1024*1024) { fclose(f); return 0; }
    unsigned char *p=(unsigned char*)malloc((size_t)size);
    if(!p) { fclose(f); return 0; }
    int ok=fread(p,1,(size_t)size,f)==(size_t)size; fclose(f);
    static const unsigned char sha1[20]={0xc2,0x59,0xec,0x7f,0xf6,0xef,0x41,0x63,0x91,0x39,0x91,0xf4,0xe4,0xdb,0x2e,0xff,0x71,0x70,0x28,0x18};
    asset_count=u32(p+8); data_len=u32(p+12);
    if(!ok || memcmp(p,"TMBPK001",8) || memcmp(p+16,sha1,20) || asset_count!=1062 ||
       48ull+asset_count*32ull+data_len!=(uint64_t)size) { free(p); return 0; }
    uint32_t hash=2166136261u;
    for(long i=48;i<size;i++) hash=(hash^p[i])*16777619u;
    if(hash!=u32(p+36)) { free(p); return 0; }
    assets=(Asset*)(p+48); data=p+48+asset_count*32;
    for(unsigned i=0;i<asset_count;i++) {
        const Asset *a=assets+i;
        if(a->raw>data_len || a->raw_len>data_len-a->raw || a->decoded>data_len ||
           a->decoded_len>data_len-a->decoded || a->size>a->raw_len ||
           a->raw_len!=((a->size+2047u)&~2047u)) { free(p); assets=NULL; data=NULL; return 0; }
    }
    pack=p;
    fprintf(stdout,"seamless: resident assets=%u bytes=%u; native loader hook enabled\n",asset_count,data_len);
    return 1;
}
static void activate(void) {
    const char *trace_env=getenv("TOMBA_SEAMLESS_TRACE");
    trace=trace_env && !strcmp(trace_env,"1");
    const char *retail_env=getenv("TOMBA_SEAMLESS_REVERB_RETAIL");
    retail_reverb=retail_env && !strcmp(retail_env,"1");
    for(int attempt=0;attempt<2;attempt++) {
        const char *path=tomba_seamless_prepare_path(attempt);
        if(!path || !*path) break;
        if(load_pack(path)) return;
        const char *explicit_path=getenv("TOMBA_SEAMLESS_PACK");
        if(explicit_path && *explicit_path) break;
        if(!attempt) fprintf(stderr,"seamless: invalid cache; rebuilding from your disc\n");
    }
    fprintf(stderr,"seamless: asset pack unavailable; resident loading disabled\n");
}
PSX_MOD_CONSTRUCTOR(tomba_register_seamless) {
    (void)psx_mod_register_activation_plugin("tomba.seamless",activate);
    (void)psx_mod_register_vblank_plugin("tomba.seamless",tick);
}
