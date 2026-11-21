import pytest
from fastapi.testclient import TestClient
from apps.dubbing_web.api import create_app
from apps.dubbing_web.config import Settings


def test_browse_import_unicode_and_root_boundary(tmp_path,monkeypatch):
    root=tmp_path/'nguồn video';root.mkdir()
    source=root/'phim thử.mp4';source.write_bytes(b'video-fixture')
    subtitle=root/'phụ đề.srt';subtitle.write_text('1\n00:00:00,000 --> 00:00:01,000\nXin chào\n',encoding='utf-8')
    (root/'secret.txt').write_text('not listed')
    monkeypatch.setenv('APP_MEDIA_ROOT',str(root))
    monkeypatch.setattr('apps.dubbing_web.api.inspect_video',lambda p:{'duration':2,'audio_tracks':[],'video_index':0})
    app=create_app(Settings(tmp_path/'data'))
    with TestClient(app) as client:
        listing=client.get('/api/media').json()
        assert {e['name'] for e in listing['entries']}=={source.name,subtitle.name}
        assert client.get('/api/media',params={'path':'..'}).status_code==400
        assert client.get('/api/media',params={'path':str(tmp_path)}).status_code==400
        response=client.post('/api/media/import',json={'video':source.name,'srt':subtitle.name})
        assert response.status_code==200,response.text
        p=response.json()
        assert p['cues'][0]['text']=='Xin chào'
        assert (app.state.store.directory(p['id'])/p['video_file']).read_bytes()==source.read_bytes()
        assert client.post('/api/media/import',json={'video':'missing.mp4','srt':subtitle.name}).status_code==400
        assert client.post('/api/media/import',json={'video':source.name,'srt':'secret.txt'}).status_code==400


def test_symlink_outside_root_is_hidden_and_rejected(tmp_path,monkeypatch):
    root=tmp_path/'media';root.mkdir()
    outside=tmp_path/'outside';outside.mkdir()
    try:
        (root/'link').symlink_to(outside,target_is_directory=True)
    except OSError:
        pytest.skip('Host does not allow symlinks')
    monkeypatch.setenv('APP_MEDIA_ROOT',str(root))
    with TestClient(create_app(Settings(tmp_path/'data'))) as client:
        assert client.get('/api/media').json()['entries']==[]
        assert client.get('/api/media',params={'path':'link'}).status_code==400


def _fake_video(duration):
    return {'duration':duration,'video_index':0,'video_start':0,'audio_tracks':[],'container':'mp4'}


def _media_source(tmp_path,monkeypatch,duration=2):
    root=tmp_path/'media';root.mkdir()
    source=root/'phim gốc.mp4';source.write_bytes(b'video-fixture')
    subtitle=root/'phụ đề.srt';subtitle.write_text('1\n00:00:00,000 --> 00:00:01,000\nXin chào\n',encoding='utf-8')
    monkeypatch.setenv('APP_MEDIA_ROOT',str(root))
    monkeypatch.setattr('apps.dubbing_web.api.inspect_video',lambda p:_fake_video(duration))
    app=create_app(Settings(tmp_path/'data'))
    return root,source,subtitle,app


def test_in_place_import_serves_and_recovers_missing_source(tmp_path,monkeypatch):
    root,source,subtitle,app=_media_source(tmp_path,monkeypatch)
    with TestClient(app) as client:
        response=client.post('/api/media/import',json={'video':source.name,'srt':subtitle.name,'in_place':True})
        assert response.status_code==200,response.text
        p=response.json()
        assert p['video_external'] is True
        assert p['video_path']==str(source.resolve())
        project_dir=app.state.store.directory(p['id'])
        assert not (project_dir/source.name).exists()
        assert not list(project_dir.glob('source*'))
        served=client.get(f"/api/projects/{p['id']}/files/{source.name}")
        assert served.status_code==200 and served.content==b'video-fixture'
        assert client.get('/api/projects').json()[0]['available'] is True

        source.unlink()
        blocked=client.get(f"/api/projects/{p['id']}")
        assert blocked.status_code==409
        assert blocked.json()['code']=='source_missing'
        assert client.get('/api/projects').json()[0]['available'] is False

        replacement=root/'phim mới.mp4';replacement.write_bytes(b'replacement')
        fixed=client.post(f"/api/projects/{p['id']}/source/in-place",json={'revision':p['revision'],'video':replacement.name})
        assert fixed.status_code==200,fixed.text
        assert fixed.json()['video_external'] is True
        assert fixed.json()['video_path']==str(replacement.resolve())
        reopened=client.get(f"/api/projects/{p['id']}")
        assert reopened.status_code==200
        assert reopened.json()['cues'][0]['text']=='Xin chào'


def test_changed_in_place_source_is_reanalysed(tmp_path,monkeypatch):
    root=tmp_path/'media';root.mkdir()
    source=root/'phim.mp4';source.write_bytes(b'original-video')
    subtitle=root/'phụ đề.srt';subtitle.write_text('1\n00:00:00,000 --> 00:00:01,000\nXin chào\n',encoding='utf-8')
    monkeypatch.setenv('APP_MEDIA_ROOT',str(root))
    durations=iter([2,5])
    monkeypatch.setattr('apps.dubbing_web.api.inspect_video',lambda p:_fake_video(next(durations)))
    app=create_app(Settings(tmp_path/'data'))
    with TestClient(app) as client:
        p=client.post('/api/media/import',json={'video':source.name,'srt':subtitle.name,'in_place':True}).json()
        assert p['media']['duration']==2
        source.write_bytes(b'changed-video-with-different-size')
        opened=client.get(f"/api/projects/{p['id']}")
        assert opened.status_code==200,opened.text
        data=opened.json()
        assert data['media']['duration']==5
        assert data['source_warning']
        assert app.state.store.get(p['id'])['media']['duration']==5
        # Unchanged afterwards: no warning and no extra analysis.
        assert not client.get(f"/api/projects/{p['id']}").json()['source_warning']


def test_upload_replacement_clears_in_place_reference(tmp_path,monkeypatch):
    root,source,subtitle,app=_media_source(tmp_path,monkeypatch)
    with TestClient(app) as client:
        p=client.post('/api/media/import',json={'video':source.name,'srt':subtitle.name,'in_place':True}).json()
        result=client.post(f"/api/projects/{p['id']}/source",data={'revision':p['revision']},files={'video':('upload.mp4',b'copied')})
        assert result.status_code==200,result.text
        data=result.json()
        assert data['video_external'] is False
        assert data['video_path'] is None
        assert data['video_stat'] is None
        assert (app.state.store.directory(p['id'])/data['video_file']).read_bytes()==b'copied'
