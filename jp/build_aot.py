"""Japan native overlays through the existing guarded AOT pipeline."""
import argparse,hashlib,json,os,shutil,struct,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'eu'),str(ROOT/'psxrecomp/tools')]
from toolchain import executable
import aot_overlay_pipeline as pipeline
BASE=0x800E9AF8

def main():
 p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=2);p.add_argument('--destination',type=Path,default=ROOT/'build-jp/full/qa/native');p.add_argument('--prepare-only',action='store_true');p.add_argument('--all-areas',action='store_true');p.add_argument('--reuse-cache',type=Path);p.add_argument('--flavor',type=int,choices=[0,2],default=2);p.add_argument('--work-dir',type=Path);p.add_argument('--config',type=Path,default=ROOT/'jp/game.toml');a=p.parse_args()
 work=(a.work_dir or ROOT/'build-jp/full/aot').resolve();assert work.is_relative_to(ROOT);work.mkdir(parents=True,exist_ok=True);tmp=work/'temp';tmp.mkdir(exist_ok=True);os.environ['TEMP']=os.environ['TMP']=str(tmp);tempfile.tempdir=str(tmp)
 disc=pipeline.Disc(ROOT/'disc/jp/disc.cue')
 profile=dict(schema='psxrecomp AOT methods v1',game_id='SLPS-01144',disc_hashes={'sha256':'fb5b8ea9e3bd328e88a6b8b8ecb0b493d0dda5a9b5f732a7a6e4c9b146d9cd2b'},strict_bounds=True,bios_resident=False,images=[],checks=[])
 pipeline.check_disc(profile,disc,ROOT/'disc/jp/disc.cue')
 boot=disc.read('SLPS_011.44');assert hashlib.sha1(boot).hexdigest()=='07d577698ad31ec1a69b9d7b80a7c3f90b650888'
 # Exact original type-F0 destination materialization, also confirmed by the
 # byte-matched Japan decompilation profiles. Never reuse a US/EU address.
 pc=0x8002025C;values={hex(pc):'0x3c06800f',hex(pc+4):'0x24c69af8'}
 for address,value in values.items():assert struct.unpack_from('<I',boot,int(address,16)-0x80010000+2048)[0]==int(value,16)
 profile['checks']=[dict(method='words',file='SLPS_011.44',base='0x80010000',file_offset=2048,values=values)]
 # The original overlay class is loaded at BASE; original data and code are
 # guarded against their full source bytes by the shared pipeline.
 names=['SYSTEM/'+n+'.BIN' for n in ['DSPSUB','DSPSUB2','DSPSUB3','INFO','INFO2','INFO3','OPTSUB00']]
 names += [f'SYSTEM/X{i:02d}.BIN' for i in ([0,1,2,3,4,5,6,8,9,10,11,13,14,16,17,18,19] if a.all_areas else [0,1])]
 contracts=json.loads((ROOT/'jp/overlay-contracts.json').read_text())['images']
 for name in names:
  spec=dict(method='fixed_address_files',files=[name],load_addr=hex(BASE),allow_missing=True)
  if name in contracts:
   contract=contracts[name];assert hashlib.sha256(disc.read(name)).hexdigest()==contract['sha256']
   spec['excluded_ranges']=contract['excluded_ranges']
  profile['images'].append(spec)
 profile['expected_records']=len(names);(work/'profile.json').write_text(json.dumps(profile,indent=2)+'\n')
 inventory=pipeline.prepare(profile,disc,[],work)
 if a.prepare_only:return
 compiler=ROOT/'build-eu-tools/psxrecomp-game.exe';attempt=Path(tempfile.mkdtemp(prefix='native-',dir=work));print(attempt,flush=True)
 if a.reuse_cache:
  reuse=a.reuse_cache.resolve();assert reuse.is_relative_to(work)
  stems={f.stem for f in reuse.rglob('*.dll')}
  completed=[job for job in inventory['jobs'] if job['pair_stem'] in stems]
  subset=attempt/'reuse-inventory.json';subset.write_text(json.dumps(dict(inventory,jobs=completed)))
  pipeline.audit(a.config.resolve(),compiler,reuse,subset,attempt/'reuse-audit.json',flavor=a.flavor)
  remaining=dict(inventory,jobs=[job for job in inventory['jobs'] if job not in completed])
  if remaining['jobs']:cache=pipeline.build(remaining,a.config.resolve(),compiler,attempt,executable('clang.exe'),a.workers,ROOT,flavor=a.flavor)
  else:cache=attempt/'cache'
  shutil.copytree(reuse,cache,dirs_exist_ok=True)
 else:cache=pipeline.build(inventory,a.config.resolve(),compiler,attempt,executable('clang.exe'),a.workers,ROOT,flavor=a.flavor)
 receipt=pipeline.audit(a.config.resolve(),compiler,cache,work/'runtime-input-inventory.json',attempt/'audit.json',flavor=a.flavor)
 destination=a.destination.resolve();assert destination.is_relative_to(ROOT)
 pipeline.stage(cache,destination,receipt);(work/'audit.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print('PASS Japan native pairs',receipt['published_pairs'],flush=True)
if __name__=='__main__':main()
