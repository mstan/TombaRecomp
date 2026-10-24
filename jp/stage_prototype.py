"""Add Japan to a NEW verified RC2 package copy. Existing EU files stay intact."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'eu'),str(ROOT/'psxrecomp/tools')]
from toolchain import executable
import aot_overlay_pipeline as pipeline

def main():
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--output',default='dist/TombaRecomp-EU-Japan-Prototype');a=p.parse_args();base=a.base.resolve();out=(ROOT/a.output).resolve()
 assert out.is_relative_to(ROOT) and not out.exists()
 manifest=json.loads((base/'PACKAGE_AUDIT.json').read_text())['files_sha256']
 actual={f.relative_to(base).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in base.rglob('*') if f.is_file() and f!=base/'PACKAGE_AUDIT.json'}
 assert actual==manifest,'Base must be an untouched clean RC2 package'
 shutil.copytree(base,out);target=out/'backends/SLPS-01144';target.mkdir()
 build=ROOT/'build-jp/player/native';assert 'PSX_DEBUG_TOOLS:BOOL=OFF' in (build/'CMakeCache.txt').read_text()
 shutil.copy2(build/'TombaRecompJP.exe',target/'TombaRecompJP.exe')
 for folder in ['assets','bios']:shutil.copytree(build/folder,target/folder)
 shutil.copytree(base/'overlay_toolchain',target/'overlay_toolchain')
 shutil.copytree(ROOT/'jp/seeds',target/'seeds')
 config=(ROOT/'jp/game.toml').read_text();config=config.replace('exe = "../disc/jp/SLPS_011.44"','exe = "user-data/SLPS_011.44"').replace('disc = "../disc/jp/disc.cue"\n','').replace('out_dir = "../build-jp/generated"','out_dir = "cache/generated"')
 (target/'game.toml').write_text(config)
 receipt=json.loads((ROOT/'build-jp/aot/audit.json').read_text())
 pipeline.stage(ROOT/'build-jp/qa/native/cache',target,receipt)
 # Strip debug paths only on NEW copied Japan files; never alter EU binaries.
 for f in [target/'TombaRecompJP.exe',*target.glob('cache/**/*.dll')]:subprocess.run([executable('llvm-strip.exe'),'--strip-debug',str(f)],check=True)
 (target/'AOT_CACHE_AUDIT.json').write_text(json.dumps({k:receipt[k] for k in ['game_id','cache_tag','published_pairs','manifest_rows','all_pairs_valid','all_guards_match_known_input_bytes','full_static_coverage_proven']},indent=2)+'\n')
 catalog='\n[[profile]]\nid = "SLPS-01144"\nsize = 289430064\nsha256 = "fb5b8ea9e3bd328e88a6b8b8ecb0b493d0dda5a9b5f732a7a6e4c9b146d9cd2b"\nbackend = "backends/SLPS-01144/TombaRecompJP.exe"\n'
 with (out/'regional-launch.toml').open('a') as f:f.write(catalog)
 shutil.copy2(ROOT/'jp/TESTANLEITUNG_DE.md',out/'JAPAN_TEST_DE.md')
 if (ROOT/'jp/TEST_REPORT.json').is_file():shutil.copy2(ROOT/'jp/TEST_REPORT.json',out/'JAPAN_TEST_REPORT.json')
 (out/'Start-TombaRecomp.cmd').write_text('@echo off\r\ncd /d "%~dp0"\r\nstart "" "%~dp0TombiRecompEU.exe"\r\n',encoding='ascii')
 for name,digest in manifest.items():
  if name!='regional-launch.toml':assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest,name
 subprocess.run([sys.executable,'-I','-B',str(ROOT/'europe/audit.py'),'--path',str(out),'--kind','prototype','--output',str(out/'PACKAGE_AUDIT.json')],check=True)
 print(out,flush=True)
if __name__=='__main__':main()
