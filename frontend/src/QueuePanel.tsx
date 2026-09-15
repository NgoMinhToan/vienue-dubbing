import React,{useEffect,useState} from 'react';
type Item={id:string;project:string;project_name:string;version:number;revision:number;kind:string;status:string;done:number;total:number;message:string;file?:string};
async function request<T>(url:string,method='GET',data?:unknown):Promise<T>{const r=await fetch('/api'+url,{method,headers:{'Content-Type':'application/json'},body:data?JSON.stringify(data):undefined});const v=await r.json();if(!r.ok)throw Error(v.detail);return v;}
export default function QueuePanel({onEdit,onRefresh}:{onEdit:(id:string)=>void;onRefresh:()=>void}){
  const [items,setItems]=useState<Item[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const load=()=>request<Item[]>('/queue').then(setItems).catch(e=>setError(e.message));
  useEffect(()=>{let alive=true;const refresh=()=>request<Item[]>('/queue').then(v=>{if(alive)setItems(v);}).catch(e=>{if(alive)setError(e.message);});void refresh();const timer=setInterval(refresh,2000);return()=>{alive=false;clearInterval(timer);};},[]);
  async function act(work:()=>Promise<void>){setBusy(true);setError('');try{await work();await load();onRefresh();}catch(e){setError(String(e));}finally{setBusy(false);}}
  const labels:Record<string,string>={waiting:'Chờ bắt đầu',queued:'Chờ worker',running:'Đang xử lý',complete:'Hoàn thành',cancelled:'Đã hủy',error:'Lỗi'};
  return <section className="queue-panel"><div className="library-filters"><h2>Hàng đợi phiên bản</h2><button disabled={busy||!items.some(j=>j.status==='waiting')} onClick={()=>act(async()=>{await request('/queue/start','POST');})}>Bắt đầu hàng đợi</button></div><p>Thêm vào hàng đợi giữ bản chờ. Bắt đầu để chạy tuần tự; mỗi phiên bản giữ riêng lời, giọng, mốc và tùy chọn xuất.</p>{error&&<p role="alert">{error}</p>}{!items.length&&<p>Chưa có phiên bản.</p>}
    {items.map(j=><article className="voice-card" key={j.id}><div><strong>{j.project_name} · Phiên bản {j.version} · {j.kind.toUpperCase()}</strong><p>{labels[j.status]||j.status} · {j.done}/{j.total} câu</p><small>{j.message}</small></div>
      {['waiting','error','cancelled'].includes(j.status)&&<button disabled={busy} onClick={()=>act(async()=>{await request('/queue/'+j.id+'/start','POST');})}>{j.status==='waiting'?'Bắt đầu':'Thử lại'}</button>}
      {['waiting','queued'].includes(j.status)&&<button disabled={busy} onClick={()=>act(async()=>{if(!confirm('Gỡ phiên bản khỏi hàng đợi và khôi phục nội dung về dự án gốc? Các chỉnh sửa hiện tại của dự án sẽ được thay bằng bản này.'))return;const p=await request<{revision:number}>('/projects/'+j.project);await request('/queue/'+j.id+'/edit','POST',{revision:p.revision});onEdit(j.project);})}>Chỉnh sửa</button>}
      {['waiting','queued','running'].includes(j.status)&&<button disabled={busy} onClick={()=>act(async()=>{await request('/jobs/'+j.id+'/cancel','POST');})}>Dừng</button>}
      <button disabled={busy || j.status==='running'} title={j.status==='running' ? 'Dừng tác vụ và chờ kết thúc trước khi xóa' : 'Xóa phiên bản khỏi hàng đợi'} onClick={()=>act(async()=>{if(!confirm('Xóa phiên bản này khỏi hàng đợi và xóa file xuất của phiên bản? Dự án gốc và các phiên bản khác được giữ nguyên.'))return;await request('/queue/'+j.id,'DELETE');})}>Xóa khỏi hàng đợi</button>
      {j.status==='complete' &&j.file&&<a className="download" href={'/api/projects/'+j.project+'/files/'+j.file+'?download=true'}>Tải {j.kind.toUpperCase()}</a>}
    </article>)}
  </section>;
}
