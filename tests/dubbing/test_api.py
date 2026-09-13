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


def test_replace_srt_is_atomic_and_checks_revision(tmp_path):
    app = create_app(Settings(tmp_path))
    with TestClient(app) as client:
        p, root = seed(app)
        url = '/api/projects/' + p['id'] + '/source'
        bad = client.post(url, data={'revision': 1}, files={'srt': ('bad.srt', b'bad')})
        assert bad.status_code == 400
        assert app.state.store.get(p['id'])['cues'] == p['cues']
        content = '1\n00:00:01,000 --> 00:00:02,000\nCâu mới'.encode()
        result = client.post(url, data={'revision': 1}, files={'srt': ('new.srt', content)})
        assert result.status_code == 200
        assert result.json()['revision'] == 2
        assert result.json()['cues'][0]['text'] == 'Câu mới'
        assert client.post(url, data={'revision': 1}, files={'srt': ('new.srt', content)}).status_code == 409


def test_proxy_survives_text_edit_but_not_source_replacement(tmp_path):
    app = create_app(Settings(tmp_path))
    with TestClient(app) as client:
        p, root = seed(app)
        dest = root / 'renders' / 'proxy'; dest.mkdir()
        (dest / 'proxy.mp4').write_bytes(b'test fixture')
        (dest / 'job.json').write_text(json.dumps({'kind':'proxy', 'status':'complete', 'revision':1, 'video_file':'source.mp4'}))
        url = '/api/projects/' + p['id'] + '/files/renders/proxy/proxy.mp4'
        client.put('/api/projects/' + p['id'], json=p)
        assert client.get(url).status_code == 200
        current = app.state.store.get(p['id'])
        current['video_file'] = 'different.mp4'
        app.state.store.save(current)
        assert client.get(url).status_code == 409
