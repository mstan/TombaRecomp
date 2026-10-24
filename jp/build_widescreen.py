"""Private Japanese shared-renderer experiment; never prepare/write a disc."""
import argparse,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'eu'))
from toolchain import executable
def main():
 p=argparse.ArgumentParser();p.add_argument('--player',action='store_true');p.add_argument('--webp-source',type=Path);a=p.parse_args()
 build=ROOT/'build-jp/widescreen'/('player' if a.player else 'qa')/'native';build.mkdir(parents=True,exist_ok=True)
 env=dict(os.environ)
 for k in ('TEMP','TMP'):
  path=build.parent/'temp';path.mkdir(exist_ok=True);env[k]=str(path)
 mapping='-ffile-prefix-map='+ROOT.as_posix()+'=. -fmacro-prefix-map='+ROOT.as_posix()+'=.'
 commands=[('generate',[str(ROOT/'build-eu-tools/psxrecomp-game.exe'),'--config','jp/widescreen.toml']),
 ('configure',[executable('cmake.exe'),'-S','jp','-B',str(build),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release',
 '-DTOMBA_JP_ENHANCEMENTS=ON','-DTOMBA_JP_WIDESCREEN=ON','-DTOMBA_JP_GENERATED_DIR='+str(ROOT/'build-jp/widescreen/generated/boot'),
 '-DPSX_DEBUG_TOOLS='+('OFF' if a.player else 'ON'),'-DPSX_PGXP_VARIANT=OFF','-DPSXRECOMP_BIOS_STEMS=OpenBIOS','-DBUILD_TESTING=OFF',
 '-DPython3_EXECUTABLE='+sys.executable,'-DCMAKE_C_COMPILER='+executable('clang.exe'),'-DCMAKE_CXX_COMPILER='+executable('clang++.exe'),'-DCMAKE_MAKE_PROGRAM='+executable('ninja.exe'),
 '-DCMAKE_C_COMPILER_LAUNCHER=','-DCMAKE_CXX_COMPILER_LAUNCHER=','-DCMAKE_C_FLAGS='+mapping,'-DCMAKE_CXX_FLAGS='+mapping,
 *(['-DFETCHCONTENT_SOURCE_DIR_PSX_LIBWEBP='+str(a.webp_source.resolve())] if a.webp_source else [])]),
 ('build',[executable('cmake.exe'),'--build',str(build),'--target','tomba-jp','-j','3'])]
 for label,command in commands:
  print(label,flush=True)
  with (build.parent/(label+'.log')).open('w') as log:subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 print('PASS Japan widescreen experimental build',flush=True)
if __name__=='__main__':main()
