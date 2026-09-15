import json
import numpy as np
from fastapi.testclient import TestClient
from apps.dubbing_web.api import create_app
from apps.dubbing_web.config import Settings
from apps.dubbing_web.jobs import Jobs


class Deferred:
    def __init__(self): self.calls=[]
    def submit(self,fn,*args): self.calls.append((fn,args))
    def shutdown(self,**kwargs): pass
    def run(self):
        fn,args=self.calls.pop(0)
        fn(*args)


def fixture(tmp_path):
    app=create_app(Settings(tmp_path))
    jobs=app.state.jobs
    jobs.pool.shutdown()
    jobs.pool=Deferred()
    calls=[]
    class Fake:
        def infer(self,text,voice):
            calls.append(text)
            return np.zeros(4800)
    jobs.tts=Fake()
    id,root=app.state.store.create()
    p={'id':id,'revision':1,'name':'Queue test','voice':'Kim Thanh','speed':1,'auto_fit':True,'fit_limit':1.6,
       'background':'off','audio_index':None,'video_file':'source.mp4','video_name':'source.mp4',
       'media':{'duration':2,'audio_tracks':[]},'cues':[{'id':'c1','start':0,'end':1,'text':'Original','voice':None,'speed':None}]}
    app.state.store.save(p)
    return app,p,root,calls


def add(client,p,mode='wait',kind='generate'):
    r=client.post('/api/projects/'+p['id']+'/versions',json={'revision':p['revision'],'mode':mode,'kind':kind})
    assert r.status_code==200,r.text
    return r.json()


def test_snapshot_survives_restart_and_current_edits(tmp_path):
    app,p,root,calls=fixture(tmp_path)
    with TestClient(app) as client:
        item=add(client,p)
        p['revision']=2;p['cues'][0]['text']='Changed'
        app.state.store.save(p)
        assert client.post('/api/queue/'+item['id']+'/start').status_code==200
        app.state.jobs.pool.run()
        assert calls==['Original']
        assert (root/'renders'/item['id']/'snapshot.json').is_file()
        pending=add(client,p,mode='now')
    restored=Jobs(app.state.store)
    try:
        assert restored.items[pending['id']]['status']=='waiting'
        assert restored.items[item['id']]['status']=='complete'
    finally: restored.shutdown()


def test_edit_removes_queued_item_and_late_callback_is_harmless(tmp_path):
    app,p,root,calls=fixture(tmp_path)
    with TestClient(app) as client:
        item=add(client,p,mode='now')
        assert client.post('/api/queue/'+item['id']+'/edit',json={'revision':0}).status_code==409
        assert client.post('/api/queue/'+item['id']+'/edit',json={'revision':1}).status_code==200
        assert client.get('/api/queue').json()==[]
        assert not (root/'renders'/item['id']).exists()
        app.state.jobs.pool.run()
        assert calls==[]
        restored=app.state.store.get(p['id'])
        assert restored['revision']==2
        assert add(client,restored)['version']==2


def test_cancel_then_retry_does_not_execute_old_dispatch(tmp_path):
    app,p,root,calls=fixture(tmp_path)
    with TestClient(app) as client:
        item=add(client,p,mode='now')
        client.post('/api/jobs/'+item['id']+'/cancel')
        app.state.jobs.items[item['id']]['skipped_cues']=[99]
        assert client.post('/api/queue/'+item['id']+'/start').status_code==200
        assert 'skipped_cues' not in app.state.jobs.items[item['id']]
        app.state.jobs.pool.run()
        assert calls==[]
        app.state.jobs.pool.run()
        assert calls==['Original']


def test_delete_confirms_pending_and_waits_for_running_inference(tmp_path):
    app,p,root,calls=fixture(tmp_path)
    with TestClient(app) as client:
        item=add(client,p,mode='now')
        add(client,p)
        assert client.delete('/api/projects/'+p['id']).status_code==409
        class Fake:
            def infer(self,text,voice):
                response=client.delete('/api/projects/'+p['id']+'?confirm_queue=true')
                assert response.status_code==202
                assert root.exists()
                return np.zeros(4800)
        app.state.jobs.tts=Fake()
        app.state.jobs.pool.run()
        assert app.state.jobs.items[item['id']]['status']=='cancelled'
        assert client.delete('/api/projects/'+p['id']+'?confirm_queue=true').status_code==200
        assert not root.exists()
        assert client.get('/api/queue').json()==[]


def test_version_output_remains_downloadable_after_project_changes(tmp_path):
    app,p,root,calls=fixture(tmp_path)
    with TestClient(app) as client:
        item=add(client,p,mode='now',kind='mp3')
        p['revision']=2;p['cues'][0]['text']='Changed'
        app.state.store.save(p)
        app.state.jobs.pool.run()
        output=client.get('/api/jobs/'+item['id']).json()
        assert output['status']=='complete',output
        assert calls==['Original']
        path='/api/projects/'+p['id']+'/files/'+output['file']
        assert client.get(path).status_code==200
        assert client.post('/api/projects/'+p['id']+'/cleanup?confirm=true').status_code==200
        assert client.get(path).status_code==200
        assert json.loads((root/'renders'/item['id']/'snapshot.json').read_text())['revision']==1


def test_project_voice_sample_matches_dictionary_cache_key(tmp_path):
    app,p,root,calls=fixture(tmp_path)
    p['pronunciation']={'rules':[{'source':'Xin chào','target':'Chào bạn'}]}
    app.state.store.save(p)
    with TestClient(app) as client:
        response=client.post('/api/projects/'+p['id']+'/jobs',json={'kind':'sample'})
        assert response.status_code==200
        app.state.jobs.pool.run()
        assert calls[0].startswith('Chào bạn,')


def test_remove_version_preserves_project_and_other_jobs(tmp_path):
    app,p,root,calls=fixture(tmp_path)
    with TestClient(app) as client:
        item=add(client,p,mode='now')
        other=add(client,p)
        clip=root/'clips'/'keep.wav'
        clip.write_bytes(b'cached audio')
        assert client.delete('/api/queue/'+item['id']).status_code==200
        app.state.jobs.pool.run()  # A scheduled callback must not recreate deleted files.
        assert calls==[]
        assert not (root/'renders'/item['id']).exists()
        assert clip.read_bytes()==b'cached audio'
        assert app.state.store.get(p['id'])==p
        assert [j['id'] for j in client.get('/api/queue').json()]==[other['id']]
        assert client.delete('/api/queue/'+item['id']).status_code==404
        assert add(client,p)['version']==3


def test_remove_refuses_running_and_cleanup_then_removes_output(tmp_path):
    app,p,root,calls=fixture(tmp_path)
    with TestClient(app) as client:
        item=add(client,p)
        stored=app.state.jobs.items[item['id']]
        folder=root/'renders'/item['id']
        stored['status']='running'
        assert client.delete('/api/queue/'+item['id']).status_code==409
        stored.update(status='complete',_executing=True)
        assert client.delete('/api/queue/'+item['id']).status_code==409
        assert folder.exists()
        stored['_executing']=False
        (folder/'output.mp3').write_bytes(b'output')
        assert client.delete('/api/queue/'+item['id']).status_code==200
        assert not folder.exists()
        assert client.get('/api/queue').json()==[]
