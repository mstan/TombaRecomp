"""Build one Japan backend against the existing framework and launcher."""
import argparse,os,subprocess,sys,tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'eu'))
from toolchain import executable

def main():
 p=argparse.ArgumentParser();p.add_argument('--disc',type=Path,required=True);p.add_argument('--player',action='store_true');p.add_argument('--jobs',type=int,default=4);p.add_argument('--build-dir',type=Path);p.add_argument('--enhancements',action='store_true');p.add_argument('--webp-source',type=Path,default=ROOT/'build-eu2/native/_deps/psx_libwebp-src');a=p.parse_args()
 profile=ROOT/('jp/pc.toml' if a.enhancements else 'jp/game.toml')
 generated=(profile.parent/tomllib.loads(profile.read_text())['recompiler']['out_dir']).resolve()
 build=(a.build_dir or ROOT/'build-jp'/('rc2' if a.enhancements else 'full')/('player' if a.player else 'qa')/'native').resolve();assert build.is_relative_to(ROOT);build.parent.mkdir(parents=True,exist_ok=True)
 env=dict(os.environ)
 for key in ['TEMP','TMP']:
  folder=build.parent/key;folder.mkdir(exist_ok=True);env[key]=str(folder)
 mapping='-ffile-prefix-map='+ROOT.as_posix()+'=. -fmacro-prefix-map='+ROOT.as_posix()+'=.'
 cmake=executable('cmake.exe')
 commands=[('prepare',[sys.executable,'-I','-B','jp/prepare.py','--disc',str(a.disc.resolve())]),
  ('generate',[str(ROOT/'build-eu-tools/psxrecomp-game.exe'),'--config',str(profile)]),
  ('configure',[cmake,'-S','jp','-B',str(build),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release',
   '-DCMAKE_C_COMPILER='+executable('clang.exe'),'-DCMAKE_CXX_COMPILER='+executable('clang++.exe'),'-DCMAKE_MAKE_PROGRAM='+executable('ninja.exe'),
   '-DCMAKE_C_COMPILER_LAUNCHER=','-DCMAKE_CXX_COMPILER_LAUNCHER=','-DCMAKE_C_FLAGS='+mapping,'-DCMAKE_CXX_FLAGS='+mapping,
   '-DPSX_DEBUG_TOOLS='+('OFF' if a.player else 'ON'),'-DPSX_PGXP_VARIANT=OFF','-DPSXRECOMP_BIOS_STEMS=OpenBIOS','-DBUILD_TESTING=OFF',
   '-DTOMBA_JP_ENHANCEMENTS='+('ON' if a.enhancements else 'OFF'),'-DTOMBA_JP_GENERATED_DIR='+str(generated),
   '-DPython3_EXECUTABLE='+sys.executable,'-DFETCHCONTENT_SOURCE_DIR_PSX_LIBWEBP='+str(a.webp_source.resolve())]),
  ('build',[cmake,'--build',str(build),'--target','tomba-jp','--parallel',str(a.jobs)])]
 for label,cmd in commands:
  print(label,flush=True)
  with (build.parent/(label+'.log')).open('w') as log:subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 print(build/'TombaRecompJP.exe',flush=True)
if __name__=='__main__':main()
