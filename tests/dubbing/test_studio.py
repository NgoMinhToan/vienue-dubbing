import io
import json
import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient
from apps.dubbing_web.api import create_app
from apps.dubbing_web.config import Settings

class Deferred:
    def __init__(self): self.calls=[]
    def submit(self,fn,*args): self.calls.append((fn,args))
    def shutdown(self,**kw): pass
    def run(self):
        fn,args=self.calls.pop(0);fn(*args)

class Model:
    def encode_reference(self,path,denoise=False):
        return np.ones(192,dtype='float32'),np.ones((4,16),dtype='int64')
    def infer(self,text,voice):
        assert isinstance(voice,dict)
        return np.ones(4800,dtype='float32')*.05

def sample(silent=False):
    data=io.BytesIO()
    sf.write(data,np.zeros(96000) if silent else .1*np.sin(np.arange(96000)*.1),24000,format='WAV')
    return data.getvalue()

def create(client,silent=False):
    r=client.post('/api/studio',data={'name':'Test clone','start':0,'end':4},files={'audio':('sample.wav',sample(silent),'audio/wav')})
    assert r.status_code==200,r.text
    return r.json()['id']

def fixture(tmp_path):
    app=create_app(Settings(tmp_path));app.state.jobs.pool.shutdown()
    app.state.jobs.pool=Deferred();app.state.jobs.tts=Model()
    return app

def test_clone_save_restart_and_delete(tmp_path):
    app=fixture(tmp_path)
    with TestClient(app) as client:
        id=create(client)
        assert client.post('/api/studio/'+id+'/save').status_code==409
        assert client.delete('/api/studio/'+id).status_code==409
        app.state.jobs.pool.run()
        assert client.get('/api/studio').json()[0]['status']=='ready'
        assert client.get('/api/studio/'+id+'/audio/preview').status_code==200
        assert client.post('/api/studio/'+id+'/save').status_code==200
        vid='custom:'+id
        assert any(v['id']==vid for v in client.get('/api/voices').json())
        assert next(v for v in client.get('/api/library/voices').json() if v['id']==vid)['name']=='Test clone'
    other=fixture(tmp_path)
    with TestClient(other) as client:
        assert other.state.jobs.resolve_voice(vid)['speaker_emb'].shape==(192,)
        p,root=other.state.store.create()
        project={'id':p,'name':'Uses clone','revision':1,'voice':vid,'cues':[]}
        other.state.store.save(project)
        assert client.delete('/api/studio/'+id).status_code==409
        project.update(voice='Kim Thanh',revision=2);other.state.store.save(project)
        snapshot=root/'renders'/'queued';snapshot.mkdir()
        (snapshot/'snapshot.json').write_text(json.dumps({**project,'voice':vid}))
        assert client.delete('/api/studio/'+id).status_code==409
        (snapshot/'snapshot.json').unlink()
        assert client.delete('/api/studio/'+id).status_code==200
        assert not (tmp_path/'studio'/id).exists()
        assert client.get('/api/studio/../../audio/preview').status_code!=200

def test_cancel_and_silent_reference(tmp_path):
    app=fixture(tmp_path)
    with TestClient(app) as client:
        id=create(client)
        client.post('/api/studio/'+id+'/cancel')
        app.state.jobs.pool.run()
        assert app.state.studio_states[id]['status']=='cancelled'
        assert client.post('/api/studio/'+id+'/retry').status_code==200
        app.state.jobs.pool.run()
        assert app.state.studio_states[id]['status']=='ready'
        assert client.delete('/api/studio/'+id).status_code==200
        id=create(client,silent=True);app.state.jobs.pool.run()
        assert app.state.studio_states[id]['status']=='failed'
        assert 'im lặng' in app.state.studio_states[id]['message']
        assert client.post('/api/studio',data={'name':'Bad','start':0,'end':90},files={'audio':('a.wav',b'bad')}).status_code==400

def test_interrupted_clone_is_not_published(tmp_path):
    app=fixture(tmp_path)
    with TestClient(app) as client: id=create(client)
    other=fixture(tmp_path)
    with TestClient(other) as client:
        assert client.get('/api/studio').json()[0]['status']=='cancelled'
        assert all(v['id']!='custom:'+id for v in client.get('/api/voices').json())
