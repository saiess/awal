import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { api, ApiError, errorMessage, jsonRequest } from './api';
import type { ExportOptions, ExportRecord, Health, Job, Narrator, Project, ProjectSummary, Segment } from './types';

const terminal = (job: Job) => ['ready', 'failed', 'interrupted'].includes(job.status);
const duration = (seconds: number | null) => {
  const value = Math.round(seconds ?? 0);
  return `${Math.floor(value / 60)}:${String(value % 60).padStart(2, '0')}`;
};
const remember = (id: string | null) => {
  try { if (id) localStorage.setItem('narration-project', id); else localStorage.removeItem('narration-project'); }
  catch { /* Project files remain authoritative when browser storage is unavailable. */ }
};

function SectionCard({ section, index, saved, value, selected, locked, legacy, onText, onSelect, onSave, onRegenerate, projectId }: {
  section: Segment; index: number; saved: boolean; value: string; selected: boolean; locked: boolean; legacy: boolean;
  onText: (text: string) => void; onSelect: (selected: boolean) => void;
  onSave: () => void; onRegenerate: () => void; projectId?: string;
}) {
  const dirty = value !== (section.inference_text ?? section.text);
  const stale = !legacy && section.stale && Boolean(section.audio_path);
  const status = legacy ? (section.audio_path ? `Saved recording · ${duration(section.duration_seconds)}` : 'No saved recording')
    : dirty ? 'Unsaved text' : section.status === 'generating' ? 'Generating…' : stale ? 'Audio needs regeneration'
    : section.status === 'ready' ? `Ready · ${duration(section.duration_seconds)}` : section.status === 'failed' ? 'Failed — retry' : 'Pending';
  const audio = saved && section.audio_path ? `/api/projects/${projectId}/segments/${section.id}/audio?v=${section.version}` : undefined;
  return <article className="section-card" data-id={section.id}>
    <div className="section-top">
      <input className="section-select" type="checkbox" checked={selected} disabled={locked}
        aria-label={`Include section ${index + 1} in selected export`} onChange={event => onSelect(event.target.checked)} />
      <strong>{String(index + 1).padStart(2, '0')} / {section.text.length} characters</strong>
      <span className={`status ${stale ? 'stale' : section.status}`}>{status}</span>
    </div>
    <label><span className="sr-label">Section {index + 1} inference text</span>
      <textarea maxLength={600} rows={3} value={value} readOnly={!saved || legacy} disabled={locked}
        data-dirty={dirty ? 'true' : 'false'} onChange={event => onText(event.target.value)} />
    </label>
    {(section.inference_text || dirty) && <details><summary>Original script text</summary><p>{section.text}</p></details>}
    <p className="section-error" hidden={!section.error}>{section.error}</p>
    <div className="actions" hidden={!saved}>
      <audio controls preload="none" hidden={!audio} src={audio} aria-label={`Section ${index + 1} original audio`} />
      <button className="save-section" type="button" disabled={locked || legacy || !dirty} data-original={section.inference_text ?? section.text} onClick={onSave}>Save inference text</button>
      <button className="regenerate-section" type="button" disabled={locked || legacy} onClick={onRegenerate}>Regenerate section</button>
    </div>
  </article>;
}

