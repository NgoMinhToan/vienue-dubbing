"""Local voice enrollment; immutable voice IDs keep project/queue caches stable."""
import json
import shutil
import threading
from uuid import uuid4
import numpy as np
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import FileResponse
from . import media
from .store import Conflict
from .pronunciation import spoken_text


def install_studio(app, store, jobs, presets, dictionary):
    root = store.root / 'studio'
    root.mkdir(exist_ok=True)
    states = {}
    lock = jobs.lock

    def folder(id):
        if len(id) != 32 or any(c not in '0123456789abcdef' for c in id):
            raise KeyError(id)
        return root / id

    def persist(state):
        jobs.write_record(folder(state['id']) / 'job.json', jobs.public(state))

    def register(state):
        presets['custom:' + state['id']] = {'description': 'Giọng tùy chỉnh · ' + state['name']}

    for path in root.glob('*/job.json'):
        state = json.loads(path.read_text(encoding='utf-8'))
        state['cancel'] = threading.Event()
        if state['status'] in ('queued', 'running'):
            state.update(status='cancelled', message='Tác vụ bị gián đoạn. Tạo lại từ mẫu nguồn.')
        states[state['id']] = state
        if state['status'] == 'saved':
            register(state)
        persist(state)

    def resolve(id):
        if not id.startswith('custom:'):
            return id
        key = id.removeprefix('custom:')
        if states[key]['status'] != 'saved':
            raise ValueError('Giọng chưa được lưu vào thư viện.')
        with np.load(folder(key) / 'voice.npz', allow_pickle=False) as data:
            return {'speaker_emb': data['speaker_emb'], 'codes': data['codes']}

    jobs.resolve_voice = resolve

    def work(state):
        dest = folder(state['id'])
        try:
            with lock:
                jobs.check_cancel(state)
                state['_executing']=True
                state.update(status='running', message='Chuẩn hóa và kiểm tra mẫu…')
                persist(state)
            media.run('ffmpeg', ['-v','error','-nostdin','-y','-i',dest/'source', '-ss',state['start'], '-t',state['end']-state['start'], '-vn','-ac','1','-ar','24000',dest/'reference.wav'], state['cancel'])
            import soundfile as sf
            wav, sr = sf.read(dest/'reference.wav', dtype='float32')
            if len(wav)/sr < 3 or not np.isfinite(wav).all():
                raise ValueError('Mẫu phải có ít nhất 3 giây âm thanh hợp lệ.')
            rms = float(np.sqrt(np.mean(wav**2)))
            if rms < 0.003:
                raise ValueError('Mẫu quá nhỏ hoặc im lặng. Hãy chọn đoạn có lời nói rõ.')
            if float(np.mean(np.abs(wav) >= .999)) > .01:
                raise ValueError('Mẫu bị clipping. Hãy thu lại với mức micro thấp hơn.')
            jobs.check_cancel(state)
            state.update(message='Đang trích xuất giọng trên CPU…'); persist(state)
            model = jobs.load_model()
            emb, codes = model.encode_reference(dest/'reference.wav', denoise=False)
            jobs.check_cancel(state)
            np.savez_compressed(dest/'voice.npz', speaker_emb=np.asarray(emb), codes=np.asarray(codes))
            state.update(message='Đang tạo bản nghe thử…'); persist(state)
            preview = model.infer(state['spoken_text'], voice={'speaker_emb':emb,'codes':codes})
            jobs.check_cancel(state)
            if not len(preview):
                raise ValueError('Không tạo được bản nghe thử.')
            sf.write(dest/'preview.wav', preview, 48000)
            with lock:
                jobs.check_cancel(state)
                state.update(status='ready', message='Nghe thử rồi lưu giọng vào thư viện.')
        except media.Cancelled:
            state.update(status='cancelled', message='Đã dừng. Có thể tạo lại từ mẫu nguồn.')
        except Exception as exc:
            state.update(status='failed', message=str(exc))
        finally:
            with lock:
                state['_executing']=False
                persist(state)

    router = APIRouter(prefix='/api/studio')

    @router.get('')
    def listing():
        with lock:
            return [jobs.public(s) for s in states.values()]

    @router.post('')
    def create(audio: UploadFile=File(...), name: str=Form(...), start: float=Form(0), end: float=Form(8), text: str=Form('Xin chào, đây là giọng đọc tùy chỉnh của tôi.')):
        if not name.strip() or len(name)>100 or not text.strip() or len(text)>500:
            raise ValueError('Tên tối đa 100 ký tự, câu thử từ 1 đến 500 ký tự.')
        if not np.isfinite([start,end]).all() or start<0 or not 3<=end-start<=8:
            raise ValueError('Chọn đoạn mẫu từ 3 đến 8 giây.')
        with lock:
            if any(s['status'] in ('queued','running') for s in states.values()):
                raise Conflict('Đang tạo một giọng. Đợi hoặc dừng trước khi tạo giọng khác.')
            id=uuid4().hex
            dest=folder(id); dest.mkdir()
            try:
                size=0
                with (dest/'source').open('wb') as target:
                    while chunk:=audio.file.read(1024*1024):
                        size+=len(chunk)
                        if size>50*1024**2: raise ValueError('Mẫu tối đa 50 MB.')
                        target.write(chunk)
                state={'id':id,'name':name.strip(),'text':text,'spoken_text':spoken_text(text,dictionary()['rules']), 'start':start,'end':end,'status':'queued','message':'Đang chờ worker CPU…','cancel':threading.Event()}
                states[id]=state; persist(state)
                jobs.pool.submit(work,state)
                return jobs.public(state)
            except Exception:
                states.pop(id,None);shutil.rmtree(dest);raise

    @router.post('/{id}/cancel')
    def cancel(id: str):
        with lock:
            state=states[id]
            if state['status'] in ('queued','running'): state['cancel'].set()
            return {'ok':True}

    @router.post('/{id}/retry')
    def retry(id: str):
        with lock:
            state=states[id]
            if state['status'] not in ('cancelled','failed') or state.get('_executing'):
                raise Conflict('Chỉ thử lại tác vụ đã dừng hoặc lỗi.')
            if any(s['status'] in ('queued','running') for s in states.values()):
                raise Conflict('Đợi tác vụ Phòng thu hiện tại hoàn tất.')
            state['cancel'].clear()
            state.update(status='queued',message='Đang chờ thử lại…',spoken_text=spoken_text(state['text'],dictionary()['rules']))
            persist(state);jobs.pool.submit(work,state)
            return jobs.public(state)

    @router.post('/{id}/save')
    def save(id: str):
        with lock, store.lock:
            state=states[id]
            if state['status'] != 'ready': raise Conflict('Chỉ lưu giọng sau khi tạo mẫu thành công.')
            voice_id='custom:'+id
            # The immutable embedding lives in the data volume, never in installed model assets.
            with store.connection() as db:
                db.execute('INSERT OR REPLACE INTO voice_metadata VALUES (?,?)',(voice_id,json.dumps({'name':state['name'],'sample_text':state['text']},ensure_ascii=False)))
            state.update(status='saved',message='Đã lưu vào thư viện giọng.')
            persist(state);register(state)
            return {'voice_id':voice_id}

    @router.get('/{id}/audio/{kind}')
    def audio_file(id: str, kind: str):
        if kind not in ('reference','preview'): raise KeyError(kind)
        state=states[id]
        if state['status'] not in ('ready','saved'): raise Conflict('Âm thanh chưa sẵn sàng.')
        return FileResponse(folder(id)/(kind+'.wav'),media_type='audio/wav')

    @router.delete('/{id}')
    def delete(id: str):
        with lock, store.lock:
            state=states[id]
            if state['status'] in ('queued','running') or state.get('_executing'): raise Conflict('Dừng và chờ tác vụ kết thúc trước khi xóa.')
            voice_id='custom:'+id
            projects=store.list()
            for path in store.root.glob('projects/*/renders/*/snapshot.json'):
                projects.append(json.loads(path.read_text(encoding='utf-8')))
            if any(p.get('voice')==voice_id or any(c.get('voice')==voice_id for c in p.get('cues',[])) for p in projects):
                raise Conflict('Giọng đang được dự án hoặc phiên bản hàng đợi sử dụng. Đổi giọng và gỡ các phiên bản liên quan trước.')
            if any(s['status'] in ('queued','running') for s in list(app.state.library_samples.values())+list(jobs.items.values())):
                raise Conflict('Đợi nghe mẫu giọng hoàn tất trước khi xóa.')
            shutil.rmtree(folder(id))
            presets.pop(voice_id,None);del states[id]
            with store.connection() as db: db.execute('DELETE FROM voice_metadata WHERE id=?',(voice_id,))
            return {'ok':True}

    app.include_router(router)
    app.state.studio_states=states
