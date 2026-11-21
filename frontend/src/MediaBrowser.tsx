import React,{useEffect,useState} from 'react';
import {ChevronUp, FileText, FileVideo, Folder, Home} from 'lucide-react';
type Entry={name:string;path:string;directory:boolean;size:number|null};
type Listing={root:string;path:string;entries:Entry[];next_offset:number|null};

function formatSize(bytes:number){
  if(bytes<1024)return `${bytes} B`;
  if(bytes<1024**2)return `${(bytes/1024).toFixed(1)} KB`;
  if(bytes<1024**3)return `${(bytes/1024**2).toFixed(1)} MB`;
  return `${(bytes/1024**3).toFixed(2)} GB`;
}

export default function MediaBrowser({onChange,onlyVideo=false}:{onChange:(video:string,srt:string)=>void;onlyVideo?:boolean}){
  const [listing,setListing]=useState<Listing|null>(null),[video,setVideo]=useState(''),[srt,setSrt]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  async function browse(path='',offset=0){setBusy(true);setError('');try{const r=await fetch('/api/media?'+new URLSearchParams({path,offset:String(offset)}));const data=await r.json();if(!r.ok)throw Error(data.detail);setListing(data);}catch(e){setError(String(e));}finally{setBusy(false);}}
  useEffect(()=>{onChange('','');void browse();},[]);
  function choose(path:string){if(!onlyVideo&&path.toLowerCase().endsWith('.srt')){setSrt(path);onChange(video,path);}else{setVideo(path);onChange(path,srt);}}
  const entries=(listing?.entries||[]).filter(e=>e.directory||!onlyVideo||!e.name.toLowerCase().endsWith('.srt'));
  return <div className="media-browser">
    {error&&<p role="alert">{error}</p>}
    <small>Thư mục trên máy chạy server: {listing?.root}</small>
    <div className="media-actions">
      <button type="button" disabled={busy} onClick={()=>browse()}><Home size={14}/>Thư mục gốc</button>
      <button type="button" disabled={busy||!listing||listing.path==='.'} onClick={()=>browse(listing!.path.split('/').slice(0,-1).join('/'))}><ChevronUp size={14}/>Lên một cấp</button>
    </div>
    <p className="media-path">{listing?.path}</p>
    <div className="media-entries">
      {entries.map(e=><button type="button" disabled={busy} key={e.path} className={e.path===video||e.path===srt?'selected':''} onClick={()=>e.directory?browse(e.path):choose(e.path)}>
        {e.directory?<Folder size={16}/>:e.name.toLowerCase().endsWith('.srt')?<FileText size={16}/>:<FileVideo size={16}/>}
        <span className="media-name">{e.name}</span>
        {e.size!==null&&<span className="media-size">{formatSize(e.size)}</span>}
      </button>)}
      {entries.length===0&&<p>Không có video/SRT hoặc thư mục con.</p>}
    </div>
    {listing?.next_offset!==null&&listing&&<button type="button" disabled={busy} onClick={()=>browse(listing.path,listing.next_offset!)}>Trang tiếp</button>}
    <p className="media-picked"><FileVideo size={14}/>Video: {video||'Chưa chọn'}</p>
    {!onlyVideo&&<p className="media-picked"><FileText size={14}/>SRT: {srt||'Chưa chọn'}</p>}
  </div>;
}