function NarratorPanel({ narrator, locked, onUpload, onTranscript, canEditTranscript }: {
  narrator: Narrator | null; locked: boolean; canEditTranscript: boolean; onUpload: (data: FormData) => Promise<boolean>; onTranscript: (text: string) => Promise<boolean>;
}) {
  const [open, setOpen] = useState(false);
  const [label, setLabel] = useState('Voice C');
  const [file, setFile] = useState<File | null>(null);
  const [rights, setRights] = useState(false);
  const [transcript, setTranscript] = useState('');
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || !rights) return;
    const data = new FormData();
    data.append('label', label); data.append('rights_confirmed', String(rights)); data.append('reference_audio', file); data.append('reference_transcript', transcript);
    if (await onUpload(data)) setOpen(false);
  }
  return <section className="narrator panel" aria-label="Narrator">
    <div className="voice-icon">{narrator?.label.charAt(0) ?? 'N'}</div>
    <div className="voice-info"><strong id="voice-label">{narrator?.label ?? 'Add your narrator'}</strong>
      <span id="voice-description">{narrator ? 'English · saved reference' : 'Upload an authorized reference to get started.'}</span>
    </div>
    <audio id="reference-audio" controls preload="none" aria-label="Saved voice reference" hidden={!narrator}
      src={narrator ? `/api/narrators/${narrator.id}/reference` : undefined} />
    {narrator && !narrator.reference_transcript && canEditTranscript && <form className="transcript-form" onSubmit={event => { event.preventDefault(); void onTranscript(transcript); }}>
      <label>Exact words in this saved reference<textarea required maxLength={4000} value={transcript} disabled={locked} onChange={event => setTranscript(event.target.value)} /></label>
      <button disabled={locked || !transcript.trim()}>Save reference transcript</button>
    </form>}
    <details id="voice-settings" open={open} onToggle={event => setOpen(event.currentTarget.open)}><summary>{narrator ? 'Change voice' : 'Add voice'}</summary>
      <form id="reference-form" onSubmit={event => { void submit(event); }}>
        <p>New projects use the new reference. Existing projects retain their saved narrator.</p>
        <label>Voice label<input id="reference-label" maxLength={120} value={label} required disabled={locked} onChange={event => setLabel(event.target.value)} /></label>
        <label>Clear 10–30-second recording<input id="reference-file" type="file" accept=".wav,.ogg,.opus,.flac,.mp3,.m4a" required disabled={locked} onChange={event => setFile(event.target.files?.[0] ?? null)} /></label>
        <label>Exact words spoken in the reference<textarea id="reference-transcript" maxLength={4000} required value={transcript} disabled={locked} onChange={event => setTranscript(event.target.value)} /></label>
        <label className="check"><input id="reference-rights" type="checkbox" checked={rights} required disabled={locked} onChange={event => setRights(event.target.checked)} />I own this recording or have permission to clone and publish the voice commercially.</label>
        <button type="submit" disabled={locked}>Save reference for new projects</button>
      </form>
    </details>
  </section>;
}

