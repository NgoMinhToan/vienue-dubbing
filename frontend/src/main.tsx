import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { useVirtualizer } from "@tanstack/react-virtual";
import {
  AudioLines,
  Film,
  Settings,
  Plus,
  ArrowLeft,
  Download,
  Play,
  RotateCcw,
  Trash2,
  Upload,
  Check,
  Cpu,
  X,
  Square,
  Undo2,
  Redo2,
  FolderOpen,
} from "lucide-react";
import "./style.css";

type Cue = {
  id: string;
  start: number;
  end: number;
  text: string;
  voice: string | null;
  speed: number | null;
  ready?: boolean;
  audio?: string;
  fit?: { speed: number; duration: number; overflow: number };
};
type Project = {
  proxy_file?: string | null;
  last_job?: Job | null;
  id: string;
  revision: number;
  name: string;
  voice: string;
  speed: number;
  auto_fit: boolean;
  fit_limit: number;
  background: string;
  audio_index: number | null;
  cues: Cue[];
  video_file: string;
  video_name: string;
  media: {
    duration: number;
    audio_tracks: {
      index: number;
      title: string;
      language: string;
      channels: number;
    }[];
  };
};
type Job = {
  id: string;
  status: string;
  message: string;
  done: number;
  total: number;
  kind: string;
  revision: number;
  file?: string;
  preview?: string;
  warnings: { cue: number; seconds: number }[];
};
type Summary = {
  id: string;
  name: string;
  count: number;
  updated: string;
  video_name: string;
};
type Health = {
  model: string;
  backend: string;
  tools: Record<string, string | null>;
};
const backgrounds = [
  ["duck", "Nhỏ lại, hạ thêm khi lồng tiếng nói"],
  ["original_duck", "Giữ nguyên, chỉ hạ khi lồng tiếng nói"],
  ["quiet", "Rất nhỏ"],
  ["off", "Tắt âm gốc"],
];
async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch("/api" + url, init);
  if (!res.ok) {
    const e = await res.json().catch(() => ({ detail: res.statusText }));
    throw Error(
      typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail),
    );
  }
  return res.json();
}
const json = (method: string, data: unknown) => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(data),
});
const stamp = (s: number) =>
  `${Math.floor(s / 60)}:${(s % 60).toFixed(2).padStart(5, "0")}`;
const active = (j: Job | null) =>
  !!j && ["queued", "running"].includes(j.status);

