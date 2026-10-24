"""Read-only discovery of regional equivalents of the official EU1 hooks.

Candidate discovery is not a runtime authorization. Full raw windows, changed
instructions and ambiguity are recorded for review before any hook is enabled.
"""
import argparse, difflib, hashlib, importlib.util, json, struct
from pathlib import Path

BASE=0x80010000
def words(data): return struct.unpack('<%dI'%(len(data)//4),data[:len(data)//4*4])
def mask(w):
    op=w>>26
    if op in (2,3): return w&0xfc000000
    if op in (1,4,5,6,7,8,9,10,11,12,13,14,15,32,33,34,35,36,37,38,40,41,42,43,46,50,58): return w&0xffff0000
    return w

def main():
    p=argparse.ArgumentParser();p.add_argument('--reference-root',type=Path,required=True);a=p.parse_args()
    root=a.reference_root.resolve()
    spec=importlib.util.spec_from_file_location('official_ws',root/'eu/widescreen_profile.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    reference=(root/'disc/EXE/MAIN0.EXE').read_bytes()[2048:];rw=words(reference)
    sites=sorted(set(m.CODE.values())|set(m.FIELDS.values())|set(m.TABLES.values())|{0x8004f624,0x8004f628})
    targets={'eu2-en':root/'disc/eu2/EXE/MAIN0.EXE','eu2-es':root/'disc/eu2/EXE/MAIN5.EXE',
      'eu2-pt':root/'disc/eu2/EXE/MAIN6.EXE','eu2-sv':root/'disc/eu2/EXE/MAIN7.EXE',
      'eu2-da':root/'disc/eu2/EXE/MAIN8.EXE','jp':root/'disc/jp/SLPS_011.44'}
    report={}
    for name,path in targets.items():
        raw=path.read_bytes();body=raw[2048:];tw=words(body);normalized=[mask(w) for w in tw]
        index={}
        for i in range(len(tw)-8):index.setdefault(tuple(normalized[i:i+8]),[]).append(i)
        rows=[]
        for pc in sites:
            ri=(pc-BASE)//4;found=[];used=0
            for radius in (16,8,4,2):
                lo=ri-radius;hi=ri+radius;key=tuple(mask(w) for w in rw[lo:lo+8])
                candidates=[i+radius for i in index.get(key,[]) if i+2*radius<=len(tw) and normalized[i:i+2*radius]==[mask(w) for w in rw[lo:hi]]]
                if len(candidates)==1:found=candidates;used=radius;break
            row={'eu1':hex(pc),'candidates':[hex(BASE+i*4) for i in found],'window_bytes':used*8}
            if found:
                ti=found[0];b=body[(ti-used)*4:(ti+used)*4]
                row.update(address=hex(BASE+ti*4),sha256=hashlib.sha256(b).hexdigest(),
                  changes=[{'relative':(i-used)*4,'eu1':hex(x),'target':hex(y)} for i,(x,y) in enumerate(zip(rw[ri-used:ri+used],tw[ti-used:ti+used])) if x!=y])
            rows.append(row)
        if name.startswith('eu2-'):
            # Resolve repetitive call sites by their enclosing independently
            # matched boundaries, never by a whole-region address delta.
            for row in rows:
                if 'address' in row:continue
                pc=int(row['eu1'],16)
                left=max((r for r in rows if 'address' in r and int(r['eu1'],16)<pc),key=lambda r:int(r['eu1'],16))
                right=min((r for r in rows if 'address' in r and int(r['eu1'],16)>pc),key=lambda r:int(r['eu1'],16))
                lo=int(left['eu1'],16);hi=int(right['eu1'],16)
                delta=int(left['address'],16)-lo
                if int(right['address'],16)-hi!=delta:continue
                if [mask(w) for w in rw[(lo-BASE)//4:(hi-BASE)//4]]!=normalized[(lo+delta-BASE)//4:(hi+delta-BASE)//4]:continue
                target=pc+delta;at=target-BASE
                row.update(address=hex(target),sha256=hashlib.sha256(body[at-32:at+32]).hexdigest(),window_bytes=64,
                    anchored_interval=[hex(lo),hex(hi)],changes=[{'relative':d,'eu1':hex(struct.unpack_from('<I',reference,pc-BASE+d)[0]),'target':hex(struct.unpack_from('<I',body,at+d)[0])} for d in range(-32,32,4) if reference[pc-BASE+d:pc-BASE+d+4]!=body[at+d:at+d+4]])
        if name=='jp':
            for row in rows:
                if 'address' in row:continue
                pc=int(row['eu1'],16)
                left=max((r for r in rows if 'address' in r and int(r['eu1'],16)<pc),key=lambda r:int(r['eu1'],16))
                right=min((r for r in rows if 'address' in r and int(r['eu1'],16)>pc),key=lambda r:int(r['eu1'],16))
                lo=int(left['eu1'],16);hi=int(right['eu1'],16);tl=int(left['address'],16);th=int(right['address'],16)
                if not 0<hi-lo<0x4000 or not 0<th-tl<0x4000:continue
                seq=difflib.SequenceMatcher(None,[mask(w) for w in rw[(lo-BASE)//4:(hi-BASE)//4]],normalized[(tl-BASE)//4:(th-BASE)//4],autojunk=False)
                index=(pc-lo)//4
                for block in seq.get_matching_blocks():
                    if block.a<=index<block.a+block.size:
                        row['aligned_candidate']=hex(tl+(block.b+index-block.a)*4)
                        row['aligned_block_words']=block.size
                        row['alignment_boundaries']=[hex(lo),hex(hi),hex(tl),hex(th)]
                        break
        report[name]={'exe_sha256':hashlib.sha256(raw).hexdigest(),'rows':rows}
        print(name,'unique',sum('address' in r for r in rows),'/',len(rows),'missing',[r['eu1'] for r in rows if 'address' not in r],flush=True)
    out=Path(__file__).resolve().parents[1]/'build-widescreen';out.mkdir(exist_ok=True)
    (out/'discovery.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
