import React, {useEffect,useRef,useState} from 'react';
import {Trash2, Plus, ArrowRight} from 'lucide-react';
type Rule={source:string;target:string;whole_word:boolean;case_sensitive:boolean;enabled:boolean};
type Dictionary={version:1;revision:number;rules:Rule[]};
async function call<T>(url:string,method='GET',data?:unknown):Promise<T>{
  const r=await fetch('/api'+url,{method,headers:{'Content-Type':'application/json'},body:data?JSON.stringify(data):undefined});
  const v=await r.json();if(!r.ok)throw Error(typeof v.detail==='string'?v.detail:JSON.stringify(v.detail));return v;
}
export default function Pronunciation({active}:{active:boolean}){
  const [dictionary,setDictionary]=useState<Dictionary|null>(null),[dirty,setDirty]=useState(false),[busy,setBusy]=useState(false);
  const [text,setText]=useState('Bản VieNeu chạy trên CPU.'),[output,setOutput]=useState(''),[message,setMessage]=useState(''),[error,setError]=useState('');
  const input=useRef<HTMLInputElement>(null);

  useEffect(()=>{if(!dirty)return;const warn=(e:BeforeUnloadEvent)=>{e.preventDefault();e.returnValue='';};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn);},[dirty]);
  useEffect(()=>{call<Dictionary>('/dictionary').then(setDictionary).catch(e=>setError(e.message));},[]);
  function update(rules:Rule[]){if(dictionary){setDictionary({...dictionary,rules});setDirty(true);setOutput('');setMessage('');}}
  async function act(work:()=>Promise<void>){setBusy(true);setError('');setMessage('');try{await work();}catch(e){setError(String(e));}finally{setBusy(false);}}
  async function save(){if(!dictionary)return;const d=await call<Dictionary>('/dictionary','PUT',dictionary);setDictionary(d);setDirty(false);setMessage('Đã lưu. Luật áp dụng cho tất cả dự án và các lần tạo/nghe giọng tiếp theo.');}
  function download(){if(!dictionary)return;const url=URL.createObjectURL(new Blob([JSON.stringify(dictionary,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='pronunciation.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  return <section className="library-page dictionary-page"><h1>Từ điển phát âm</h1><p>Áp dụng chung cho lồng tiếng và nghe mẫu giọng. Chỉ đổi lời đọc, giữ nguyên văn bản hiển thị. Luật ở trên được ưu tiên khi trùng, kết quả không bị thay thế lần nữa.</p>
    {error&&<p role="alert" className="error">{error}</p>}{message&&<p role="status">{message}</p>}
    {dictionary&&<><div className="library-filters"><button disabled={busy||dictionary.rules.length>=500} onClick={()=>update([...dictionary.rules,{source:'',target:'',whole_word:true,case_sensitive:false,enabled:true}])}><Plus size={16}/>Thêm luật</button><button disabled={busy} onClick={()=>input.current?.click()}>Nhập JSON</button><button onClick={download}>Xuất JSON</button><button className="primary" disabled={!dirty||busy} onClick={()=>act(save)}>Lưu từ điển</button></div>
    <input hidden ref={input} type="file" accept=".json" onChange={e=>{const file=e.target.files?.[0];e.target.value='';if(file)void act(async()=>{if(file.size>1024*1024)throw Error('Tệp tối đa 1 MB.');const d=JSON.parse(await file.text());if(!Array.isArray(d.rules))throw Error('Thiếu danh sách rules.');const validated=await call<{rules:Rule[]}>('/dictionary/preview','POST',{...d,text:''});update(validated.rules);setMessage('Đã nhập để xem lại. Bấm Lưu từ điển để áp dụng.');});}}/>
    <div className="dictionary-rules">{!dictionary.rules.length && <p className="empty-rules">Chưa có luật. Thêm từ cần chỉnh cách đọc để bắt đầu.</p>}
    {dictionary.rules.map((r,i)=><div className={'rule-card pronunciation-rule'+(!r.enabled?' rule-disabled':'')} key={i}>
      <span className="rule-number">{String(i+1).padStart(2,'0')}</span>
      <label className="rule-field">Viết là<input aria-label={'Viết là '+(i+1)} placeholder="Ví dụ: CPU" value={r.source} maxLength={200} onChange={e=>update(dictionary.rules.map((x,j)=>j===i?{...x,source:e.target.value}:x))}/></label>
      <ArrowRight className="rule-arrow" size={18}/>
      <label className="rule-field">Đọc thành<input aria-label={'Đọc thành '+(i+1)} placeholder="Ví dụ: xi pi iu" value={r.target} maxLength={500} onChange={e=>update(dictionary.rules.map((x,j)=>j===i?{...x,target:e.target.value}:x))}/></label>
      <div className="rule-options">{(['whole_word','case_sensitive','enabled'] as const).map((k,j)=><label key={k}><input type="checkbox" checked={r[k]} onChange={e=>update(dictionary.rules.map((x,n)=>n===i?{...x,[k]:e.target.checked}:x))}/>{['Cả từ','Phân biệt hoa/thường','Bật luật'][j]}</label>)}</div>
      <button className="delete-rule" aria-label={'Xóa luật '+(i+1)} title="Xóa luật" onClick={()=>update(dictionary.rules.filter((_,j)=>i!==j))}><Trash2 size={18}/></button>
    </div>)}</div>
    <h2>Thử văn bản</h2><textarea aria-label="Văn bản thử phát âm" maxLength={10000} value={text} onChange={e=>{setText(e.target.value);setOutput('');}}/><button disabled={busy} onClick={()=>act(async()=>{const r=await call<{text:string}>('/dictionary/preview','POST',{...dictionary,text});setOutput(r.text);})}>Xem lời engine đọc</button><p className="spoken-preview">{output}</p>
</>}
  </section>;
}
