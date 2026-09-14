import json
import numpy as np
import pytest
import soundfile as sf
import shutil
from apps.dubbing_web.jobs import Jobs
from apps.dubbing_web.store import Store
from apps.dubbing_web.domain import voice_key


class DeferredPool:
    def submit(self, fn, *args):
        self.pending = (fn, args)

    def shutdown(self, **kwargs):
        pass


def setup(tmp_path):
    store = Store(tmp_path)
    pid, root = store.create()
    project = {'id':pid,'revision':1,'name':'Recovery','voice':'Kim Thanh',
               'media':{'duration':2},'cues':[{'id':'c1','start':0,'end':1,'text':'Hello'}]}
    store.save(project)
    jobs = Jobs(store)
    jobs.pool.shutdown()
    jobs.pool = DeferredPool()
    return jobs, project, root


def test_queued_job_persists_and_restart_marks_interrupted(tmp_path):
    jobs, project, root = setup(tmp_path)
    job = jobs.submit(project, 'generate')
    record = root/'renders'/job['id']/'job.json'
    assert json.loads(record.read_text(encoding='utf-8'))['status'] == 'queued'
    jobs.shutdown()
    restored = Jobs(jobs.store)
    try:
        assert restored.items[job['id']]['status'] == 'cancelled'
        assert json.loads(record.read_text(encoding='utf-8'))['status'] == 'cancelled'
        assert not record.with_suffix('.tmp').exists()
    finally:
        restored.shutdown()


def test_cancel_during_last_inference_keeps_cache_and_resume_uses_it(tmp_path):
    jobs, project, root = setup(tmp_path)
    job = jobs.submit(project, 'generate')
    record = jobs.items[job['id']]
    calls = []
    class Engine:
        def infer(self, *args, **kwargs):
            calls.append(1)
            record['cancel'].set()
            return np.zeros(4800)
    jobs.tts = Engine()
    jobs.execute(record, project, None, False)
    assert record['status'] == 'cancelled'
    assert (root/'clips'/(voice_key(project['cues'][0],project)+'.wav')).exists()
    second = jobs.submit(project, 'generate')
    jobs.execute(jobs.items[second['id']], project, None, False)
    assert jobs.items[second['id']]['status'] == 'complete'
    assert len(calls) == 1
    assert [p.name for p in (root/'renders'/job['id']).iterdir()] == ['job.json']
    jobs.shutdown()


@pytest.mark.parametrize('policy,expected', [('keep',2),('skip',1)])
def test_overflow_preselected_exports_once(tmp_path, monkeypatch, policy, expected):
    from apps.dubbing_web import media
    jobs, p, root = setup(tmp_path)
    p.update(speed=1, auto_fit=True, fit_limit=1)
    p['cues'] = [{'id':'a','start':0,'end':.5,'text':'Long'}, {'id':'b','start':1,'end':2,'text':'Short'}]
    jobs.store.save(p)
    for c, frames in zip(p['cues'], [72000,4800]):
        sf.write(root/'clips'/(voice_key(c,p)+'.wav'), np.zeros(frames),48000)
    mixed = []
    monkeypatch.setattr(media,'tempo',lambda source,dest,*args: shutil.copyfile(source,dest))
    def mix(project, directory, clips, output, cancel):
        mixed.append(clips)
        sf.write(output,np.zeros(96000),48000)
    monkeypatch.setattr(media,'mix',mix)
    monkeypatch.setattr(media,'encode_mp3',lambda source,dest,*args: dest.write_bytes(b'test'))
    submitted = jobs.submit(p,'mp3',overflow_policy=policy)
    record = jobs.items[submitted['id']]
    jobs.execute(record,p,None,False,policy)
    assert record['status'] == 'complete'
    assert len(mixed) == 1 and len(mixed[0]) == expected
    assert [c['start'] for c in mixed[0]] == ([0,1] if policy=='keep' else [1])
    assert record.get('skipped_cues',[]) == ([1] if policy=='skip' else [])
    next_job = jobs.submit(p,'mp3',overflow_policy=policy)
    jobs.execute(jobs.items[next_job['id']],p,None,False,policy)
    assert jobs.items[next_job['id']]['reused_mix']
    assert len(mixed) == 1  # Exporting the unchanged mix must not run tempo/mix a second time.
    jobs.shutdown()
