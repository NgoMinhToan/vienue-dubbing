import React, { useEffect, useState } from "react";

import {Play, Headphones, Pencil, Star, LoaderCircle} from "lucide-react";

type Voice = {id:string; revision:number; name:string; description:string; gender:string; region:string; style:string; tags:string[]; favorite:boolean; sample_text:string};
async function request<T>(url:string, body?:unknown):Promise<T> {
  const r=await fetch('/api/library'+url, body ? {method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)} : undefined);
  const value=await r.json(); if(!r.ok) throw Error(value.detail || r.statusText); return value;
}
export default function VoiceLibrary() {
  const [voices,setVoices]=useState<Voice[]>([]), [draft,setDraft]=useState<Voice|null>(null);
  const [search,setSearch]=useState(''), [favorite,setFavorite]=useState(false), [error,setError]=useState('');
  const [filters,setFilters]=useState({gender:'',region:'',style:''});
  const [sample,setSample]=useState<{id:string;status:string;message?:string}|null>(null);
  const [saving,setSaving]=useState(false), [requesting,setRequesting]=useState(false);
  const [listening,setListening]=useState<Voice|null>(null);
  useEffect(()=>{request<Voice[]>('/voices').then(setVoices).catch(e=>setError(e.message));},[]);
  useEffect(()=>{
    if(!sample || !['queued','running'].includes(sample.status)) return;
    let alive=true;
    const timer=setInterval(()=>request<typeof sample>('/samples/'+sample.id).then(v=>{if(alive)setSample(v);}).catch(e=>{if(alive){setError(e.message);setSample(null);}}),1000);
    return ()=>{alive=false;clearInterval(timer);};
  },[sample?.id,sample?.status]);
  async function save(v:Voice) {
    setSaving(true);setError('');
    try {const saved=await request<Voice>('/voices/'+encodeURIComponent(v.id),v);setVoices(all=>all.map(x=>x.id===saved.id?saved:x));setDraft(null);}
    catch(e){setError(String(e));} finally {setSaving(false);}
  }
  async function listen(id:string) {
    setError('');setRequesting(true);setSample(null);setListening(voices.find(v=>v.id===id)||null);
    try {const r=await fetch('/api/library/voices/'+encodeURIComponent(id)+'/sample',{method:'POST'});const s=await r.json();if(!r.ok)throw Error(s.detail);setSample(s);}
    catch(e){setError(String(e));} finally {setRequesting(false);}
  }
  const waiting=requesting || !!sample && ['queued','running'].includes(sample.status);
  const visible=voices.filter(v=>(!favorite||v.favorite)&&Object.entries(filters).every(([k,value])=>!value||v[k as keyof typeof filters]===value)&&[v.name,v.id,v.description,...v.tags].join(' ').toLocaleLowerCase().includes(search.toLocaleLowerCase()));
  return <section className="library-page">
    <h1>Giọng nói <small>{voices.length} giọng cục bộ</small></h1>
    <p>Tên và thẻ lưu trên máy. ID giọng dùng trong dự án được giữ nguyên.</p>
    {error&&<div role="alert" className="error">{error}</div>}
    <input aria-label="Tìm giọng" placeholder="Tìm tên, mô tả hoặc thẻ…" value={search} onChange={e=>setSearch(e.target.value)}/>
    <div className="library-filters">{(['gender','region','style'] as const).map((key,i)=><label key={key}>{['Giới tính','Vùng miền','Phong cách'][i]}<select value={filters[key]} onChange={e=>setFilters({...filters,[key]:e.target.value})}><option value="">Tất cả</option>{[...new Set(voices.map(v=>v[key]).filter(Boolean))].map(v=><option key={v}>{v}</option>)}</select></label>)}
    <label><input type="checkbox" checked={favorite} onChange={e=>setFavorite(e.target.checked)}/> Chỉ yêu thích</label></div>
    <div className="voice-listener">
      <div className="listener-heading"><span className="listener-icon"><Headphones size={22}/></span><div><small>NGHE THỬ GIỌNG</small><h2>{listening?.name || 'Chọn một giọng để nghe'}</h2></div>{waiting&&<LoaderCircle className="loading-icon" size={20}/>}</div>
      <p className="sample-quote">{listening?.sample_text || 'Bấm biểu tượng phát bên cạnh giọng. Mẫu nghe sử dụng từ điển phát âm đã lưu.'}</p>
      {waiting&&<p role="status">{sample?.status==='running'?'Đang tạo mẫu giọng trên CPU…':'Đang chờ tạo mẫu giọng…'}</p>}
      {sample?.status==='failed'&&<p role="alert">{sample.message}</p>}
      {sample?.status==='complete'&&<audio aria-label={'Nghe mẫu '+listening?.name} key={sample.id} controls autoPlay src={'/api/library/samples/'+sample.id+'/audio'}/>}
    </div>
    <p>{visible.length} / {voices.length} giọng</p>
    {visible.map(v=><article className={"voice-card voice-library-card"+(listening?.id===v.id?" listening":"")} key={v.id}><button className="voice-play" aria-label={"Nghe mẫu "+v.name} title={"Nghe mẫu "+v.name} disabled={waiting} onClick={()=>listen(v.id)}><Play size={18}/></button><div><strong>{v.name}</strong><small>{v.id}</small><p>{v.description}</p><small>{[v.gender,v.region,v.style,...v.tags].filter(Boolean).join(' · ')}</small></div><button aria-label={'Yêu thích '+v.name} aria-pressed={v.favorite} disabled={saving} onClick={()=>save({...v,favorite:!v.favorite})}><Star size={18} fill={v.favorite?'currentColor':'none'}/></button><button aria-label={"Sửa "+v.name} onClick={()=>setDraft({...v})}><Pencil size={15}/>Sửa</button></article>)}
    {draft&&<div className="modal-backdrop"><form className="library-dialog" onSubmit={e=>{e.preventDefault();save(draft);}}><h2>Sửa thông tin giọng</h2><small>ID: {draft.id}</small>{(['name','description','gender','region','style','sample_text'] as const).map((key,i)=><label key={key}>{['Tên hiển thị','Mô tả','Giới tính','Vùng miền','Phong cách','Câu mẫu'][i]}<input required={key==='name'||key==='sample_text'} maxLength={key==='sample_text'?500:key==='description'?1000:100} value={draft[key]} onChange={e=>setDraft({...draft,[key]:e.target.value})}/></label>)}<label>Thẻ (ngăn cách bởi dấu phẩy)<input value={draft.tags.join(', ')} onChange={e=>setDraft({...draft,tags:e.target.value.split(',').map(t=>t.trim())})}/></label><div><button type="button" disabled={saving} onClick={()=>setDraft(null)}>Hủy</button><button className="primary" disabled={saving}>Lưu thông tin</button></div></form></div>}
  </section>;
}
