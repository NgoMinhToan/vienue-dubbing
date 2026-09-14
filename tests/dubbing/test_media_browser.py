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
