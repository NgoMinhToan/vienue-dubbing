"""Browse only the configured server media root, including read-only Docker mounts."""
import os
from pathlib import Path
from fastapi import APIRouter, UploadFile
from pydantic import BaseModel, Field

VIDEO_EXTENSIONS={'.mp4','.mkv','.mov','.avi','.webm','.m4v'}


class ImportRequest(BaseModel):
    name: str = Field(default='Lồng tiếng mới', min_length=1, max_length=200)
    video: str
    srt: str


def install_media_browser(app, create):
    root=Path(os.environ.get('APP_MEDIA_ROOT',Path.cwd())).resolve()
    router=APIRouter(prefix='/api/media')

    def resolve(relative):
        path=Path(relative)
        if path.is_absolute() or path.drive:
            raise ValueError('Chọn đường dẫn tương đối trong thư mục nguồn.')
        target=(root/path).resolve()
        if not target.is_relative_to(root):
            raise ValueError('Đường dẫn nằm ngoài thư mục nguồn được cấu hình.')
        if not target.exists():
            raise ValueError('Không tìm thấy file/thư mục nguồn. Kiểm tra APP_MEDIA_ROOT và volume mount.')
        return target

    @router.get('')
    def browse(path: str='', offset: int=0):
        folder=resolve(path)
        if not folder.is_dir() or offset<0:
            raise ValueError('Thư mục hoặc vị trí trang không hợp lệ.')
        try:
            entries=[]
            for child in folder.iterdir():
                if child.name.startswith('.'):
                    continue
                try:
                    resolved=child.resolve()
                    if not resolved.is_relative_to(root):
                        continue
                    if not child.is_dir() and child.suffix.lower() not in VIDEO_EXTENSIONS|{'.srt'}:
                        continue
                    entries.append({'name':child.name,'path':child.relative_to(root).as_posix(),
                                    'directory':child.is_dir(),'size':child.stat().st_size if child.is_file() else None})
                except OSError:
                    continue
            entries.sort(key=lambda e:(not e['directory'],e['name'].casefold()))
            return {'root':str(root),'path':folder.relative_to(root).as_posix(), 'entries':entries[offset:offset+200],
                    'next_offset':offset+200 if offset+200<len(entries) else None}
        except PermissionError as exc:
            raise ValueError('Không có quyền đọc thư mục nguồn.') from exc

    @router.post('/import')
    def import_files(values: ImportRequest):
        video,srt=resolve(values.video),resolve(values.srt)
        if not video.is_file() or video.suffix.lower() not in VIDEO_EXTENSIONS or not srt.is_file() or srt.suffix.lower()!='.srt':
            raise ValueError('Cần chọn video và file .srt hợp lệ.')
        try:
            # Copy into application data through the same validated upload pipeline.
            # A read-only source mount is sufficient and original files are never changed.
            with video.open('rb') as v,srt.open('rb') as s:
                return create(values.name,UploadFile(filename=video.name,file=v),UploadFile(filename=srt.name,file=s))
        except PermissionError as exc:
            raise ValueError('Không có quyền đọc file nguồn.') from exc

    app.include_router(router)
