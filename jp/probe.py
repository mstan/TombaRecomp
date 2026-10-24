"""Private controller-only Japan acceptance probe; no writes/state loading."""
import argparse,json,os,socket,struct,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'eu'))
from campaign_test import Probe,ALLOWED
ALLOWED.update(('quit','video_info','spu_status'))

def main():
 p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--port',type=int,default=4514);p.add_argument('--hold',type=int,default=0);a=p.parse_args()
 if Path(a.name).name!=a.name:p.error('One output folder component')
 out=ROOT/'build-jp'/a.name;out.mkdir(exist_ok=False);cards=out/'fresh-cards';cards.mkdir()
 build=ROOT/'build-jp/qa/native';probe=Probe(out,a.port)
 try:
  with socket.create_connection(('127.0.0.1',a.port),timeout=.2):raise RuntimeError('Port already in use')
 except OSError:pass
 env=dict(os.environ,PSX_OVERLAY_AUTOCOMPILE_OFF='1',PSX_INTERNAL_RESOLUTION='native',SDL_AUDIO_DRIVER='dummy',SDL_AUDIODRIVER='dummy')
 with (out/'runtime.log').open('w') as log:
  child=subprocess.Popen([str(build/'TombaRecompJP.exe'),'--headless','--no-launcher','--game',str(ROOT/'jp/game.toml'),'--disc',str(ROOT/'disc/jp/disc.cue'),'--memcard-dir',str(cards),'--debug-port',str(a.port)],cwd=build,env=env,stdout=log,stderr=subprocess.STDOUT)
  def sample(label):
   if Path(label).name!=label:raise ValueError('Filename component')
   frame=probe.rpc('frame');game=probe.ram(0x8009E508,64);player=probe.ram(0x800A7B78,0x30)
   result=dict(label=label,frame=frame,game_prefix=game.hex(),player_prefix=player.hex(),area_section=list(struct.unpack_from('<HH',game)),position=[x/65536 for x in struct.unpack_from('<iii',player,16)],player_state=list(player[4:8]))
   try:probe.rpc('screenshot_file',path=str(out/(label+'.png')))
   except RuntimeError as e:result['screenshot_error']=str(e)
   (out/(label+'.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
  try:
   deadline=time.monotonic()+120
   while True:
    if child.poll() is not None:raise RuntimeError('Runtime exited '+str(child.returncode))
    try:
     if probe.rpc('frame')['frame']>=400:break
    except (OSError,RuntimeError):pass
    if time.monotonic()>deadline:raise TimeoutError('Original boot frame deadline')
    time.sleep(.1)
   sample('boot');print('READY '+str(out),flush=True)
   deadline=time.monotonic()+a.hold
   while a.hold and time.monotonic()<deadline and child.poll() is None:time.sleep(.2)
   for line in sys.stdin:
    req=json.loads(line)
    if req.get('quit'):break
    if 'drive' in req:probe.drive(req['drive'])
    if 'sample' in req:sample(req['sample'])
    if 'status' in req:
     print(json.dumps({k:probe.rpc(k) for k in ['frame','video_info','spu_status','overlay_loader_status']}),flush=True)
    print('OK',flush=True)
  finally:
   if child.poll() is None:
    try:probe.rpc('quit');child.wait(timeout=10)
    except Exception:child.terminate();child.wait(timeout=10)
   (out/'events.json').write_text(json.dumps(probe.events,indent=2)+'\n')
 print(out,flush=True)
if __name__=='__main__':main()
