"""Fresh original New Game, walk/jump/land; pad inputs and reads only."""
import argparse,json,os,socket,struct,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'eu'))
from campaign_test import Probe,step,ALLOWED
ALLOWED.update(['quit','video_info','spu_status','spu_voices','geom_correction','mod_counters','resident_status','fmv_state','gpu_state','ws_tag_stats','ws_backdrop_ring','wide_shot','display_timing'])

def main():
 p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--opengl',action='store_true');p.add_argument('--port',type=int,default=4516);p.add_argument('--build-dir',type=Path,default=ROOT/'build-jp/full/qa/native');p.add_argument('--config',type=Path,default=ROOT/'jp/game.toml');p.add_argument('--pgxp',action='store_true');p.add_argument('--seamless',choices=['on','off','original']);p.add_argument('--try-roundtrip',action='store_true');p.add_argument('--fmv-skip',action='store_true');p.add_argument('--trace',action='store_true')
 p.add_argument('--profile-defaults',action='store_true');p.add_argument('--require-hq',action='store_true');p.add_argument('--view',choices=['off','Fit','16:9','21:9','32:9'],default='off');p.add_argument('--audio-diagnostics',action='store_true');p.add_argument('--require-bgm',action='store_true');a=p.parse_args()
 build=a.build_dir.resolve();assert build.is_relative_to(ROOT/'build-jp'), 'Private Japan QA build required'
 assert Path(a.name).name==a.name
 out=ROOT/'build-jp'/a.name;out.mkdir(exist_ok=False);probe=Probe(out,a.port)
 try:
  with socket.create_connection(('127.0.0.1',a.port),timeout=.2):raise RuntimeError('Test port occupied')
 except OSError:pass
 env=dict(os.environ,PSX_OVERLAY_AUTOCOMPILE_OFF='1',PSX_INTERNAL_RESOLUTION='native',SDL_AUDIO_DRIVER='dummy',SDL_AUDIODRIVER='dummy')
 if a.profile_defaults:env.pop('PSX_INTERNAL_RESOLUTION',None)
 if a.trace:env['TOMBI_SEAMLESS_TRACE']='1'
 if a.seamless=='original':env['TOMBA_JP_SEAMLESS_TEST_CD']='1'
 if a.seamless:env['PSX_RESIDENT_CACHE']=str(ROOT/'build-jp/rc2/resident-cache')
 def player():
  b=probe.ram(0x800A7B78,48);return dict(state=list(b[4:8]),position=[v/65536 for v in struct.unpack_from('<iii',b,16)],selected_area_section=list(struct.unpack('<HH',probe.ram(0x8009e508,4))),current_area_section=list(struct.unpack('<HH',probe.ram(0x8009ee50,4))))
 def snapshot(n):
  s=player();s['frame']=probe.rpc('frame')['frame'];probe.rpc('screenshot_file',path=str(out/(n+'.png')));(out/(n+'.json')).write_text(json.dumps(s,indent=2)+'\n');return s
 mod_state=build/'mods/state.toml';previous=mod_state.read_bytes() if mod_state.exists() else None
 mod_state.parent.mkdir(exist_ok=True)
 mod_state.write_text('format_version = 2\n[[feature]]\npackage_id = "psx.enhancement.pgxp"\nid = "pgxp"\nenabled = '+str(a.pgxp).lower()+'\n')
 if a.view:
  with mod_state.open('a') as state:state.write('\n[[feature]]\npackage_id = "tomba.enhancement.widescreen"\nid = "widescreen"\nenabled = '+str(a.view!='off').lower()+'\n[feature.values]\naspect = "'+('Fit' if a.view=='off' else a.view)+'"\n')
 if a.seamless:
  with mod_state.open('a') as state:state.write('\n[[feature]]\npackage_id = "tomba.jp.enhancement.seamless"\nid = "resident-assets"\nenabled = '+str(a.seamless!='off').lower()+'\n')
 if a.fmv_skip:
  with mod_state.open('a') as state:state.write('\n[[feature]]\npackage_id = "tomba.enhancement.skip-fmv"\nid = "skip-fmv"\nenabled = true\n')
 with (out/'runtime.log').open('w') as log:
  child=subprocess.Popen([str(build/'TombaRecompJP.exe'),'--headless-opengl' if a.opengl else '--headless','--no-launcher','--game',str(a.config.resolve()),'--disc',str(ROOT/'disc/jp/disc.cue'),'--memcard-dir',str(out/'fresh-cards'),'--debug-port',str(a.port)],cwd=build,env=env,stdout=log,stderr=subprocess.STDOUT)
  try:
   deadline=time.monotonic()+120
   while True:
    assert child.poll() is None,'Runtime exited during boot'
    try:
     if probe.rpc('frame')['frame']>=1500:break
    except (OSError,RuntimeError):pass
    if time.monotonic()>deadline:raise TimeoutError('boot')
    time.sleep(.1)
   for i in range(40):
    s=player()
    if s['state'][0] in [1,5] and s['position'][:2]==[64.0,-52.0] and probe.ram(0x8009E518,1)==b'\x04':break
    probe.drive([step(['start'],16),step([],60),step(['cross'],16),step([],120)])
   else:raise TimeoutError('Original New Game')
   snapshot('new-game')
   for i in range(80):
    probe.drive([step(['circle'],4),step([],35)])
    if player()['state'][0]==1:
     probe.drive([step([],120)])
     if player()['state'][0]==1:break
   else:raise TimeoutError('Original opening dialogs')
   before=snapshot('walk-before');probe.drive([step(['right'],40),step([],4)]);after=snapshot('walk-after')
   assert after['position'][0]>before['position'][0]+5
   probe.drive([step(['cross'],4),step([],8)]);jump=snapshot('jump-air');assert jump['state'][1]==2 and jump['position'][1]<after['position'][1]-1
   probe.drive([step([],80)]);land=snapshot('jump-landed');assert land['state'][0]==1 and land['state'][1]!=2
   audio_samples=[]
   if a.audio_diagnostics or a.require_bgm:
    # Quiet normal gameplay after transient jumping/landing effects expire.
    # A nonzero mixer alone cannot distinguish BGM from sound effects.
    for i in range(4):
     probe.drive([step([],180)])
     status=probe.rpc('spu_status');voices=probe.rpc('spu_voices')
     audio_samples.append(dict(frame=probe.rpc('frame')['frame'],
      bgm_sequence_id=struct.unpack('<h',probe.ram(0x800A4F70,2))[0],
      bgm_vab_id=struct.unpack('<h',probe.ram(0x8009E498,2))[0],
      bank_handles=list(struct.unpack('<44h',probe.ram(0x1F8003A8,88))),
      status=status,voices=voices,timing=probe.rpc('display_timing')))
    (out/'audio-diagnostics.json').write_text(json.dumps(audio_samples,indent=2)+'\n')
    if a.require_bgm:
     assert all(s['bgm_sequence_id']>=0 and s['bgm_vab_id']>=0 for s in audio_samples),'Original BGM sequence/bank did not open'
     assert audio_samples[-1]['status']['nonzero_frames']>audio_samples[0]['status']['nonzero_frames'],'No sustained audio during quiet gameplay'
     assert all(any(v['active'] and int(v['env'],16)>0 for v in s['voices']['voices']) for s in audio_samples),'No sustained SPU voices'
   if a.require_hq:
    assert audio_samples and all(s['timing']['spu_hq_enabled'] for s in audio_samples),'HQ SPU is not enabled in the runtime'
    assert any(s['timing']['spu_hq_proven'] for s in audio_samples),'HQ SPU did not enter verified output during quiet gameplay'
    assert all(s['timing']['vsync_requested']==0 for s in audio_samples),'Fresh VSync is not OFF'
   if a.view!='off':
    renderer=dict(gpu=probe.rpc('gpu_state'),tags=probe.rpc('ws_tag_stats'),backdrop=probe.rpc('ws_backdrop_ring'))
    ws=renderer['gpu']['ws']
    assert ws['mode']==2 and ws['nw_extra']>0 and ws['x_margin']>0 and ws['game_mode'] and ws['view_anchor'],ws
    assert renderer['tags']['hud_roles']['hit']>0,renderer['tags']
    (out/'renderer.json').write_text(json.dumps(renderer,indent=2)+'\n')
    probe.rpc('wide_shot',path=str(out/'world-wide.png'))
   roundtrip=None
   if a.try_roundtrip:
    origin=land['current_area_section'];samples=[];crossed=None;returned=None
    for i in range(12):
     probe.drive([step(['right','cross'],24),step(['right'],56),step([],20)])
     s=snapshot('boundary-out-'+str(i));samples.append(s)
     if s['current_area_section']!=origin and s['state'][0]==1:
      crossed=s;break
    # The ordinary first-house entrance needs Up at its door; do not force
    # an area, quest, position or cutscene. This is one bounded route only.
    if not crossed and 950<=player()['position'][0]<=1100:
     for i in range(3):
      probe.drive([step(['right'],10),step(['up'],30),step([],180)])
      s=snapshot('house-door-'+str(i));samples.append(s)
      if s['current_area_section']!=origin:
       crossed=s;break
    if crossed:
     for i in range(20):
      if player()['state'][0]!=5:break
      probe.drive([step(['circle'],4),step([],90)])
     probe.drive([step(['down'],30),step([],180)])
     s=snapshot('house-down-exit');samples.append(s)
     if s['current_area_section']==origin and s['state'][0]==1:returned=s
     for i in range(12):
      if returned:break
      probe.drive([step(['left','cross'],24),step(['left'],56),step([],20)])
      s=snapshot('boundary-back-'+str(i));samples.append(s)
      if s['current_area_section']==origin and s['state'][0]==1:
       returned=s;break
    roundtrip=dict(origin=origin,crossed=crossed,returned=returned,samples=samples,passed=bool(crossed and returned),bounded_attempt=True)
    (out/'roundtrip.json').write_text(json.dumps(roundtrip,indent=2)+'\n')
   overlay=probe.rpc('overlay_loader_status');assert overlay['dispatch_native']>0 and overlay['registered']>0
   video=probe.rpc('video_info');audio=probe.rpc('spu_status');assert audio['nonzero_frames']>0
   if a.opengl:assert video['gl']==1 and video['backend']=='opengl'
   precision=probe.rpc('geom_correction')
   counters={item['name']:item['count'] for item in probe.rpc('mod_counters')['counters']}
   if a.seamless=='on':assert counters.get('tomba.seamless.batches',0)>0,counters
   if a.seamless in ['off','original']:assert not counters.get('tomba.seamless.batches',0),counters
   if a.seamless=='original':assert counters.get('tomba.jp.seamless.test_original',0)>0,counters
   if a.pgxp:assert precision['pgxp']['dataflow_hit']>0 and precision['pgxp']['tri_precise']>0 and precision['perspective_triangles']>0,precision
   report=dict(result='passed',fresh_original_new_game=True,controller_only=True,artificial_game_state=False,japanese_dialog_framebuffer=True,walk_before=before['position'],walk_after=after['position'],jump=jump['position'],landed=land['position'],native_overlay_dispatches=overlay['dispatch_native'],native_functions_registered=overlay['registered'],nonzero_audio_frames=audio['nonzero_frames'],renderer=video['backend'],gl=video['gl'],desktop_automation=False,area_transition=False,save_load=False)
   report.update(profile_defaults=a.profile_defaults,require_hq=a.require_hq,widescreen=a.view,pgxp_enabled=a.pgxp,precision=precision,seamless=a.seamless,mod_counters=counters,roundtrip=roundtrip,fmv_skip=a.fmv_skip)
   if audio_samples:report['bgm_diagnostics']=audio_samples
   if a.fmv_skip:
    totals=struct.unpack('<22H',probe.ram(0x80071d3c,44));assert totals[1]==3,totals
    report['fmv_original_new_game_teardown']=True;report['fmv_totals_after']=list(totals)
   (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='bgm_diagnostics'}),flush=True)
  finally:
   if child.poll() is None:
    try:probe.rpc('quit');child.wait(timeout=10)
    except Exception:child.terminate();child.wait(timeout=10)
   (out/'events.json').write_text(json.dumps(probe.events,indent=2)+'\n')
   if previous is None:mod_state.unlink(missing_ok=True)
   else:mod_state.write_bytes(previous)
if __name__=='__main__':main()
