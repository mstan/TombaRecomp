"""Reconstruct upstream+patches, rebuild Japan host, re-audit reused AOT."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'eu'))
from toolchain import executable

def main():
 p=argparse.ArgumentParser();p.add_argument('--handoff',type=Path,required=True);p.add_argument('--name',required=True);p.add_argument('--enhancements',action='store_true');a=p.parse_args()
 assert Path(a.name).name==a.name
 subprocess.run([sys.executable,'-I','-B','europe/tests/rebuild.py','--handoff',str(a.handoff.resolve()),'--name',a.name,'--check-only'],cwd=ROOT,check=True)
 out=ROOT/'build-europe'/a.name;tree=out/'source'
 def run(label,cmd,cwd=tree):
  print(label,flush=True)
  with (out/(label+'.log')).open('w') as log:subprocess.run(list(map(str,cmd)),cwd=cwd,stdout=log,stderr=subprocess.STDOUT,check=True)
 cmake=executable('cmake.exe');mapping='-ffile-prefix-map='+tree.as_posix()+'=. -fmacro-prefix-map='+tree.as_posix()+'=.'
 run('configure-compiler',[cmake,'-S','psxrecomp/recompiler','-B','build-eu-tools','-G','Ninja','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_C_COMPILER='+executable('clang.exe'),'-DCMAKE_CXX_COMPILER='+executable('clang++.exe'),'-DCMAKE_MAKE_PROGRAM='+executable('ninja.exe'),'-DCMAKE_C_FLAGS='+mapping,'-DCMAKE_CXX_FLAGS='+mapping])
 run('build-compiler',[cmake,'--build','build-eu-tools','--target','psxrecomp-game','psxrecomp-bios','-j','3'])
 run('codegen-hash',[cmake,'-DOUT='+str(tree/'psxrecomp/runtime/include/overlay_codegen_hash.h'),'-DPSXRECOMP_CODEGEN_HASH_ROOT='+str(tree/'psxrecomp'),'-P',tree/'psxrecomp/runtime/hash_codegen.cmake'])
 run('build-japan',[sys.executable,'-I','-B','jp/build.py','--player','--disc',ROOT/'disc/jp/disc.cue','--webp-source',ROOT/'build-eu2/native/_deps/psx_libwebp-src']+(['--enhancements'] if a.enhancements else []))
 scope='rc2' if a.enhancements else 'full'
 work=tree/('build-jp/'+scope+'/aot');work.mkdir(parents=True,exist_ok=True)
 cache=work/'verified-input-cache';shutil.copytree(ROOT/('build-jp/'+scope+'/qa/native/cache'),cache)
 # Reuse translation artifacts only after fresh source extraction and both
 # subset and final audits by the newly rebuilt compiler/framework.
 run('audit-japan-aot',[sys.executable,'-I','-B','jp/build_aot.py','--all-areas','--flavor','2','--work-dir',work,'--reuse-cache',cache,'--destination','build-jp/'+scope+'/player/native']+(['--config','jp/pc.toml'] if a.enhancements else []))
 receipt=json.loads((work/'audit.json').read_text());assert receipt['published_pairs']==24
 (out/'JAPAN_REBUILD_RESULT.json').write_text(json.dumps(dict(result='passed',exact_upstream_plus_patches=True,recompiler_rebuilt=True,japan_boot_regenerated=True,japan_player_rebuilt=True,japan_native_pairs_reaudited=24,eu_backends_rebuilt_this_run=False,usa_backend_rebuilt_this_run=False),indent=2)+'\n')
 print('PASS isolated Japanese source rebuild and native-cache re-audit',flush=True)
if __name__=='__main__':main()
