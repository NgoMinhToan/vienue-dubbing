"""Synthetic long-timeline mixer benchmark; does not measure TTS inference."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import threading
import time

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from apps.dubbing_web.media import mix

parser = argparse.ArgumentParser()
parser.add_argument('--seconds', type=int, default=600)
parser.add_argument('--cues', type=int, default=1000)
args = parser.parse_args()
assert args.seconds > 0 and args.cues > 0
base = ROOT / '.test-data'
base.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='timeline-', dir=base) as folder:
    root = Path(folder)
    clip = root/'clip.wav'
    sf.write(clip, np.zeros(9600), 48000)
    cues = [{'start':i*args.seconds/args.cues, 'duration':.2, 'frames':9600, 'path':clip} for i in range(args.cues)]
    project = {'media':{'duration':args.seconds}, 'audio_index':None, 'background':'off', 'video_file':'unused'}
    started = time.perf_counter()
    mix(project, root, cues, root/'mix.wav', threading.Event())
    elapsed = time.perf_counter() - started
    info = sf.info(root/'mix.wav')
    assert abs(info.duration - args.seconds) < .01
    print(json.dumps({'kind':'synthetic_mixer_only', 'cues':args.cues, 'timeline_seconds':args.seconds,
                      'elapsed_seconds':round(elapsed,2), 'output_bytes':(root/'mix.wav').stat().st_size}))
