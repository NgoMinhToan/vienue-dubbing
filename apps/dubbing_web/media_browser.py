"""Browse only the configured server media root, including read-only Docker mounts."""
import io
import os
from pathlib import Path
from fastapi import APIRouter, UploadFile
from pydantic import BaseModel, Field

VIDEO_EXTENSIONS={'.mp4','.mkv','.mov','.avi','.webm','.m4v'}
SRT_LIMIT=10*1024*1024


class ImportRequest(BaseModel):
    name: str = Field(default='Lồng tiếng mới', min_length=1, max_length=200)
    video: str
    srt: str
    in_place: bool = False


def media_root():
    return Path(os.environ.get('APP_MEDIA_ROOT', Path.cwd())).resolve()


def resolve_media(relative):
    """Resolve a relative path inside APP_MEDIA_ROOT, rejecting traversal and symlink escapes."""
    root=media_root()
    path=Path(relative)
    if path.is_absolute() or path.drive:
        raise ValueError('Chọn đường dẫn tương đối trong thư mục nguồn.')
    target=(root/path).resolve()
    if not target.is_relative_to(root):
        raise ValueError('Đường dẫn nằm ngoài thư mục nguồn được cấu hình.')
    if not target.exists():
        raise ValueError('Không tìm thấy file/thư mục nguồn. Kiểm tra APP_MEDIA_ROOT và volume mount.')
    return target


def install_media_browser(app, create, create_in_place):
    router=APIRouter(prefix='/api/media')

    @router.get('')
    def browse(path: str='', offset: int=0):
        root=media_root()
        folder=resolve_media(path)
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
        video,srt=resolve_media(values.video),resolve_media(values.srt)
        if not video.is_file() or video.suffix.lower() not in VIDEO_EXTENSIONS or not srt.is_file() or srt.suffix.lower()!='.srt':
            raise ValueError('Cần chọn video và file .srt hợp lệ.')
        try:
            raw=srt.read_bytes()
        except PermissionError as exc:
            raise ValueError('Không có quyền đọc file nguồn.') from exc
        if len(raw)>SRT_LIMIT:
            raise ValueError('SRT quá lớn (tối đa 10 MB).')
        if values.in_place:
            # Reference the video where it sits; nothing is written to the source mount.
            return create_in_place(values.name,video,raw)
        try:
            # Copy into application data through the same validated upload pipeline.
            # A read-only source mount is sufficient and original files are never changed.
            with video.open('rb') as v:
                return create(values.name,UploadFile(filename=video.name,file=v),
                              UploadFile(filename=srt.name,file=io.BytesIO(raw)))
        except PermissionError as exc:
            raise ValueError('Không có quyền đọc file nguồn.') from exc

    app.include_router(router)
