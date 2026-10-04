"""Capture a live transition from the debug display ring, without pausing.

For forensic runs only: screenshot readback has overhead. Audio acceptance
must be repeated without display capture. Each response retains its frame ID.
"""
import argparse
import json
from pathlib import Path
import socket
import time


def request(port, **command):
    with socket.create_connection(('127.0.0.1', port), timeout=15) as conn:
        conn.sendall((json.dumps(command) + '\n').encode())
        response = ''
        for line in conn.makefile():
            response += line
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                pass
        raise RuntimeError(f'Truncated response: {response[:200]}')


def capture(port, directory, seconds, buttons, input_frames=2):
    directory.mkdir(parents=True, exist_ok=True)
    before = request(port, cmd='audio_stats')
    start = request(port, cmd='frame')['frame']
    receipt = {'start_frame': start, 'audio_before': before, 'frames': [], 'errors': []}
    if buttons is not None:
        request(port, cmd='press', buttons=buttons, frames=input_frames)
    deadline = time.monotonic() + seconds
    last = start - 1
    while time.monotonic() < deadline:
        ring = request(port, cmd='display_ring_stats')
        for frame in range(max(last + 1, ring['oldest_frame']), ring['newest_frame'] + 1):
            result = request(port, cmd='display_ring_get', frame=frame,
                             path=str((directory / f'{frame:08d}.png').resolve()))
            receipt['frames' if result.get('ok') else 'errors'].append(result)
            last = frame
    receipt['audio_after'] = request(port, cmd='audio_stats')
    receipt['end_frame'] = request(port, cmd='frame')['frame']
    (directory / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(f'{start}..{receipt["end_frame"]}: {len(receipt["frames"])} captured; {len(receipt["errors"])} misses')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=4379)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=5)
    parser.add_argument('--buttons', type=lambda s: int(s, 0), default=0xFFF7)
    parser.add_argument('--input-frames', type=int, default=2)
    args = parser.parse_args()
    capture(args.port, args.directory, args.seconds, args.buttons, args.input_frames)