export default function App() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [narrator, setNarrator] = useState<Narrator | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [title, setTitle] = useState('');
  const [script, setScript] = useState('');
  const [preview, setPreview] = useState<string[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [job, setJob] = useState<Job | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [operation, setOperation] = useState(false);
  const operationRef = useRef(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [healthText, setHealthText] = useState('Checking local engine…');
  const [speed, setSpeed] = useState('1.10');
  const [processed, setProcessed] = useState(true);
  const [enhance, setEnhance] = useState(false);
  const [gap, setGap] = useState('0.12');
  const [trimTrailing, setTrimTrailing] = useState(true);
  const [master, setMaster] = useState<ExportRecord | null>(null);
  const legacy = Boolean(project && project.engine_id !== 'qwen3-tts-0.6b-base');
  const busy = Boolean(job && !terminal(job));
  const locked = initializing || operation || busy;
  const hasDirty = project?.segments.some(section => drafts[section.id] !== undefined && drafts[section.id] !== (section.inference_text ?? section.text)) ?? false;

  function adoptProject(value: Project) {
    setProject(value); setTitle(value.title); setScript(value.script); setPreview([]); setDrafts({});
    setSelected(new Set(value.segments.map(section => section.id)));
    setSpeed(value.export_settings.speed.toFixed(2)); setProcessed(value.export_settings.processed);
    setTrimTrailing(value.export_settings.trim_trailing_silence ?? false); setEnhance(value.export_settings.enhance); setGap(String(value.export_settings.gap_seconds));
    setMaster(value.exports.at(-1) ?? null); setJob(null); remember(value.id);
  }

  useEffect(() => {
    const controller = new AbortController();
    async function init() {
      try {
        const options = { signal: controller.signal };
        const [voices, list, health] = await Promise.all([
          api<Narrator[]>('/api/narrators', options), api<ProjectSummary[]>('/api/projects', options), api<Health>('/api/health', options),
        ]);
        if (controller.signal.aborted) return;
        setNarrator(voices[0] ?? null); setProjects(list);
        setHealthText(health.gpu_available ? 'NVIDIA GPU available · Qwen loads on first generation' : 'CUDA unavailable · run check.bat before generating');
        let last: string | null = null;
        try { last = localStorage.getItem('narration-project'); } catch { /* Optional browser preference. */ }
        const id = health.active_job?.project_id ?? (list.some(item => item.id === last) ? last : null);
        if (id) {
          const value = await api<Project>(`/api/projects/${id}`, options);
          if (controller.signal.aborted) return;
          adoptProject(value);
        } else remember(null);
        if (health.active_job) setJob(health.active_job);
      } catch (cause) { if (!controller.signal.aborted) setError(errorMessage(cause)); }
      finally { if (!controller.signal.aborted) setInitializing(false); }
    }
    void init();
    return () => controller.abort();
  }, []);

  const jobId = job?.id;
  useEffect(() => {
    if (!jobId || !job || terminal(job)) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const options = { signal: controller.signal };
        const value = await api<Job>(`/api/jobs/${jobId}`, options);
        const saved = await api<Project>(`/api/projects/${value.project_id}`, options);
        if (controller.signal.aborted) return;
        setError(''); setJob(value); setProject(saved);
        if (terminal(value)) {
          if (value.error) setError(value.error);
          else setNotice('All generated sections are saved. Preview them or build your master export.');
          setProjects(await api<ProjectSummary[]>('/api/projects', options));
          return;
        }
      } catch (cause) {
        if (controller.signal.aborted) return;
        if (cause instanceof ApiError && cause.status === 404) {
          setJob(previous => previous ? { ...previous, status: 'interrupted', error: errorMessage(cause) } : null);
          setError('The server restarted. Reopen your saved project and generate missing sections.');
          return;
        }
        setError(`${errorMessage(cause)} Retrying generation status…`);
      }
      if (!controller.signal.aborted) timer = setTimeout(() => { void poll(); }, 1000);
    }
    void poll();
    return () => { controller.abort(); clearTimeout(timer); };
    // A new job owns a new polling loop. Server snapshots must not create extra loops.
  }, [jobId]);

  async function action(work: () => Promise<void>) {
    if (operationRef.current || busy || initializing) return false;
    operationRef.current = true; setOperation(true); setError(''); setNotice('');
    try { await work(); return true; } catch (cause) { setError(errorMessage(cause)); return false; }
    finally { operationRef.current = false; setOperation(false); }
  }

  function discardAllowed() { return !hasDirty || window.confirm('Discard unsaved section edits? Saved audio stays in your project.'); }
  async function openProject(id: string) {
    if (!discardAllowed()) return;
    adoptProject(await api<Project>(`/api/projects/${id}`));
    setProjects(await api<ProjectSummary[]>('/api/projects'));
  }
  async function newProject() {
    if (!discardAllowed()) return;
    setProject(null); setTitle(''); setScript(''); setPreview([]); setDrafts({}); setSelected(new Set()); setMaster(null); setJob(null); remember(null);
    setProjects(await api<ProjectSummary[]>('/api/projects'));
  }
  async function saveSection(section: Segment): Promise<Project> {
    if (!project) throw new Error('Open a saved project first.');
    const text = drafts[section.id] ?? section.inference_text ?? section.text;
    const updated = await jsonRequest<Project>(`/api/projects/${project.id}/segments/${section.id}`, 'PATCH', { inference_text: text === section.text ? null : text });
    setProject(updated);
    setDrafts(previous => { const next = { ...previous }; delete next[section.id]; return next; });
    return updated;
  }
  async function generate() {
    if (hasDirty) throw new Error('Save your section edits before generating.');
    let saved = project;
    if (!saved) {
      if (!title.trim()) throw new Error('Give this project a title.');
      if (!narrator?.reference_transcript) throw new Error('Save an authorized reference and its exact transcript first.');
      const result = await jsonRequest<{ segments: string[] }>('/api/segment', 'POST', { script });
      if (!window.confirm(`Create this project and generate ${result.segments.length} sections?`)) return;
      saved = await jsonRequest<Project>('/api/projects', 'POST', { title, script, narrator_id: narrator.id });
      adoptProject(saved);
      setProjects(await api<ProjectSummary[]>('/api/projects'));
    }
    setJob(await jsonRequest<Job>(`/api/projects/${saved.id}/generate`, 'POST', { only_missing_or_stale: true }));
  }
  async function regenerate(section: Segment) {
    if (!project) return;
    if ((drafts[section.id] ?? section.inference_text ?? section.text) !== (section.inference_text ?? section.text)) await saveSection(section);
    setJob(await jsonRequest<Job>(`/api/projects/${project.id}/segments/${section.id}/regenerate`, 'POST', {}));
  }
  async function makeExport(format: 'wav' | 'mp3', sections = false, download = true) {
    if (!project) return;
    if (hasDirty) throw new Error('Save section text and regenerate changed audio before exporting.');
    if (sections && !selected.size) throw new Error('Select at least one section.');
    if (!speed || !gap || !Number.isFinite(Number(speed)) || !Number.isFinite(Number(gap))) throw new Error('Enter a valid speed and boundary gap.');
    const options: ExportOptions = { format, include_segments: sections, segment_ids: sections ? [...selected] : null,
      speed: Number(speed), processed, trim_trailing_silence: trimTrailing, enhance: processed && enhance, gap_seconds: Number(gap) };
    const record = await jsonRequest<ExportRecord>(`/api/projects/${project.id}/exports`, 'POST', options);
    setMaster(record); setProject(await api<Project>(`/api/projects/${project.id}`));
    if (download) {
      const link = document.createElement('a');
      link.href = `/api/projects/${project.id}/exports/${record.id}/download?download=true`; link.download = '';
      document.body.append(link); link.click(); link.remove();
    }
    setNotice('Export saved. Raw section recordings are unchanged.');
  }

  const segments: Segment[] = project?.segments ?? preview.map((text, order) => ({ id: `preview-${order}`, order, text,
    status: 'pending', stale: true, audio_path: null, version: 0, duration_seconds: null, error: null }));
  const allSelected = segments.length > 0 && segments.every(section => selected.has(section.id));
  function selectSection(id: string, checked: boolean) {
    setSelected(previous => { const next = new Set(previous); if (checked) next.add(id); else next.delete(id); return next; });
  }
  const activeIndex = project?.segments.findIndex(section => section.id === job?.active_segment_id) ?? -1;
  const progressLabel = job && terminal(job) ? job.status === 'ready' ? 'Narration saved.' : 'Generation needs attention.'
    : job?.status === 'queued' ? 'Preparing narration…' : activeIndex >= 0 ? `Generating section ${activeIndex + 1}…` : 'Loading narrator on the GPU…';

  return <>
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">N</span><div>Local Narration<small>Personal workspace</small></div></div>
      <button id="new-project" className="primary wide" disabled={locked} onClick={() => { void action(newProject); }}><span aria-hidden="true">+</span>New project</button>
      <div className="sidebar-label"><span>Your projects</span><span className="project-count" aria-label={`${projects.length} saved projects`}>{projects.length}</span></div>
      <nav id="projects" aria-label="Saved projects">
        {!projects.length && <p className="muted">{initializing ? 'Loading projects…' : 'Your saved projects will appear here.'}</p>}
        {projects.map(item => <button key={item.id} className={project?.id === item.id ? 'active' : ''} data-project-id={item.id}
          aria-current={project?.id === item.id ? 'page' : undefined} title={item.title}
          disabled={locked} onClick={() => { void action(() => openProject(item.id)); }}>
          <span className="project-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" /><path d="M14 3v6h6M8 13h8M8 17h5" /></svg></span>
          <span className="project-copy"><span className="project-name">{item.title}</span><small>{item.ready_count} / {item.segment_count} sections ready</small></span>
        </button>)}
      </nav>
      <div id="health" className="health" role="status">{healthText}</div>
    </aside>
    <main>
      <header><div><p className="eyebrow">NARRATION</p><h1 id="heading">{project?.title ?? 'New project'}</h1></div><span className="local-badge"><span className="local-dot" aria-hidden="true" />Local</span></header>
      <div id="error" role="alert" hidden={!error}>{error}</div><div id="notice" role="status" hidden={!notice}>{notice}</div>
      {legacy && <p className="muted" role="status">This Chatterbox project keeps its saved recordings. Preview and export remain available. Create a new Qwen project to generate narration.</p>}
      <NarratorPanel narrator={project?.narrator ?? narrator} locked={locked} canEditTranscript={!project} onTranscript={text => action(async () => {
        if (!narrator) return;
        setNarrator(await jsonRequest<Narrator>(`/api/narrators/${narrator.id}/transcript`, 'PATCH', { transcript: text }));
        setNotice('Reference transcript saved for new projects.');
      })} onUpload={data =>
        action(async () => {
          setNarrator(await api<Narrator>('/api/narrators', { method: 'POST', body: data }));
          setNotice('Reference saved for new projects. Existing projects keep their saved voice.');
        })} />
      <section className="panel" id="script-panel" hidden={Boolean(project)}>
        <div className="section-heading"><div><p className="eyebrow">WRITE</p><h2>Script</h2></div><span id="script-count" className="muted">{script.length.toLocaleString()} characters</span></div>
        <label>Project title<input id="title" maxLength={120} placeholder="Give your narration a title" value={title} readOnly={Boolean(project)} disabled={locked} onChange={event => setTitle(event.target.value)} required /></label>
        <label>English script<textarea id="script" rows={9} maxLength={100000} value={script} readOnly={Boolean(project)} disabled={locked} onChange={event => setScript(event.target.value)} placeholder="Paste or write your English script here..." /></label>
        <div className="actions">
          <button id="preview-script" disabled={locked || Boolean(project)} onClick={() => { void action(async () => {
            const result = await jsonRequest<{ segments: string[] }>('/api/segment', 'POST', { script });
            setPreview(result.segments); setSelected(new Set(result.segments.map((_, index) => `preview-${index}`)));
          }); }}>Preview sections</button>
          {!project && <button id="generate" className="primary" disabled={locked || !narrator?.reference_transcript} onClick={() => { void action(generate); }}>Create & generate</button>}
          <span id="script-hint" className="muted">Your original audio is always kept.</span>
        </div>
      </section>
      <section id="progress-panel" className="panel" hidden={!job} aria-label="Generation progress">
        <div className="section-heading"><strong id="progress-label">{progressLabel}</strong><span id="progress-count">{job ? `${job.done_segments} / ${job.total_segments}` : ''}</span></div>
        <progress id="progress" max={Math.max(1, job?.total_segments ?? 1)} value={job?.done_segments ?? 0} />
        <p className="muted">Sections save as they finish. First generation loads the GPU model. Closing this tab does not stop the local server.</p>
      </section>
      <section id="sections-panel" className="panel" hidden={!project && !preview.length}>
        <div className="section-heading"><div><p className="eyebrow">REVIEW</p><h2>Sections</h2></div>
          {project && <button id="generate" className="primary" disabled={locked || legacy} onClick={() => { void action(generate); }}>Generate missing / changed</button>}
        </div>
        <div className="section-selection"><span id="section-count" className="muted">{segments.length} sections</span><label className="check"><input id="select-all" type="checkbox" checked={allSelected} disabled={locked} onChange={event => setSelected(new Set(event.target.checked ? segments.map(section => section.id) : []))} />Select all</label></div>
        <p className="muted">{legacy ? 'Preview and export the last saved recordings. Create a separate Qwen project for new narration.' : 'Correct inference text, save it, then regenerate just that section. Your original script is kept. Audio previews play the original 1.00× recording.'}</p>
        <div id="sections">{segments.map((section, index) => <SectionCard key={section.id} section={section} index={index}
          saved={Boolean(project)} value={drafts[section.id] ?? section.inference_text ?? section.text} selected={selected.has(section.id)} locked={locked} legacy={legacy} projectId={project?.id}
          onText={text => setDrafts(previous => ({ ...previous, [section.id]: text }))} onSelect={checked => selectSection(section.id, checked)}
          onSave={() => { void action(async () => { await saveSection(section); setNotice('Inference text saved. Original script and audio are preserved until you regenerate.'); }); }}
          onRegenerate={() => { void action(() => regenerate(section)); }} />)}</div>
      </section>
      <section id="export-panel" className="panel" hidden={!project}>
        <div className="section-heading"><div><p className="eyebrow">DOWNLOAD</p><h2>Export</h2></div><span id="export-info" className="muted">{operation ? 'Working…' : 'Raw recordings stay unchanged.'}</span></div>
        <div className="export-options">
          <label className="check"><input id="processed" type="checkbox" checked={processed} disabled={locked} onChange={event => setProcessed(event.target.checked)} />Apply export processing</label>
          <label>Playback speed (pitch preserved)<input id="speed" type="number" min="0.5" max="2" step="0.05" value={speed} disabled={locked || !processed} onChange={event => setSpeed(event.target.value)} /></label>
          <label>Minimum section gap (seconds)<input id="gap" type="number" min="0" max="0.5" step="0.01" value={gap} disabled={locked} onChange={event => setGap(event.target.value)} /></label>
          {!legacy && <label className="check"><input id="trim-trailing" type="checkbox" checked={trimTrailing} disabled={locked || !processed} onChange={event => setTrimTrailing(event.target.checked)} />Shorten excessive trailing silence (keep 0.35 seconds)</label>}
          <label className="check"><input id="enhance" type="checkbox" checked={enhance} disabled={locked || !processed} onChange={event => setEnhance(event.target.checked)} />Conservative volume adjustment</label>
        </div>
        <p className="muted">Turn off export processing for original speed. Existing pauses count toward the section gap.</p>
        <div className="actions">
          <button id="preview-master" disabled={locked} onClick={() => { void action(() => makeExport('wav', false, false)); }}>Preview master</button>
          <button id="export-wav" className="primary" disabled={locked} onClick={() => { void action(() => makeExport('wav')); }}>Export WAV</button>
          <button id="export-mp3" disabled={locked} onClick={() => { void action(() => makeExport('mp3')); }}>Export MP3</button>
          <button id="export-segments" disabled={locked} onClick={() => { void action(() => makeExport('wav', true)); }}>Selected sections (ZIP)</button>
        </div>
        <div id="master-panel" hidden={!master}>
          <label htmlFor="master-audio">Master preview</label>
          <audio id="master-audio" controls preload="metadata" src={master && project ? `/api/projects/${project.id}/exports/${master.id}/download?audio_only=true` : undefined} />
          <p id="master-caption" className="muted">{master ? `${duration(master.duration_seconds)} · ${master.options.processed ? master.effective_speed.toFixed(2) + '× processed' : '1.00× original speed'}${master.options.enhance ? ' · volume adjusted' : ''} · Saved export snapshot; regenerate changed sections and export again to update it.` : ''}</p>
        </div>
      </section>
      <footer>Saved on your computer.</footer>
    </main>
  </>;
}
