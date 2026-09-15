import time
import numpy as np
from fastapi.testclient import TestClient
from apps.dubbing_web.api import create_app
from apps.dubbing_web.config import Settings


def test_voice_metadata_persists_and_rejects_stale_edit(tmp_path):
    app = create_app(Settings(tmp_path))
    with TestClient(app) as client:
        voice = client.get('/api/library/voices').json()[0]
        id = voice['id']
        response = client.put('/api/library/voices/'+id, json={**voice, 'name':'Tên riêng', 'favorite':True})
        assert response.status_code == 200
        assert response.json()['id'] == id
        assert client.put('/api/library/voices/'+id, json=voice).status_code == 409
        assert client.put('/api/library/voices/missing', json=voice).status_code == 404
    with TestClient(create_app(Settings(tmp_path))) as client:
        saved = next(v for v in client.get('/api/library/voices').json() if v['id']==id)
        assert saved['name']=='Tên riêng' and saved['favorite']


def test_sample_uses_saved_text_and_cache(tmp_path):
    app = create_app(Settings(tmp_path))
    calls=[]
    class Fake:
        def infer(self, text, voice):
            calls.append((text,voice))
            return np.zeros(4800)
    app.state.jobs.tts=Fake()
    with TestClient(app) as client:
        voice=client.get('/api/library/voices').json()[0]
        url='/api/library/voices/'+voice['id']
        client.put(url,json={**voice,'sample_text':'Câu riêng.'})
        sample=client.post(url+'/sample').json()
        for _ in range(100):
            status=client.get('/api/library/samples/'+sample['id']).json()
            if status['status']=='complete': break
            time.sleep(.01)
        assert status['status']=='complete'
        assert calls==[('Câu riêng.',voice['id'])]
        assert client.get('/api/library/samples/'+sample['id']+'/audio').status_code==200
        assert client.post(url+'/sample').json()['id']==sample['id']
        assert len(calls)==1
        dictionary=client.get('/api/dictionary').json()
        dictionary['rules']=[{'source':'Câu riêng','target':'Cách đọc mới'}]
        assert client.put('/api/dictionary',json=dictionary).status_code==200
        changed=client.post(url+'/sample').json()
        assert changed['id']!=sample['id']
        for _ in range(100):
            if client.get('/api/library/samples/'+changed['id']).json()['status']=='complete': break
            time.sleep(.01)
        assert calls[-1]==('Cách đọc mới.',voice['id'])
        assert client.get('/api/library/samples/not-a-hash/audio').status_code==404
