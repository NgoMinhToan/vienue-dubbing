"""End-to-end synthetic project with distinct real TTS cues; no user media is used."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from apps.dubbing_web.config import Settings
from apps.dubbing_web.store import Store
from apps.dubbing_web.jobs import Jobs

parser = argparse.ArgumentParser()
parser.add_argument('--minutes', type=int, default=10)
parser.add_argument('--cues', type=int, default=60)
args = parser.parse_args()
Settings.from_env()  # Reuse the model cache, but keep benchmark projects isolated.
base = ROOT/'.test-data'/f'tts-{args.minutes}min'
store = Store(base)
pid, root = store.create()
duration = args.minutes*60
cues = [{'id':f'cue-{i}', 'start':i*duration/args.cues,'end':(i+1)*duration/args.cues,
         'text':f'Đoạn thứ {i+1}. Hôm nay chúng ta cùng kiểm tra chất lượng giọng đọc tiếng Việt trên máy tính. Những câu nói cần rõ ràng, tự nhiên và giữ đúng thời gian của bản video.'}
        for i in range(args.cues)]
project = {'id':pid,'revision':1,'name':'Synthetic real TTS benchmark','voice':'Kim Thanh',
           'speed':1,'auto_fit':True,'fit_limit':1.6,'background':'off','audio_index':None,
           'video_file':'unused.mp4','media':{'duration':duration},'cues':cues}
store.save(project)
jobs = Jobs(store)
started = time.perf_counter()
job = jobs.submit(project,'mp3',overflow_policy='keep')
try:
    while jobs.items[job['id']]['status'] in ('queued','running'):
        current = jobs.items[job['id']]
        print(f"{current['done']}/{args.cues} {current['status']}",flush=True)
        time.sleep(10)
    report = jobs.public(jobs.items[job['id']])
    report.update(elapsed_seconds=round(time.perf_counter()-started,2),timeline_seconds=duration,cue_count=args.cues)
    (base/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))
    if report['status'] != 'complete':
        raise SystemExit(1)
finally:
    jobs.shutdown()