function App() {
  const [list, setList] = useState<Summary[]>([]),
    [project, setProject] = useState<Project | null>(null),
    [voices, setVoices] = useState<{ id: string; description: string }[]>([]),
    [health, setHealth] = useState<Health | null>(null);
  const [page, setPage] = useState("projects"),
    [create, setCreate] = useState(false),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [dirty, setDirty] = useState(false),
    [job, setJob] = useState<Job | null>(null),
    [menu, setMenu] = useState(false),
    [selected, setSelected] = useState(""),
    [time, setTime] = useState(0),
    [zoom, setZoom] = useState(1),
    [preview, setPreview] = useState(false);
  const [history, setHistory] = useState<Project[]>([]),
    [future, setFuture] = useState<Project[]>([]);
  const video = useRef<HTMLVideoElement>(null),
    audio = useRef<HTMLAudioElement>(null),
    scroller = useRef<HTMLDivElement>(null);
  const latest = useRef(project);
  const dirtyRef = useRef(dirty);
  const saving = useRef<Promise<Project | null> | null>(null);
  const oneShot = useRef<HTMLAudioElement | null>(null);
  const playhead = useRef<HTMLDivElement>(null);
  const [videoFailed, setVideoFailed] = useState(false);
  const replaceVideo = useRef<HTMLInputElement>(null);
  const replaceSrt = useRef<HTMLInputElement>(null);
  latest.current = project;
  dirtyRef.current = dirty;
  const virtual = useVirtualizer({
    count: project?.cues.length || 0,
    getScrollElement: () => scroller.current,
    estimateSize: () => 192,
    overscan: 4,
  });
  const loadList = () =>
    api<Summary[]>("/projects")
      .then(setList)
      .catch((e) => setError(e.message));
  useEffect(() => {
    loadList();
    api<typeof voices>("/voices")
      .then(setVoices)
      .catch((e) => setError(e.message));
    const ping = () =>
      api<Health>("/health")
        .then(setHealth)
        .catch((e) => setError(e.message));
    ping();
    const id = setInterval(ping, 5000);
    return () => clearInterval(id);
  }, []);
  useEffect(() => {
    if (!job || !active(job)) return;
    const id = setInterval(() => {
      api<Job>("/jobs/" + job.id)
        .then(async (next) => {
          setJob(next);
          if ((next.status === "complete" || (next.kind === "generate" && next.status === "running")) && project && !dirtyRef.current) {
            const p = await api<Project>("/projects/" + project.id);
            if (!dirtyRef.current && latest.current?.id === p.id) setProject(p);
          }
        })
        .catch((e) => setError(e.message));
    }, 1000);
    return () => clearInterval(id);
  }, [job?.id, job?.status, project?.id, dirty]);
  useEffect(() => {
    if (page !== "editor" || !project) return;
    let frame = 0;
    let lastLabel = 0;
    const tick = (now: number) => {
      const t = video.current?.currentTime || 0;
      if (playhead.current) playhead.current.style.left = `${Math.min(100, t / project.media.duration * 100)}%`;
      if (now - lastLabel >= 100) { setTime(t); lastLabel = now; }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [page, project?.id, project?.media.duration]);
  useEffect(() => {
    const before = (e: BeforeUnloadEvent) => {
      if (dirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", before);
    return () => window.removeEventListener("beforeunload", before);
  }, [dirty]);
  useEffect(() => {
    if (!dirty || page !== 'editor') return;
    const id = setTimeout(() => {save().catch(e => setError(e.message));}, 1200);
    return () => clearTimeout(id);
  }, [project, dirty, page]);
  function mutate(change: Partial<Project>) {
    if (!project) return;
    setHistory((h) => [...h.slice(-39), project]);
    setFuture([]);
    const cues = change.voice !== undefined ? project.cues.map(c => c.voice ? c : {...c, ready: false}) : project.cues;
    setProject({ ...project, cues, ...change });
    setDirty(true);
    setPreview(false);
    audio.current?.pause();
  }
  function editCue(id: string, change: Partial<Cue>) {
    if (project)
      mutate({
        cues: project.cues.map((c) =>
          c.id === id
            ? {
                ...c,
                ...change,
                ready:
                  change.text !== undefined || change.voice !== undefined
                    ? false
                    : c.ready,
              }
            : c,
        ),
      });
  }
  async function save(): Promise<Project | null> {
    if (saving.current) { await saving.current; return save(); }
    const snapshot = latest.current;
    if (!snapshot || !dirtyRef.current) return snapshot;
    const work = (async () => {
      const p = await api<Project>('/projects/' + snapshot.id, json('PUT', snapshot));
      if (latest.current === snapshot) {
        latest.current = p; dirtyRef.current = false;
        setProject(p); setDirty(false);
      } else if (latest.current?.id === p.id) {
        const merged = {...latest.current, revision:p.revision};
        latest.current = merged; setProject(merged);
      }
      return p;
    })();
    saving.current = work;
    try { await work; } finally { saving.current = null; }
    return dirtyRef.current ? save() : latest.current;
  }
  async function run(kind: string, cueId?: string, allow = false) {
    try {
      setError("");
      setBusy(true);
      const p = await save();
      if (!p) return;
      setPreview(false);
      setJob(
        await api<Job>(
          `/projects/${p.id}/jobs`,
          json("POST", { kind, cue_id: cueId, allow_overlap: allow }),
        ),
      );
      setMenu(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function open(id: string) {
    try {
      if (dirty && !confirm("Bỏ các thay đổi chưa lưu?")) return;
      const p = await api<Project>("/projects/" + id);
      setProject(p);
      setPage("editor");
      setDirty(false);
      setHistory([]);
      setFuture([]);
      setJob(p.last_job || null);
      setSelected("");
      setPreview(false);
      setVideoFailed(false);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  function file(path: string, download = false) {
    return `/api/projects/${project?.id}/files/${path}${download ? "?download=true" : ""}`;
  }
  async function replaceSource(kind: "video" | "srt", chosen?: File) {
    if (!chosen) return;
    if (kind === "srt" && !confirm("Thay SRT sẽ thay toàn bộ danh sách câu hiện tại. Tiếp tục?")) return;
    setBusy(true);
    try {
      const p = await save();
      if (!p) return;
      const body = new FormData();
      body.append("revision", String(p.revision));
      body.append(kind, chosen);
      const next = await api<Project>(`/projects/${p.id}/source`, {method:"POST", body});
      setProject(next); setHistory([]); setFuture([]); setJob(null); setPreview(false); setVideoFailed(false);
      audio.current?.pause();
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  function seek(t: number, id?: string) {
    if (video.current) video.current.currentTime = t;
    if (audio.current && preview) audio.current.currentTime = t;
    setTime(t);
    if (id) setSelected(id);
  }
  async function listen(c: Cue) {
    if (!c.audio || dirty) return;
    oneShot.current?.pause();
    const a = new Audio(file(c.audio));
    oneShot.current = a;
    a.preservesPitch = true;
    a.playbackRate = c.fit?.speed || c.speed || project?.speed || 1;
    await a.play().catch((e) => setError(e.message));
  }
  function undo() {
    if (!project || !history.length) return;
    setFuture((f) => [project, ...f]);
    setProject({ ...history.at(-1)!, revision: project.revision });
    setHistory((h) => h.slice(0, -1));
    setDirty(true);
  }
  function redo() {
    if (!project || !future.length) return;
    setHistory((h) => [...h, project]);
    setProject({ ...future[0], revision: project.revision });
    setFuture((f) => f.slice(1));
    setDirty(true);
  }
  const validOutput =
    job?.status === "complete" &&
    ["mp3", "mkv"].includes(job.kind) &&
    job.revision === project?.revision &&
    !dirty &&
    job.file;
  const readyCount = project?.cues.filter(c => c.ready).length || 0;
  const totalCount = project?.cues.length || 0;
  useEffect(() => {
    if (!validOutput) { setPreview(false); audio.current?.pause(); }
  }, [validOutput]);
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">
            <AudioLines size={22} />
          </span>
          <strong>
            VieNeu<span>DUBBING</span>
          </strong>
        </div>
        <div className="nav-label">KHÔNG GIAN LÀM VIỆC</div>
        <button
          className={page !== "settings" ? "nav selected" : "nav"}
          onClick={() => {
            if (!dirty || confirm("Bỏ các thay đổi chưa lưu?")) {
              setPage("projects");
              setDirty(false);
              loadList();
            }
          }}
        >
          <Film size={17} />
          Lồng tiếng
        </button>
        <button
          className={page === "settings" ? "nav selected" : "nav"}
          onClick={() => setPage("settings")}
        >
          <Settings size={17} />
          Cài đặt
        </button>
        <div className="side-bottom">
          <div className="local-badge">
            <span /> Xử lý trên máy
          </div>
          <div className="cpu">
            <Cpu size={18} />
            <div>
              CPU · v3 Turbo<small>{health?.model || "Đang kết nối…"}</small>
            </div>
          </div>
          <small className="version">WebUI · phiên bản phát triển 0.1</small>
        </div>
      </aside>
      <main>
        {error && (
          <div className="error" role="alert">
            {error}
            <button aria-label="Đóng lỗi" onClick={() => setError("")}>
              <X size={16} />
            </button>
          </div>
        )}
        {page === "projects" && (
          <div className="project-page">
            <div className="page-heading">
              <div>
                <div className="eyebrow">VIDEO + PHỤ ĐỀ</div>
                <h1>
                  Lồng tiếng video <span className="badge">TRÊN MÁY</span>
                </h1>
                <p>
                  Giữ từng nhịp thoại. Chọn giọng, chỉnh câu và tạo bản lồng
                  tiếng của bạn.
                </p>
              </div>
              <button className="primary" onClick={() => setCreate(true)}>
                <Plus size={17} />
                Dự án lồng tiếng
              </button>
            </div>
            <div className="section-title">
              DỰ ÁN CỦA BẠN <span>{list.length}</span>
            </div>
            {!list.length ? (
              <div className="empty">
                <div className="empty-icon">
                  <Film size={34} />
                </div>
                <h2>Bắt đầu với video của bạn</h2>
                <p>Chọn một video và file phụ đề .srt đã có lời thoại.</p>
                <button className="primary" onClick={() => setCreate(true)}>
                  <Plus size={16} />
                  Tạo dự án đầu tiên
                </button>
                <div className="format-note">
                  MP4, MKV, MOV, AVI, WEBM · SRT UTF-8
                </div>
              </div>
            ) : (
              <div className="project-grid">
                {list.map((p) => (
                  <article className="project-card" key={p.id}>
                    <button className="project-open" onClick={() => open(p.id)}>
                      <div className="card-cover">
                        <Film size={32} />
                        <span>{p.count} câu</span>
                      </div>
                      <h3>{p.name}</h3>
                      <p>{p.video_name}</p>
                      <div className="card-footer">
                        <span>
                          Mở dự án{" "}
                          <ArrowLeft
                            size={13}
                            style={{ transform: "rotate(180deg)" }}
                          />
                        </span>
                        <small>
                          {new Date(p.updated).toLocaleDateString("vi-VN")}
                        </small>
                      </div>
                    </button>
                    <button
                      className="delete-project"
                      aria-label={"Xóa " + p.name}
                      onClick={async () => {
                        if (confirm("Xóa dự án và toàn bộ âm thanh đã tạo?")) {
                          try {
                            await api("/projects/" + p.id, {
                              method: "DELETE",
                            });
                            loadList();
                          } catch (e) {
                            setError((e as Error).message);
                          }
                        }
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </article>
                ))}
              </div>
            )}
          </div>
        )}
        {page === "settings" && (
          <div className="settings-page">
            <h1>Cài đặt</h1>
            <p>Giọng đọc và dữ liệu được xử lý trên máy chạy ứng dụng.</p>
            <section className="panel">
              <h3>Mô hình và bộ xử lý</h3>
              <div className="setting-choice">
                <Check size={18} />
                <div>
                  <strong>v3 Turbo · CPU</strong>
                  <p>ONNX · fp32 · 48 kHz</p>
                </div>
                <span className="badge">MẶC ĐỊNH</span>
              </div>
              <p>{health?.model}</p>
              <small>
                Model được tải khi tạo giọng lần đầu. Sau khi tải đủ tài nguyên,
                có thể dùng offline.
              </small>
            </section>
            <section className="panel">
              <h3>Công cụ âm thanh & video</h3>
              {Object.entries(health?.tools || {}).map(([k, v]) => (
                <div className="tool" key={k}>
                  <strong>{k}</strong>
                  <span className={v ? "good" : "warning"}>
                    {v ? "Sẵn sàng" : "Chưa cài"}
                  </span>
                </div>
              ))}
              <small>
                FFmpeg xử lý âm thanh; MKVToolNix ghép video với hai track.
              </small>
            </section>
          </div>
        )}
        {page === "editor" && project && (
          <div className="editor">
            <header className="toolbar">
              <button
                className="back"
                onClick={() => {
                  if (!dirty || confirm("Bỏ thay đổi chưa lưu?")) {
                    setDirty(false);
                    setPage("projects");
                    loadList();
                  }
                }}
              >
                <ArrowLeft size={16} />
                Dự án
              </button>
              <input
                aria-label="Tên dự án"
                className="title-input"
                value={project.name}
                onChange={(e) => mutate({ name: e.target.value })}
              />
              <span className="badge">TRÊN MÁY</span>
              <div className="toolbar-actions">
                <button
                  title="Hoàn tác"
                  aria-label="Hoàn tác"
                  disabled={!history.length}
                  onClick={undo}
                >
                  <Undo2 size={16} />
                </button>
                <button
                  title="Làm lại"
                  aria-label="Làm lại"
                  disabled={!future.length}
                  onClick={redo}
                >
                  <Redo2 size={16} />
                </button>
                <button
                  disabled={!dirty || busy}
                  onClick={() => save().catch((e) => setError(e.message))}
                >
                  {dirty ? "Lưu thay đổi" : "Đã lưu"}
                </button>
                <button
                  className="generate"
                  disabled={busy || active(job) || readyCount === totalCount}
                  onClick={() => run("generate")}
                >
                  <AudioLines size={16} />
                  Tạo giọng tất cả ({readyCount}/{totalCount} đã tạo)
                </button>
                <div className="export-wrap">
                  <button className="primary" onClick={() => setMenu(!menu)}>
                    <Download size={16} />
                    Tải về
                  </button>
                  {menu && (
                    <div className="export-menu">
                      <label>
                        Âm gốc trong bản lồng tiếng
                        <select
                          value={project.background}
                          onChange={(e) =>
                            mutate({ background: e.target.value })
                          }
                        >
                          {backgrounds.map(([v, t]) => (
                            <option key={v} value={v}>
                              {t}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button
                        disabled={busy || active(job)}
                        onClick={() => run("mp3")}
                      >
                        <AudioLines size={18} />
                        <span>
                          Chỉ âm thanh<small>MP3 · bản phối lồng tiếng</small>
                        </span>
                      </button>
                      <button
                        disabled={
                          busy || active(job) || project.audio_index === null
                        }
                        onClick={() => run("mkv")}
                      >
                        <Film size={18} />
                        <span>
                          Video MKV<small>Âm gốc + lồng tiếng · 2 track</small>
                        </span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </header>
            <div className="editor-body">
              <section className="preview-column">
                <video
                  ref={video}
                  controls
                    src={file(project.proxy_file || project.video_file)}
                    onLoadedData={() => setVideoFailed(false)}
                  muted={preview}
                  onTimeUpdate={() => {
                    const t = video.current?.currentTime || 0;
                    setTime(t);
                    if (
                      preview &&
                      audio.current &&
                      Math.abs(audio.current.currentTime - t) > 0.15
                    )
                      audio.current.currentTime = t;
                  }}
                  onPlay={() => {
                    if (preview) {
                      audio.current!.currentTime = video.current!.currentTime;
                      audio.current?.play().catch((e) => setError(e.message));
                    }
                  }}
                  onPause={() => audio.current?.pause()}
                  onSeeked={() => {
                    if (preview && audio.current)
                      audio.current.currentTime = video.current!.currentTime;
                  }}
                    onError={() => setVideoFailed(true)}
                />
                <button
                  className={"preview-button" + (preview ? " is-dubbed" : "")}
                  aria-pressed={preview}
                    disabled={busy || active(job)}
                    onClick={() => {
                      if (preview) { setPreview(false); audio.current?.pause(); return; }
                      if (!validOutput) { void run("mp3"); return; }
                    setPreview(true);
                    if (video.current && audio.current) {
                      audio.current.currentTime = video.current.currentTime;
                      void audio.current.play().catch(e => setError(e.message));
                      void video.current.play().catch(e => setError(e.message));
                    }
                  }}
                >
                  <Play size={15} />
                  {preview ? "Đang xem bản lồng tiếng · Chuyển về bản gốc" : "Xem trước bản lồng tiếng"}
                </button>
                <p className={"playback-mode" + (preview ? " is-dubbed" : "")} role="status">
                  {preview ? "Âm thanh: bản lồng tiếng đã trộn" : "Âm thanh: bản gốc của video"}
                </p>
                <audio
                  ref={audio}
                  src={
                    validOutput && job?.preview ? file(job.preview) : undefined
                  }
                />
                <p className="hint">
                  Bấm vào một câu hoặc timeline để tua tới đúng chỗ.
                </p>
                {videoFailed && <button disabled={busy || active(job)} onClick={() => void run("proxy")}>Tạo video tương thích để xem trước</button>}
                <div className="source-info">
                  <Film size={16} />
                  <span>{project.video_name}</span>
                  <small>{stamp(project.media.duration)}</small>
                </div>
                <div className="speed-row">
                  <button disabled={busy || active(job)} onClick={() => replaceVideo.current?.click()}>Thay video</button>
                  <button disabled={busy || active(job)} onClick={() => replaceSrt.current?.click()}>Nhập SRT khác</button>
                  <input hidden type="file" ref={replaceVideo} accept=".mp4,.mkv,.avi,.mov,.webm,.m4v" onChange={e => {void replaceSource("video", e.target.files?.[0]); e.target.value="";}} />
                  <input hidden type="file" ref={replaceSrt} accept=".srt" onChange={e => {void replaceSource("srt", e.target.files?.[0]); e.target.value="";}} />
                </div>
                <label>
                  Giọng chung
                  <select
                    value={project.voice}
                    onChange={(e) => mutate({ voice: e.target.value })}
                  >
                    {voices.map((v) => (
                      <option key={v.id}>{v.id}</option>
                    ))}
                  </select>
                </label>
                <button disabled={busy || active(job)} onClick={() => void run("sample")}>Nghe mẫu giọng chung</button>
                {job?.kind === "sample" && job.status === "complete" && job.revision === project.revision && job.file && <audio controls src={file(job.file)} />}
                <div className="speed-row">
                  <label>Tốc độ chung</label>
                  <input
                    aria-label="Tốc độ chung"
                    type="number"
                    min="0.5"
                    max="3"
                    step="0.1"
                    value={project.speed}
                    onChange={(e) => mutate({ speed: Number(e.target.value) })}
                  />
                  <span>×</span>
                </div>
                <section className="fit-panel">
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={project.auto_fit}
                      onChange={(e) => mutate({ auto_fit: e.target.checked })}
                    />
                    Tự khớp khung thời gian
                  </label>
                  <p>
                    Dùng khoảng nghỉ sau câu. Tăng tốc khi cần để không lấn câu
                    tiếp theo.
                  </p>
                  <label>
                    Tăng thêm tối đa
                    <select
                      value={project.fit_limit}
                      onChange={(e) =>
                        mutate({ fit_limit: Number(e.target.value) })
                      }
                    >
                      {[1, 1.2, 1.4, 1.6, 2].map((v) => (
                        <option key={v} value={v}>
                          {v}×
                        </option>
                      ))}
                    </select>
                  </label>
                </section>
                <label>
                  Âm thanh gốc
                  <select
                    disabled={!project.media.audio_tracks.length}
                    value={project.audio_index ?? ""}
                    onChange={(e) =>
                      mutate({ audio_index: Number(e.target.value) })
                    }
                  >
                    {!project.media.audio_tracks.length && (
                      <option value="">Video không có âm thanh</option>
                    )}
                    {project.media.audio_tracks.map((a) => (
                      <option value={a.index} key={a.index}>
                        {a.title} · {a.language} · {a.channels} kênh
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Mức âm gốc
                  <select
                    value={project.background}
                    onChange={(e) => mutate({ background: e.target.value })}
                  >
                    {backgrounds.map(([v, t]) => (
                      <option key={v} value={v}>
                        {t}
                      </option>
                    ))}
                  </select>
                </label>
              </section>
              <section className="cue-column">
                <div className="cue-heading">
                  <span>
                    LỜI THOẠI <b>{project.cues.length}</b>
                  </span>
                  <button
                    onClick={() => {
                      const c: Cue = {
                        id: crypto.randomUUID(),
                        start: time,
                        end: time + 2,
                        text: "Câu thoại mới",
                        voice: null,
                        speed: null,
                      };
                      mutate({
                        cues: [...project.cues, c].sort(
                          (a, b) => a.start - b.start,
                        ),
                      });
                    }}
                  >
                    <Plus size={14} />
                    Thêm câu
                  </button>
                </div>
                <div className="cue-scroll" ref={scroller}>
                  <div
                    style={{
                      height: virtual.getTotalSize(),
                      position: "relative",
                    }}
                  >
                    {virtual.getVirtualItems().map((v) => {
                      const c = project.cues[v.index];
                      return (
                        <article
                          className={
                            "cue " + (selected === c.id ? "focused" : "")
                          }
                          key={c.id}
                          style={{
                            position: "absolute",
                            top: 0,
                            left: 0,
                            width: "100%",
                            height: 184,
                            transform: `translateY(${v.start}px)`,
                          }}
                          onClick={() => setSelected(c.id)}
                        >
                          <div className="cue-meta">
                            <button onClick={() => seek(c.start, c.id)}>
                              #{v.index + 1}{" "}
                              <span>
                                {stamp(c.start)} → {stamp(c.end)}
                              </span>
                            </button>
                            <span
                              className={c.ready ? "status good" : "status"}
                            >
                              {c.ready ? "đã tạo" : "chưa tạo"}
                            </span>
                            {c.fit && (
                              <span
                                className={
                                  "status fit " +
                                  (c.fit.overflow > 0.02 ? "warning" : "good")
                                }
                              >
                                {c.fit.overflow > 0.02
                                  ? `tràn ${c.fit.overflow.toFixed(1)}s`
                                  : "vừa khung"}
                              </span>
                            )}
                          </div>
                          <textarea
                            aria-label={"Lời câu " + (v.index + 1)}
                            value={c.text}
                            onChange={(e) =>
                              editCue(c.id, { text: e.target.value })
                            }
                          />
                          <div className="cue-actions">
                            <select
                              aria-label={"Giọng câu " + (v.index + 1)}
                              value={c.voice || ""}
                              onChange={(e) =>
                                editCue(c.id, { voice: e.target.value || null })
                              }
                            >
                              <option value="">Giọng chung</option>
                              {voices.map((v) => (
                                <option key={v.id}>{v.id}</option>
                              ))}
                            </select>
                            <input
                              aria-label={"Tốc độ câu " + (v.index + 1)}
                              type="number"
                              min="0.5"
                              max="3"
                              step="0.1"
                              placeholder={String(project.speed)}
                              value={c.speed ?? ""}
                              onChange={(e) =>
                                editCue(c.id, {
                                  speed: e.target.value
                                    ? Number(e.target.value)
                                    : null,
                                })
                              }
                            />
                            <span>×</span>
                            <button
                              title="Xóa câu"
                              aria-label={"Xóa câu " + (v.index + 1)}
                              onClick={() =>
                                mutate({
                                  cues: project.cues.filter(
                                    (x) => x.id !== c.id,
                                  ),
                                })
                              }
                            >
                              <Trash2 size={14} />
                            </button>
                            <div className="spacer" />
                            <button
                              aria-label={"Nghe câu " + (v.index + 1)}
                              disabled={!c.ready || dirty}
                              onClick={() => listen(c)}
                            >
                              <Play size={14} />
                            </button>
                            <button
                              className="regenerate"
                              disabled={busy || active(job)}
                              onClick={() => run("generate", c.id)}
                            >
                              <RotateCcw size={13} />
                              Tạo lại
                            </button>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                </div>
              </section>
            </div>
            <div className="timeline">
              <div className="timeline-controls">
                <span>Thu phóng</span>
                <input
                  aria-label="Thu phóng timeline"
                  type="range"
                  min="1"
                  max="20"
                  value={zoom}
                  onChange={(e) => setZoom(Number(e.target.value))}
                />
                <span className="timecode">
                  {stamp(time)} / {stamp(project.media.duration)}
                </span>
              </div>
              <div className="timeline-scroll">
                <div
                  className="timeline-track"
                  style={{ width: `${zoom * 100}%` }}
                  onClick={(e) => {
                    const r = e.currentTarget.getBoundingClientRect();
                    seek(
                      ((e.clientX - r.left) / r.width) * project.media.duration,
                    );
                  }}
                >
                  {Array.from({ length: 11 }, (_, i) => (
                    <span
                      className="tick"
                      key={i}
                      style={{ left: `${i * 10}%` }}
                    >
                      {stamp((project.media.duration * i) / 10)}
                    </span>
                  ))}
                  {project.cues.map((c, i) => (
                    <button
                      key={c.id}
                      className={
                        "timeline-cue " + (selected === c.id ? "selected" : "")
                      }
                      style={{
                        left: `${(c.start / project.media.duration) * 100}%`,
                        width: `${Math.max(0.12, ((c.end - c.start) / project.media.duration) * 100)}%`,
                      }}
                      title={c.text}
                      onClick={(e) => {
                        e.stopPropagation();
                        seek(c.start, c.id);
                        virtual.scrollToIndex(i, { align: "center" });
                      }}
                    >
                      #{i + 1} {c.text}
                    </button>
                  ))}
                  <div
                    ref={playhead}
                    className="playhead"
                  />
                </div>
              </div>
            </div>
            {job && (
              <div
                className={
                  "job-bar " + (job.status === "error" ? "error-job" : "")
                }
              >
                <AudioLines size={18} />
                <span>{job.message}</span>
                {active(job) && (
                  <>
                    <div className="smooth-progress" role="progressbar" aria-label="Tiến trình tạo giọng" aria-valuemin={0} aria-valuemax={job.total || 1} aria-valuenow={job.done}>
                      <div style={{transform: `scaleX(${Math.min(1, job.done / (job.total || 1))})`}} />
                    </div>
                    <small>
                      {job.done}/{job.total}
                    </small>
                    <button
                      onClick={() =>
                        api("/jobs/" + job.id + "/cancel", { method: "POST" })
                      }
                    >
                      <Square size={13} />
                      Dừng
                    </button>
                  </>
                )}
                {job.status === "needs_confirmation" && (
                  <>
                    <span className="warning">
                      {job.warnings.length} câu · tối đa{" "}
                      {Math.max(...job.warnings.map((w) => w.seconds)).toFixed(
                        1,
                      )}
                      s
                    </span>
                    <button onClick={() => run(job.kind, undefined, true)}>
                      Chấp nhận chồng lời và xuất
                    </button>
                  </>
                )}
                {validOutput && (
                  <a className="download" href={file(job.file!, true)}>
                    <Download size={15} />
                    Tải {job.kind.toUpperCase()}
                  </a>
                )}
              </div>
            )}
          </div>
        )}
      </main>
      {create && (
        <div className="modal-overlay">
          <form
            className="modal"
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              setError("");
              try {
                const form = new FormData(e.currentTarget);
                const p = await api<Project>("/projects", {
                  method: "POST",
                  body: form,
                });
                setProject(p);
                setPage("editor");
                setCreate(false);
                setDirty(false);
                setJob(null);
              } catch (e) {
                setError((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <div className="modal-heading">
              <h2>Dự án lồng tiếng mới</h2>
              <button
                type="button"
                aria-label="Đóng"
                onClick={() => setCreate(false)}
              >
                <X size={20} />
              </button>
            </div>
            <p>Video và phụ đề được xử lý trên máy của bạn.</p>
            <label>
              Tên dự án
              <input
                name="name"
                defaultValue="Lồng tiếng mới"
                maxLength={200}
                required
              />
            </label>
            <label className="file-drop">
              <Upload size={24} />
              <strong>Chọn video</strong>
              <small>MP4, MKV, MOV, AVI, WEBM</small>
              <input
                name="video"
                type="file"
                accept=".mp4,.mkv,.mov,.avi,.webm,.m4v"
                required
              />
            </label>
            <label className="file-drop compact">
              <FolderOpen size={21} />
              <strong>Chọn phụ đề .srt</strong>
              <input name="srt" type="file" accept=".srt" required />
            </label>
            <div className="modal-footer">
              <button type="button" onClick={() => setCreate(false)}>
                Hủy
              </button>
              <button className="primary" disabled={busy}>
                {busy ? "Đang nhập dữ liệu…" : "Tạo dự án"}
                <ArrowLeft size={15} style={{ transform: "rotate(180deg)" }} />
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
