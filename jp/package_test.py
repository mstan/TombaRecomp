"""Exact packaged three-backend verification; real discs, no desktop APIs."""
import argparse,hashlib,json,os,shutil,subprocess,time,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'eu/tests'))
from audit_release_imports import imports

def main():
 p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--name',required=True);p.add_argument('--all-regions',action='store_true');a=p.parse_args()
 assert Path(a.name).name==a.name
 out=ROOT.parent/'release-qa'/a.name;out.mkdir(parents=True,exist_ok=False);app=out/'Windows x64'
 if a.package.is_file():
  app.mkdir()
  with zipfile.ZipFile(a.package) as archive:
   assert all((app/n).resolve().is_relative_to(app.resolve()) for n in archive.namelist())
   archive.extractall(app)
  if not (app/'TombiRecompEU.exe').exists():
   dirs=[p for p in app.iterdir() if p.is_dir()];assert len(dirs)==1;app=dirs[0]
 else:shutil.copytree(a.package.resolve(),app)
 entry=app/'TombiRecompEU.exe';japan=app/'backends/SLPS-01144';exe=japan/'TombaRecompJP.exe'
 system=Path(os.environ['SystemRoot'])/'System32';env=dict(os.environ,PATH=str(system),SDL_AUDIO_DRIVER='dummy',SDL_AUDIODRIVER='dummy')
 for k in list(env):
  if k.startswith(('PSX_','TOMBA_','TOMBI_','RECOMP_','LNG_')) or k in ['PYTHONPATH','PYTHONHOME']:env.pop(k)
 discs={'SLPS-01144':ROOT/'disc/jp/disc.cue','SCES-01330':ROOT/'disc/Tombi! (Europe) (En,Fr,De,It,Nl) (Rev 1).cue','SCES-01331':ROOT/'disc/eu2/disc.cue'}
 if a.all_regions:discs['SCUS-94236']=ROOT/'disc/Tomba! (USA).cue'
 cases=[]
 for region,disc in discs.items():
  result=subprocess.run([str(entry),'--launcher-disc-check','--disc',str(disc)],cwd=app,env=env,capture_output=True,text=True,errors='replace',timeout=90)
  (out/(region+'-verification.txt')).write_text(result.stdout+result.stderr)
  assert result.returncode==0 and f'expected={region} serial={region} verdict=1 iso=1 handoff=0' in result.stdout
  cases.append(region)
 # Cold restart with the last selection set back to Japan.
 subprocess.run([str(entry),'--regional-select-only','--disc',str(discs['SLPS-01144'])],cwd=app,env=env,check=True,capture_output=True)
 result=subprocess.run([str(entry),'--launcher-disc-check'],cwd=app,env=env,capture_output=True,text=True,timeout=90)
 assert result.returncode==0 and 'expected=SLPS-01144 serial=SLPS-01144 verdict=1' in result.stdout
 (out/'remembered-japan.txt').write_text(result.stdout+result.stderr)
 binaries=[p for p in japan.rglob('*') if p.suffix.lower() in ['.exe','.dll','.pyd']];names={p.name.lower() for p in binaries};missing={}
 for f in binaries:
  for n in imports(f):
   if n.lower() not in names and not (system/n).exists() and not n.lower().startswith(('api-ms-win-','ext-ms-win-')):missing.setdefault(f.relative_to(japan).as_posix(),[]).append(n)
 assert not missing,missing
 with (out/'player-boot.txt').open('w') as log:
  child=subprocess.Popen([str(exe),'--headless','--no-launcher','--disc',str(discs['SLPS-01144'])],cwd=app,env=env,stdout=log,stderr=subprocess.STDOUT)
  try:
   deadline=time.monotonic()+45
   while time.monotonic()<deadline:
    assert child.poll() is None,'Packaged Japan player exited'
    text=(out/'player-boot.txt').read_text(errors='replace')
    if 'executing from PC=' in text and 'NTSC-J (serial SLPS-01144)' in text and ', SLPS-01144)' in text:break
    time.sleep(.2)
   else:raise TimeoutError('Packaged Japan boot')
   time.sleep(3)
  finally:child.terminate();child.wait(timeout=10)
 for i in [1,2]:
  b=(japan/f'saves/SLPS-01144/card{i}.mcd').read_bytes();assert len(b)==131072 and b[:2]==b'MC'
 if a.all_regions:
  usa=app/'backends/SCUS-94236'
  with (out/'usa-player-boot.txt').open('w') as log:
   child=subprocess.Popen([str(usa/'Tomba__Recompiled.exe'),'--headless','--no-launcher','--disc',str(discs['SCUS-94236'])],cwd=app,env=env,stdout=log,stderr=subprocess.STDOUT)
   try:
    deadline=time.monotonic()+45
    while time.monotonic()<deadline:
     assert child.poll() is None,'Packaged USA player exited'
     text=(out/'usa-player-boot.txt').read_text(errors='replace')
     if 'executing from PC=' in text and 'serial SCUS-94236' in text:break
     time.sleep(.2)
    else:raise TimeoutError('Packaged USA boot')
    time.sleep(3)
   finally:child.terminate();child.wait(timeout=10)
  for i in [1,2]:
   b=(usa/f'saves/SCUS-94236/card{i}.mcd').read_bytes();assert len(b)==131072 and b[:2]==b'MC'
 result=dict(result='passed',actual_packaged_launcher_callback_regions=cases,remembered_japan_handoff=True,package_root_cwd=True,missing_imports=missing,production_japan_player_boot=True,original_ntsc_j=True,separate_new_japan_cards=True,developer_tools_removed_from_path=True,desktop_automation=False)
 result.update(production_usa_player_boot=a.all_regions,source_is_final_archive=a.package.is_file())
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(out,flush=True)
if __name__=='__main__':main()
