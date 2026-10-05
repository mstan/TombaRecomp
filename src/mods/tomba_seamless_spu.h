#ifndef TOMBA_SEAMLESS_SPU_H
#define TOMBA_SEAMLESS_SPU_H
/* The caller validates the reverb allocation and transfer mode. This exact
 * transfer body is also compiled by the original-MIPS comparison fixture.
 * w16/w32 and psx_mod_spu_upload belong to the including translation unit
 * (the framework service in the runtime, a hardware-boundary model in the
 * fixture). */
static void tomba_reverb_transfer(uint32_t begin) {
    for(uint32_t dest=begin;dest<0x80000u;dest+=1024) {
        uint32_t count=0x80000u-dest;
        if(count>1024) count=1024;
        /* PsyQ rounds the final transfer to 64 bytes, even for reverb
         * modes whose start is only 8-byte aligned. The SPU wraps at 512K. */
        count=(count+63u)&~63u;
        w16(0x80097C60u,(uint16_t)(dest>>3));
        w32(0x80097C98u,0); w32(0x80097C9Cu,0x80097840u); w32(0x80097CA0u,count/64);
        (void)psx_mod_spu_upload(dest,0x80097840u,count,1);
    }
}
#endif
