import io
import json
import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient
from apps.dubbing_web.api import create_app
from apps.dubbing_web.config import Settings
from apps.dubbing_web.domain import voice_key


def seed(app):
    store=app.state.store
    id, root=store.create()
    project={'id':id,'revision':1,'name':'Sample','voice':'Kim Thanh','speed':1,'auto_fit':True,'fit_limit':1.6,
             'background':'off','audio_index':None,'video_file':'source.mp4','video_name':'source.mp4',
             'media':{'duration':3,'audio_tracks':[]},'cues':[{'id':'c1','start':0,'end':2,'text':'Xin chào','voice':None,'speed':None}]}
    store.save(project)
    return project, root


def test_api_revision_validation_and_origin(tmp_path):
    app=create_app(Settings(tmp_path))
    with TestClient(app) as client:
        p, root=seed(app)
        assert client.get('/api/health').status_code==200
        assert len(client.get('/api/voices').json())==23
        assert client.put('/api/projects/'+p['id'],json=p,headers={'Origin':'https://evil.example'}).status_code==403
        changed=client.put('/api/projects/'+p['id'],json=p)
        assert changed.status_code==200
        assert changed.json()['revision']==2
        assert client.put('/api/projects/'+p['id'],json=p).status_code==409
        p['revision']=2;p['voice']='Missing'
        assert client.put('/api/projects/'+p['id'],json=p).status_code==400
        assert client.post('/api/projects/'+p['id']+'/jobs',json={'kind':'mkv'}).status_code==400
        assert client.get('/api/projects/'+p['id']+'/files/../../projects.sqlite3').status_code==404


def test_output_is_unavailable_after_edit(tmp_path):
    app=create_app(Settings(tmp_path))
    with TestClient(app) as client:
        p,root=seed(app)
        output=root/'renders'/'abc';output.mkdir()
        (output/'dubbed.mp3').write_bytes(b'fake test bytes')
        (output/'job.json').write_text(json.dumps({'status':'complete','revision':1}))
        url='/api/projects/'+p['id']+'/files/renders/abc/dubbed.mp3'
        assert client.get(url).status_code==200
        client.put('/api/projects/'+p['id'],json=p)
        assert client.get(url).status_code==409
