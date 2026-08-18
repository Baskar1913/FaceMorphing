"use client";

import { ChangeEvent, DragEvent, useEffect, useRef, useState } from "react";

type Kind = "video" | "source" | "target";
type Upload = { file: File | null; url: string };
type Job = { status: string; processed: number; total: number; matched: number; message: string; output?: string };
const API = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
const emptyUpload: Upload = { file: null, url: "" };
const emptyJob: Job = { status: "idle", processed: 0, total: 0, matched: 0, message: "Add all three files to begin." };

function Logo() {
  return <div className="brand-mark" aria-hidden="true"><span className="face face-left" /><span className="face face-right" /><span className="spark">✦</span></div>;
}

function UploadCard({ kind, title, copy, accept, value, onFile }: { kind: Kind; title: string; copy: string; accept: string; value: Upload; onFile: (file: File) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const receive = (file?: File) => file && onFile(file);
  return (
    <article className={`upload-card ${kind}-card ${value.file ? "has-file" : ""} ${drag ? "dragging" : ""}`}
      onDragOver={(e: DragEvent) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
      onDrop={(e: DragEvent) => { e.preventDefault(); setDrag(false); receive(e.dataTransfer.files[0]); }}>
      <div className="card-head"><span className="file-icon">{kind === "video" ? "▶" : kind === "source" ? "✦" : "◎"}</span><div><h3>{title}</h3><p>{copy}</p></div></div>
      <div className="preview-shell">
        {value.url ? kind === "video" ? <video key={value.url} src={value.url} controls playsInline preload="metadata">Your browser cannot play this video.</video> :
          // eslint-disable-next-line @next/next/no-img-element
          <img src={value.url} alt={`${title} preview`} />
          : <button className="empty-preview" type="button" onClick={() => input.current?.click()}><span className="upload-arrow">↑</span><strong>Drop file here</strong><small>or click to browse</small></button>}
      </div>
      <div className="file-row"><span className="file-name">{value.file ? value.file.name : kind === "video" ? "MP4, MOV or WebM" : "JPG, PNG or WebP"}</span><button type="button" onClick={() => input.current?.click()}>{value.file ? "Replace" : "Browse"}</button></div>
      <input ref={input} className="sr-only" type="file" accept={accept} onChange={(e: ChangeEvent<HTMLInputElement>) => receive(e.target.files?.[0])} />
    </article>
  );
}

export default function Home() {
  const [video, setVideo] = useState<Upload>(emptyUpload);
  const [source, setSource] = useState<Upload>(emptyUpload);
  const [target, setTarget] = useState<Upload>(emptyUpload);
  const [consent, setConsent] = useState(false);
  const [job, setJob] = useState<Job>(emptyJob);
  const [jobId, setJobId] = useState("");
  const running = ["uploading", "queued", "processing", "finalizing"].includes(job.status);
  const ready = Boolean(video.file && source.file && target.file && consent && !running);
  const percent = job.total ? Math.min(job.status === "completed" ? 100 : 99, Math.round(job.processed / job.total * 100)) : 0;
  const outputUrl = job.status === "completed" && jobId ? `${API}/api/jobs/${jobId}/output` : "";
  const downloadUrl = job.status === "completed" && jobId ? `${API}/api/jobs/${jobId}/download` : "";

  function assign(kind: Kind, file: File) {
    const next = { file, url: URL.createObjectURL(file) };
    const setter = kind === "video" ? setVideo : kind === "source" ? setSource : setTarget;
    setter(previous => { if (previous.url) URL.revokeObjectURL(previous.url); return next; });
    if (["completed", "failed"].includes(job.status)) { setJob(emptyJob); setJobId(""); }
  }

  useEffect(() => {
    if (!jobId) return;
    let active = true;
    let timer = 0;
    const poll = async () => {
      try {
        const response = await fetch(`${API}/api/jobs/${jobId}`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Unable to read progress.");
        if (!active) return;
        setJob({ status: data.status, processed: data.processed_frames || 0, total: data.total_frames || 0, matched: data.matched_frames || 0, message: data.message || "Processing video..." });
        if (!["completed", "failed"].includes(data.status)) timer = window.setTimeout(poll, 1000);
      } catch (error) {
        if (active) setJob(current => ({ ...current, status: "failed", message: error instanceof Error ? error.message : "Connection failed." }));
      }
    };
    poll();
    return () => { active = false; window.clearTimeout(timer); };
  }, [jobId]);

  async function start() {
    if (!video.file || !source.file || !target.file || !consent) return;
    const form = new FormData(); form.append("video", video.file); form.append("source_face", source.file); form.append("target_face", target.file); form.append("consent", "true");
    setJob({ ...emptyJob, status: "uploading", message: "Uploading your files..." });
    try {
      const response = await fetch(`${API}/api/jobs`, { method: "POST", body: form });
      const data = await response.json(); if (!response.ok) throw new Error(data.detail || "Could not start the job.");
      setJobId(data.job_id); setJob({ ...emptyJob, status: "queued", message: "Files received. Preparing AI models..." });
    } catch (error) { setJob({ ...emptyJob, status: "failed", message: error instanceof Error ? error.message : "Upload failed." }); }
  }

  return <main>
    <nav className="nav-wrap"><a className="brand" href="#top"><Logo /><span><strong>FaceMorph</strong><small>STUDIO</small></span></a><div className="nav-meta"><span className="online-dot" /> AI engine ready <a href="#how">How it works</a></div></nav>
    <section className="hero" id="top"><div className="orb orb-one" /><div className="orb orb-two" />
      <div className="hero-content"><div className="eyebrow"><span>✦</span> Identity-aware video editing</div><h1>Change one face.<br /><em>Keep every moment.</em></h1><p>Upload a video, the new source face, and a reference photo of the person to replace. Our AI follows only the selected identity—frame by frame.</p><div className="hero-pills"><span>◎ Specific-person matching</span><span>◈ Original audio preserved</span><span>⌁ Local AI backend</span></div></div>
      <div className="hero-visual" aria-hidden="true"><div className="portrait-card portrait-a"><span>01</span><div className="silhouette" /></div><div className="morph-line"><i /><b>✦</b><i /></div><div className="portrait-card portrait-b"><span>02</span><div className="silhouette alternate" /></div></div>
    </section>
    <section className="workspace"><header className="section-heading"><div><span className="step-number">01</span><p>PREPARE YOUR FILES</p></div><h2>Build your morphing job</h2><p>Three files are all you need. Preview each one before starting.</p></header>
      <div className="upload-grid"><UploadCard kind="video" title="Original video" copy="The scene you want to transform" accept="video/mp4,video/quicktime,video/webm" value={video} onFile={f => assign("video", f)} /><UploadCard kind="source" title="Source face" copy="The new identity to apply" accept="image/jpeg,image/png,image/webp" value={source} onFile={f => assign("source", f)} /><UploadCard kind="target" title="Target person" copy="Who should change in the video" accept="image/jpeg,image/png,image/webp" value={target} onFile={f => assign("target", f)} /></div>
      <label className="consent-row"><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} /><span className="custom-check">✓</span><span>I confirm that I have permission from the people shown and will use this tool lawfully.</span></label>
      <button className="primary-action" disabled={!ready} onClick={start}><span>{running ? "Processing video" : "Start face morphing"}</span><b>{running ? "•••" : "→"}</b></button>
      <section className={`status-panel ${job.status}`} aria-live="polite"><div className="status-top"><div><span>PROCESS STATUS</span><h3>{job.status === "completed" ? "Your video is ready" : job.status === "failed" ? "Something needs attention" : job.message}</h3></div><strong>{job.status === "completed" ? 100 : percent}%</strong></div><div className="progress-track"><span style={{ width: `${job.status === "completed" ? 100 : percent}%` }} /></div><div className="frame-stats"><span><b>{job.processed.toLocaleString()}</b> frames processed</span><span><b>{job.matched.toLocaleString()}</b> target matches</span><span><b>{job.total.toLocaleString()}</b> total frames</span></div></section>
      <section className={`result-panel ${outputUrl ? "result-ready" : "result-waiting"}`}><div className="result-copy"><span>02</span><div><p>FINAL OUTPUT</p><h2>{outputUrl ? "Transformation complete" : "Your finished video will appear here"}</h2></div></div>{outputUrl ? <video key={outputUrl} className="result-video" controls playsInline preload="metadata" src={outputUrl}>Your browser cannot play this video.</video> : <div className="result-placeholder"><span>▶</span><p>{running ? "Processing is still running…" : "Complete a face-morphing job to unlock the final video."}</p></div>}<div className="result-actions"><p>{outputUrl ? "Original audio preserved · MP4 output" : "Player and download become available at 100% completion"}</p>{downloadUrl ? <a href={downloadUrl}>Download final video <span>↓</span></a> : <span className="download-disabled">Download final video <b>↓</b></span>}</div></section>
    </section>
    <section className="how-section" id="how"><header className="section-heading compact"><div><span className="step-number">03</span><p>UNDER THE HOOD</p></div><h2>Precise by design</h2></header><div className="process-grid"><article><span>01</span><i>◎</i><h3>Detect</h3><p>Buffalo_L finds every face and maps facial landmarks.</p></article><article><span>02</span><i>⌁</i><h3>Identify</h3><p>Recognition embeddings locate only your target person.</p></article><article><span>03</span><i>✦</i><h3>Morph</h3><p>InSwapper applies the source identity to matched frames.</p></article><article><span>04</span><i>▶</i><h3>Finish</h3><p>FFmpeg restores the original audio and delivers the MP4.</p></article></div></section>
    <footer><div className="brand"><Logo /><span><strong>FaceMorph</strong><small>STUDIO</small></span></div><p>Consent-based AI video editing · React, InsightFace &amp; FFmpeg</p></footer>
  </main>;
}
