import threading

from fastapi.testclient import TestClient
from apps.dubbing_web.api import create_app
from apps.dubbing_web.config import Settings


def seed(app, name='Phim của tôi'):
    store = app.state.store
    pid, root = store.create()
    project = {'id': pid, 'revision': 1, 'name': name, 'voice': 'Kim Thanh', 'speed': 1,
               'auto_fit': True, 'fit_limit': 1.6, 'background': 'off', 'audio_index': None,
               'video_file': 'source.mp4', 'video_name': 'source.mp4',
               'media': {'duration': 3, 'audio_tracks': []}, 'cues': []}
    store.save(project)
    return project, root


def add_job(app, project, jid, kind='mp3', status='complete', revision=1, version=None):
    folder = app.state.store.directory(project['id']) / 'renders' / jid
    folder.mkdir(parents=True)
    name = 'output.mkv' if kind == 'mkv' else 'dubbed.mp3'
    (folder / name).write_bytes(b'export-bytes')
    item = {'id': jid, 'project': project['id'], 'revision': revision, 'kind': kind,
            'status': status, 'file': f'renders/{jid}/{name}', 'done': 1, 'total': 1,
            'message': '', 'warnings': [], 'cancel': threading.Event()}
    if version is not None:
        item['version'] = version
    app.state.jobs.items[jid] = item
    return item


def test_save_completed_export_and_avoid_overwrite(tmp_path):
    output = tmp_path / 'output'
    app = create_app(Settings(tmp_path / 'data', output=output))
    with TestClient(app) as client:
        project, _ = seed(app)
        add_job(app, project, 'job1')
        first = client.post('/api/jobs/job1/save')
        assert first.status_code == 200, first.text
        saved = first.json()
        assert saved['name'] == 'Phim của tôi-job1.mp3'
        assert (output / saved['name']).read_bytes() == b'export-bytes'
        assert saved['bytes'] == 12

        second = client.post('/api/jobs/job1/save')
        assert second.status_code == 200, second.text
        assert second.json()['name'] == 'Phim của tôi-job1-2.mp3'
        assert (output / second.json()['name']).exists()
        # The project's own render is left untouched.
        assert (app.state.store.directory(project['id']) / 'renders/job1/dubbed.mp3').read_bytes() == b'export-bytes'


def test_save_rejects_incomplete_stale_and_wrong_kind(tmp_path):
    app = create_app(Settings(tmp_path / 'data', output=tmp_path / 'output'))
    with TestClient(app) as client:
        project, _ = seed(app)
        add_job(app, project, 'running', status='running')
        assert client.post('/api/jobs/running/save').status_code == 400

        add_job(app, project, 'proxy', kind='proxy')
        assert client.post('/api/jobs/proxy/save').status_code == 400

        add_job(app, project, 'old', revision=0)
        assert client.post('/api/jobs/old/save').status_code == 400

        add_job(app, project, 'missing')
        (app.state.store.directory(project['id']) / 'renders/missing/dubbed.mp3').unlink()
        assert client.post('/api/jobs/missing/save').status_code == 409


def test_save_version_snapshot_survives_revision_change(tmp_path):
    app = create_app(Settings(tmp_path / 'data', output=tmp_path / 'output'))
    with TestClient(app) as client:
        project, _ = seed(app)
        add_job(app, project, 'version1', revision=0, version=1)
        current = app.state.store.get(project['id'])
        current['revision'] = 5
        app.state.store.save(current)
        result = client.post('/api/jobs/version1/save')
        assert result.status_code == 200, result.text
        assert result.json()['name'] == 'Phim của tôi-v1.mp3'


def test_save_sanitizes_project_name(tmp_path):
    app = create_app(Settings(tmp_path / 'data', output=tmp_path / 'output'))
    with TestClient(app) as client:
        project, _ = seed(app, name='../phim: mới?')
        add_job(app, project, 'job1', kind='mkv')
        result = client.post('/api/jobs/job1/save')
        assert result.status_code == 200, result.text
        name = result.json()['name']
        assert '/' not in name and '..' not in name and name.endswith('.mkv')
        assert (tmp_path / 'output' / name).exists()


def test_save_reports_unwritable_output_directory(tmp_path):
    blocker = tmp_path / 'output'
    blocker.write_text('not a directory')
    app = create_app(Settings(tmp_path / 'data', output=blocker))
    with TestClient(app) as client:
        project, _ = seed(app)
        add_job(app, project, 'job1')
        result = client.post('/api/jobs/job1/save')
        assert result.status_code == 400
        assert 'APP_OUTPUT_DIR' in result.json()['detail'] or 'thư mục' in result.json()['detail']
