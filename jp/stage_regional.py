"""Stage four backends using the existing common launcher, never user installs."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'eu'),str(ROOT/'psxrecomp/tools')]
from toolchain import executable
import aot_overlay_pipeline as pipeline

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',default='dist/TombaRecomp-Regional-Japan-RC1');p.add_argument('--enhancements',action='store_true');a=p.parse_args()
 out=(ROOT/a.output).resolve();assert out.is_relative_to(ROOT) and not out.exists()
 base=ROOT/'dist/TombiRecomp-Europe-Windows-x64-RC2'
 manifest=json.loads((base/'PACKAGE_AUDIT.json').read_text())['files_sha256']
 assert {f.relative_to(base).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in base.rglob('*') if f.is_file() and f!=base/'PACKAGE_AUDIT.json'}==manifest
 shutil.copytree(base,out)
 profiles=[]
 for region,filename,build,config,receipt_path,cache,seeds in [
  ('SLPS-01144','TombaRecompJP.exe',ROOT/('build-jp/rc2/player/native' if a.enhancements else 'build-jp/full/player/native'),ROOT/('jp/pc.toml' if a.enhancements else 'jp/game.toml'),ROOT/('build-jp/rc2/aot/audit.json' if a.enhancements else 'build-jp/full/aot-pgxp/audit.json'),ROOT/('build-jp/rc2/qa/native/cache' if a.enhancements else 'build-jp/full/qa/native/cache'),ROOT/'jp/seeds'),
  ('SCUS-94236','Tomba__Recompiled.exe',ROOT/'build-regional/us-player/native',ROOT/'packaging/release/game.toml',ROOT/'build-regional/us-audit-full/audit.json',ROOT/'build-regional/us-cache-copy',ROOT/'seeds')]:
  assert 'PSX_DEBUG_TOOLS:BOOL=OFF' in (build/'CMakeCache.txt').read_text()
  target=out/'backends'/region;target.mkdir();shutil.copy2(build/filename,target/filename)
  for folder in ['assets','bios','mods']:shutil.copytree(build/folder,target/folder)
  if region=='SLPS-01144':
   # A staged build may retain an old experimental manifest after CMake
   # regeneration. Never offer the unverified Japanese hybrid path.
   candidate=target/'mods/bundled/tomba.enhancement.hybrid-controller'
   if candidate.exists():shutil.rmtree(candidate)
  for personal in ['state.toml','settings.toml']:assert not (target/'mods'/personal).exists()
  shutil.copytree(base/'overlay_toolchain',target/'overlay_toolchain');(target/'seeds').mkdir()
  for name in (['boot.txt'] if region=='SLPS-01144' else ['ghidra_funcs.txt','tomba_bios_thunks.txt']):
   # Seed comments are developer provenance, sometimes with old local paths.
   # Only the actual parser input belongs in the portable runtime package.
   lines=(seeds/name).read_text().splitlines()
   (target/'seeds'/name).write_text('\n'.join(line for line in lines if not line.lstrip().startswith('#'))+'\n')
  text=config.read_text()
  if region=='SLPS-01144':
   text=text.replace('exe = "../disc/jp/SLPS_011.44"','exe = "user-data/SLPS_011.44"').replace('disc = "../disc/jp/disc.cue"\n','').replace('out_dir = "../build-jp/generated"','out_dir = "cache/generated"').replace('Japan Prototype','Japan').replace('SLPS-01144 Prototype','SLPS-01144')
   text=text.replace('out_dir = "../build-jp/rc2/generated/boot"','out_dir = "cache/generated"')
   size=289430064;digest='fb5b8ea9e3bd328e88a6b8b8ecb0b493d0dda5a9b5f732a7a6e4c9b146d9cd2b';pairs=24
  else:
   text=text.replace('memcard_dir = "saves"','memcard_dir = "saves/SCUS-94236"').replace('disc = "tomba/tomba.cue"\n','')
   text+='\n[prepare_disc]\nboot_exe = "SCUS_942.36"\nknown_sizes = [280193760]\nknown_md5 = ["c80636a28de4abcfa34f9e57fb3b043d"]\nknown_sha1 = ["c259ec7ff6ef4163913991f4e4db2eff71702818"]\n'
   inventory=json.loads((ROOT/'build-regional/us-audit-full/runtime-input-inventory.json').read_text());digest=inventory['original_disc_sha256'];size=(ROOT/'disc/Tomba! (USA).bin').stat().st_size;pairs=176
  (target/'game.toml').write_text(text)
  receipt=json.loads(receipt_path.read_text());assert receipt['published_pairs']==pairs and receipt['all_pairs_valid'] and receipt['all_guards_match_known_input_bytes']
  pipeline.stage(cache,target,receipt)
  for f in [target/filename,*target.glob('cache/**/*.dll')]:subprocess.run([executable('llvm-strip.exe'),'--strip-debug',str(f)],check=True)
  (target/'AOT_CACHE_AUDIT.json').write_text(json.dumps({k:receipt[k] for k in ['game_id','cache_tag','published_pairs','manifest_rows','all_pairs_valid','all_guards_match_known_input_bytes','full_static_coverage_proven']},indent=2)+'\n')
  profiles.append(f'\n[[profile]]\nid = "{region}"\nsize = {size}\nsha256 = "{digest}"\nbackend = "backends/{region}/{filename}"\n')
 with (out/'regional-launch.toml').open('a') as f:f.write(''.join(profiles))
 (out/'Start-TombaRecomp.cmd').write_text('@echo off\r\ncd /d "%~dp0"\r\nstart "" "%~dp0TombiRecompEU.exe"\r\n',encoding='ascii')
 shutil.copy2(ROOT/'jp/PORT_STATUS_EN.md',out/'JAPAN_HANDOFF_EN.md')
 if a.enhancements:shutil.copy2(ROOT/'jp/RC2_MOD_REVIEW_EN.md',out/'RC2_MOD_REVIEW_EN.md')
 for name,digest in manifest.items():
  if name!='regional-launch.toml':assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest,name
 shutil.copy2(ROOT/'jp/REGIONAL_README_EN.md',out/'README_EN.md')
 shutil.copy2(ROOT/'jp/MANUAL_RELEASE_TESTS_DE.md',out/'JAPAN_TEST_DE.md')
 shutil.copy2(ROOT/'jp/FEATURES_EN.md',out/'FEATURES.md')
 print(out,flush=True)
if __name__=='__main__':main()
