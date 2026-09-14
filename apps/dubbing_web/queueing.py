"""Durable, immutable input versions; one CPU executor handles released items."""
import json
import shutil
import threading
from uuid import uuid4
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Literal
from .store import Conflict


class VersionRequest(BaseModel):
    revision: int
    kind: Literal['generate','mp3','mkv'] = 'mp3'
    mode: Literal['now','wait'] = 'now'
    overflow_policy: Literal['keep','skip'] = 'keep'


class EditVersion(BaseModel):
    revision: int


class Queue:
    def __init__(self,store,jobs):
        self.store,self.jobs=store,jobs
        with store.connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS queue_sequence (project TEXT PRIMARY KEY, number INTEGER NOT NULL)')

    def snapshot_path(self,item):
        return self.store.directory(item['project'])/'renders'/item['id']/'snapshot.json'

    def add(self,id,values):
        with self.jobs.lock,self.store.lock:
            p=self.store.get(id)
            if p['revision']!=values.revision:
                raise Conflict('Dự án đã đổi. Nạp lại trước khi tạo phiên bản.')
            if values.kind=='mkv' and p['audio_index'] is None:
                raise ValueError('Video không có âm gốc. Chọn xuất MP3.')
            with self.store.connection() as db:
                db.execute('BEGIN IMMEDIATE')
                row=db.execute('SELECT number FROM queue_sequence WHERE project=?',(id,)).fetchone()
                number=(row[0] if row else 0)+1
                db.execute('INSERT OR REPLACE INTO queue_sequence VALUES (?,?)',(id,number))
            jid=uuid4().hex
            item={'id':jid,'project':id,'project_name':p['name'],'revision':p['revision'],'version':number,
                  'kind':values.kind,'status':'waiting','done':0,'total':len(p['cues']),
                  'message':'Đang chờ bắt đầu hàng đợi.','warnings':[], 'overflow_policy':values.overflow_policy,
                  'cancel':threading.Event()}
            self.snapshot_path(item).parent.mkdir()
            self.jobs.write_record(self.snapshot_path(item),p)
            self.jobs.persist(item)
            self.jobs.items[jid]=item
            if values.mode=='now':
                self.start(jid)
            return self.jobs.public(item)

    def start(self,id):
        with self.jobs.lock:
            item=self.jobs.items[id]
            if not item.get('version') or item['status'] not in ('waiting','cancelled','error') or item.get('_executing'):
                raise Conflict('Chỉ bắt đầu được phiên bản đang chờ.')
            self.store.get(item['project'])
            p=json.loads(self.snapshot_path(item).read_text(encoding='utf-8'))
            item.update(status='queued',done=0,warnings=[],message='Đã đưa vào worker CPU.')
            for field in ('skipped_cues','file','preview','reused_mix'):
                item.pop(field,None)
            item['cancel'].clear()
            item['_dispatch']=item.get('_dispatch',0)+1
            self.jobs.persist(item)
            self.jobs.pool.submit(self.jobs.execute,item,p,None,False,item['overflow_policy'],item['_dispatch'])
            return self.jobs.public(item)

    def edit(self,id,revision):
        with self.jobs.lock,self.store.lock:
            item=self.jobs.items[id]
            if not item.get('version') or item['status'] not in ('waiting','queued') or item.get('_executing'):
                raise Conflict('Chỉ chỉnh sửa phiên bản đang chờ; dừng tác vụ đã bắt đầu trước.')
            current=self.store.get(item['project'])
            if current['revision']!=revision:
                raise Conflict('Dự án đã đổi. Nạp lại trước khi khôi phục phiên bản.')
            snapshot=json.loads(self.snapshot_path(item).read_text(encoding='utf-8'))
            snapshot['revision']=revision+1
            self.store.save(snapshot,expected=revision)
            item['cancel'].set()
            item['status']='cancelled'
            # Only this waiting item's folder is removed after restoring successfully.
            folder=self.snapshot_path(item).parent.resolve()
            expected=(self.store.directory(item['project'])/'renders').resolve()
            if folder.parent!=expected:
                raise ValueError('Đường dẫn hàng đợi không hợp lệ.')
            shutil.rmtree(folder)
            del self.jobs.items[id]
            return {'project':item['project']}

    def summary(self,id):
        items=[j for j in self.jobs.items.values() if j['project']==id and j.get('version')]
        return {'total':len(items),'waiting':sum(j['status'] in ('waiting','queued') for j in items),
                'completed':sum(j['status']=='complete' for j in items),
                'current':[j['version'] for j in items if j['status']=='running'],
                'last_completed':max((j['version'] for j in items if j['status']=='complete'),default=None)}

    def cancel_project(self,id):
        # Caller holds jobs.lock. Queued workers check cancelled before accessing disk.
        for item in self.jobs.items.values():
            if item['project']==id and item['status'] in ('waiting','queued','running'):
                item['cancel'].set()
                if item['status']!='running':
                    item.update(status='cancelled',message='Đã hủy khi xóa dự án.')
                    self.jobs.persist(item)
        return any(j['project']==id and (j['status']=='running' or j.get('_executing')) for j in self.jobs.items.values())


def install_queue(app,store,jobs):
    queue=Queue(store,jobs)
    router=APIRouter(prefix='/api')
    @router.get('/queue')
    def listing():
        with jobs.lock:
            return [jobs.public(j) for j in jobs.items.values() if j.get('version')]
    @router.post('/projects/{id}/versions')
    def add(id: str,values:VersionRequest):
        return queue.add(id,values)
    @router.post('/queue/{id}/start')
    def start(id: str):
        return queue.start(id)
    @router.post('/queue/start')
    def start_all():
        with jobs.lock:
            for id,item in list(jobs.items.items()):
                if item.get('version') and item['status']=='waiting':
                    queue.start(id)
        return {'ok':True}
    @router.post('/queue/{id}/edit')
    def edit(id: str,values:EditVersion):
        return queue.edit(id,values.revision)
    app.include_router(router)
    return queue
