"""Verify original Japan input and stage only an isolated development copy."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'psxrecomp/tools')]
from extract_overlays import DiscReader,enumerate_files,parse_cue
SIZE=289430064
SHA256='fb5b8ea9e3bd328e88a6b8b8ecb0b493d0dda5a9b5f732a7a6e4c9b146d9cd2b'
BOOT_SHA1='07d577698ad31ec1a69b9d7b80a7c3f90b650888'

def main():
 p=argparse.ArgumentParser();p.add_argument('--disc',type=Path,required=True);a=p.parse_args()
 source,raw=parse_cue(str(a.disc.resolve()));source=Path(source)
 assert raw and source.stat().st_size==SIZE
 assert hashlib.file_digest(source.open('rb'),'sha256').hexdigest()==SHA256,'Unsupported original revision'
 home=ROOT/'disc/jp';home.mkdir(parents=True,exist_ok=True);target=home/'disc.bin'
 if not target.exists():
  with source.open('rb') as src,target.open('xb') as dst:shutil.copyfileobj(src,dst)
 assert hashlib.file_digest(target.open('rb'),'sha256').hexdigest()==SHA256
 cue='FILE "disc.bin" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n'
 f=home/'disc.cue'
 if f.exists():assert f.read_text()==cue
 else:f.write_text(cue,encoding='ascii')
 disc=DiscReader(str(target),raw=True)
 try:
  files={n:(l,s) for n,l,s in enumerate_files(disc)};boot=disc.read_file_bytes(*files['SLPS_011.44'])
  assert hashlib.sha1(boot).hexdigest()==BOOT_SHA1
  f=home/'SLPS_011.44'
  if f.exists():assert f.read_bytes()==boot
  else:f.write_bytes(boot)
 finally:disc.close()
 print('PASS: original SLPS-01144 full-track identity and boot; isolated working copy',flush=True)
if __name__=='__main__':main()
