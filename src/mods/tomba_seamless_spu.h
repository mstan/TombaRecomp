#ifndef TOMBA_SEAMLESS_SPU_H
#define TOMBA_SEAMLESS_SPU_H
/* The caller validates the reverb allocation and transfer mode. This exact
 * transfer body is also compiled by the original-MIPS comparison fixture.
 * r32/w16/w32 and the SPU services belong to the including translation unit. */
static void tomba_reverb_transfer(uint32_t begin) {
    for(uint32_t dest=begin;dest<0x80000u;dest+=1024) {
        uint32_t count=0x80000u-dest;
        if(count>1024) count=1024;
        /* PsyQ rounds the final transfer to 64 bytes, even for reverb
         * modes whose start is only 8-byte aligned. The SPU wraps at 512K. */
        count=(count+63u)&~63u;
        w16(0x80097C60u,(uint16_t)(dest>>3));
        w32(0x80097C98u,0); w32(0x80097C9Cu,0x80097840u); w32(0x80097CA0u,count/64);
        spu_write(0x1F801DA6u,dest>>3);
        uint16_t ctrl=spu_ctrl_read();
        spu_write(0x1F801DAAu,(ctrl&~0x30u)|0x20u);
        for(uint32_t j=0;j<count;j+=4) spu_dma_write(r32(0x80097840u+j));
        spu_write(0x1F801DAAu,ctrl&~0x30u);
    }
}
#endif
