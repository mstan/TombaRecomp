/* Synthetic bank data, exercising the same planner as the runtime. */
#include "seamless_request_fixture.c"

static uint8_t test_ram[0x200000], test_scratch[1024], test_bank[2048];
static void put32(uint8_t *p,uint32_t value) {
    p[0]=(uint8_t)value; p[1]=(uint8_t)(value>>8);
    p[2]=(uint8_t)(value>>16); p[3]=(uint8_t)(value>>24);
}
static int check_bank(unsigned bank,int expected) {
    test_ram[0x98000+14]=(uint8_t)bank;
    test_ram[0x98000+15]=(uint8_t)(bank>>8);
    int actual=seamless_fixture_plan(test_ram,test_scratch,0);
    if(actual!=expected) {
        fprintf(stderr,"sound bank %u: expected %d, got %d\n",bank,expected,actual);
        return 1;
    }
    return 0;
}
int main(void) {
    Asset asset={0};
    asset.size=asset.raw_len=sizeof test_bank;
    assets=&asset; asset_count=1; data=test_bank;
    /* One header and one eight-byte sample, with room for DMA rounding. */
    put32(test_bank,0x100); put32(test_bank+4,0x40);
    put32(test_bank+0x40,8); put32(test_bank+0x44,40);
    put32(test_bank+0x100,8); put32(test_bank+0x104,16);
    test_ram[0x791a1]=2; /* BCD 00:02:00 = LBA 0. */
    put32(test_ram+0x791a4,sizeof test_bank);
    put32(test_ram+0x9e748,0x80098000);
    put32(test_ram+0x9e74c,0x80100000);
    test_ram[0x98003]=0x93;
    put32(test_ram+0x98010,2);
    put32(test_ram+0x97c70,3);
    for(unsigned i=0;i<75;i++) put32(test_ram+0x77d50+8*i,0x48250);
    int failures=0;
    for(unsigned i=0;i<75;i++) failures+=check_bank(i,1);
    failures+=check_bank(75,0);
    failures+=check_bank(0xffff,0);
    put32(test_ram+0x97c64,0x80010000);
    failures+=check_bank(16,0);
    put32(test_ram+0x97c64,0);
    put32(test_ram+0x77d50+16*8,0x80000);
    failures+=check_bank(16,0);
    if(!failures) puts("PASS: all 75 sound-bank indices and invalid-request guards");
    return failures ? 1 : 0;
}
