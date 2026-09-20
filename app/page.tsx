"use client";

import { ChangeEvent, DragEvent, FormEvent, useEffect, useRef, useState } from "react";
import {
  ArrowUp, BookOpen, Check, ChevronDown, FileImage, FileText, Files,
  Layers3, LoaderCircle, Menu, MessageSquareText, Plus, Search,
  ShieldCheck, Sparkles, Trash2, Upload, X,
} from "lucide-react";

type Source = { file: string; type: string; snippet: string; page?: number; slide?: number };
type Message = { id: string; role: "user" | "assistant"; content: string; sources?: Source[] };
type DocumentInfo = { name: string; type: string; size?: number; chunks?: number };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const starters = ["Summarise the key findings", "Create a study guide", "Compare the main concepts", "Generate five quiz questions"];
const initialMessages: Message[] = [{
  id: "welcome",
  role: "assistant",
  content: "Your workspace is ready. Add research papers, reports, slide decks, or images and I’ll answer with traceable references to the original material.",
}];

function fileIcon(type: string) {
  return ["png", "jpg", "jpeg", "image"].includes(type.toLowerCase()) ? FileImage : FileText;
}

function formatSize(bytes?: number) {
  if (!bytes) return "Document";
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function renderText(text: string) {
  return text.split("\n").map((line, index) => {
    const value = line.replace(/^#{1,4}\s*/, "").replace(/\*\*/g, "");
    if (!value.trim()) return <br key={index} />;
    if (/^#{1,4}\s/.test(line)) return <strong key={index} className="answer-heading">{value}</strong>;
    if (/^[-*]\s/.test(line)) return <span key={index} className="answer-list">{value.replace(/^[-*]\s/, "")}</span>;
    return <span key={index}>{value}</span>;
  });
}

export default function Home() {
  const picker = useRef<HTMLInputElement>(null);
  const end = useRef<HTMLDivElement>(null);
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [question, setQuestion] = useState("");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [asking, setAsking] = useState(false);
  const [status, setStatus] = useState<"checking" | "online" | "offline">("checking");
  const [notice, setNotice] = useState("");
  const [activeSources, setActiveSources] = useState<Source[] | null>(null);
  const [chunkCount, setChunkCount] = useState(0);

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((response) => response.ok ? response.json() : Promise.reject())
      .then((payload) => {
        const data = payload as { chunks?: number; documents?: DocumentInfo[] };
        setStatus("online"); setChunkCount(data.chunks ?? 0); setDocuments(data.documents ?? []);
      })
      .catch(() => setStatus("offline"));
  }, []);

  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [messages, asking]);
  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => setNotice(""), 4200);
    return () => window.clearTimeout(timeout);
  }, [notice]);

  async function processFiles(files: File[]) {
    const valid = files.filter((file) => /\.(pdf|docx|pptx|png|jpe?g)$/i.test(file.name));
    if (!valid.length) { setNotice("Choose a PDF, DOCX, PPTX, PNG, or JPG file."); return; }
    setProcessing(true);
    const optimistic = valid.map((file) => ({ name: file.name, type: file.name.split(".").pop() ?? "file", size: file.size }));
    setDocuments((current) => [...current, ...optimistic]);
    try {
      const body = new FormData();
      valid.forEach((file) => body.append("files", file));
      const response = await fetch(`${API_URL}/documents/process`, { method: "POST", body });
      const data = await response.json() as { detail?: string; documents?: DocumentInfo[]; chunks?: number };
      if (!response.ok) throw new Error(data.detail ?? "The documents could not be processed.");
      setDocuments(data.documents ?? optimistic); setChunkCount(data.chunks ?? 0); setStatus("online"); setUploadOpen(false);
      setNotice(`${valid.length} ${valid.length === 1 ? "document" : "documents"} indexed and ready.`);
    } catch (error) {
      setDocuments((current) => current.filter((item) => !optimistic.some((file) => file.name === item.name)));
      setStatus("offline"); setNotice(error instanceof Error ? error.message : "Could not reach the document service.");
    } finally { setProcessing(false); }
  }

  function selectFiles(event: ChangeEvent<HTMLInputElement>) {
    void processFiles(Array.from(event.target.files ?? [])); event.target.value = "";
  }

  function dropFiles(event: DragEvent<HTMLDivElement>) {
    event.preventDefault(); setDragging(false); void processFiles(Array.from(event.dataTransfer.files));
  }

  async function ask(event?: FormEvent) {
    event?.preventDefault();
    const prompt = question.trim();
    if (!prompt || asking) return;
    if (!chunkCount) { setUploadOpen(true); setNotice("Add at least one document before asking a question."); return; }
    setQuestion(""); setMessages((current) => [...current, { id: crypto.randomUUID(), role: "user", content: prompt }]); setAsking(true);
    try {
      const response = await fetch(`${API_URL}/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: prompt }) });
      const data = await response.json() as { detail?: string; answer: string; sources?: Source[] };
      if (!response.ok) throw new Error(data.detail ?? "The answer could not be generated.");
      setMessages((current) => [...current, { id: crypto.randomUUID(), role: "assistant", content: data.answer, sources: data.sources ?? [] }]);
    } catch (error) {
      setMessages((current) => [...current, { id: crypto.randomUUID(), role: "assistant", content: error instanceof Error ? error.message : "Something went wrong while generating the answer." }]);
    } finally { setAsking(false); }
  }

  async function clearWorkspace() {
    if (!documents.length) return;
    try {
      const response = await fetch(`${API_URL}/documents`, { method: "DELETE" });
      if (!response.ok) throw new Error();
      setDocuments([]); setChunkCount(0); setMessages(initialMessages); setNotice("Workspace cleared.");
    } catch { setNotice("The workspace could not be cleared."); }
  }

  const ready = chunkCount > 0;
  return (
    <main className="shell">
      <aside className={`sidebar ${mobileNav ? "sidebar-open" : ""}`}>
        <div className="brand-row"><a className="brand" href="#" aria-label="Lumen home"><span>L</span>LUMEN</a><button className="mobile-close" onClick={() => setMobileNav(false)} aria-label="Close navigation"><X /></button></div>
        <button className="new-session" onClick={() => setMessages(initialMessages)}><Plus /> New conversation <span>⌘ K</span></button>
        <nav className="primary-nav" aria-label="Workspace navigation">
          <button className="nav-item active"><MessageSquareText /> Ask Lumen <span>01</span></button>
          <button className="nav-item" onClick={() => setUploadOpen(true)}><Files /> Library <span>{String(documents.length).padStart(2, "0")}</span></button>
          <button className="nav-item"><BookOpen /> Notes <span>00</span></button>
        </nav>
        <div className="library-preview">
          <div className="sidebar-label"><span>Current library</span><button onClick={() => setUploadOpen(true)} aria-label="Add a document"><Plus /></button></div>
          {documents.length ? documents.slice(0, 4).map((document) => {
            const Icon = fileIcon(document.type);
            return <button className="mini-document" key={document.name} onClick={() => setUploadOpen(true)}><span className="mini-icon"><Icon /></span><span><strong>{document.name}</strong><small>{document.type.toUpperCase()} · {formatSize(document.size)}</small></span></button>;
          }) : <div className="empty-library"><Layers3 /><p>No sources yet</p><span>Your indexed files appear here.</span></div>}
          {documents.length > 4 && <button className="show-all" onClick={() => setUploadOpen(true)}>View all {documents.length} documents</button>}
        </div>
        <div className="privacy-card"><ShieldCheck /><div><strong>Private by design</strong><span>Your files stay in your workspace.</span></div></div>
        <div className="profile"><span className="avatar">HR</span><div><strong>Harsh Rathod</strong><span>Personal workspace</span></div><ChevronDown /></div>
      </aside>
      {mobileNav && <button className="scrim" aria-label="Close navigation" onClick={() => setMobileNav(false)} />}
      <section className="workspace">
        <header className="topbar">
          <button className="menu-button" onClick={() => setMobileNav(true)} aria-label="Open navigation"><Menu /></button>
          <div><span className="breadcrumb">WORKSPACE /</span> Research session</div>
          <div className="topbar-actions"><span className={`api-status ${status}`}><i />{status === "online" ? "AI online" : status === "offline" ? "Service offline" : "Connecting"}</span><button className="search-button" aria-label="Search"><Search /></button><button className="add-source" onClick={() => setUploadOpen(true)}><Plus /> Add sources</button></div>
        </header>
        <div className="conversation">
          <div className="conversation-head">
            <div className="overline"><span /> GROUNDED DOCUMENT INTELLIGENCE</div>
            <h1>Ask your research.<br /><em>Find the evidence.</em></h1>
            <p>Explore complex documents through one focused conversation. Every answer stays grounded in your uploaded sources.</p>
            <div className="workspace-stats"><span><strong>{String(documents.length).padStart(2, "0")}</strong> SOURCES</span><i /><span><strong>{chunkCount.toLocaleString()}</strong> INDEXED CHUNKS</span><i /><span className={ready ? "ready" : "waiting"}><b /> {ready ? "READY TO QUERY" : "AWAITING SOURCES"}</span></div>
          </div>
          <div className="thread">
            {messages.map((message) => <article className={`message ${message.role}`} key={message.id}>
              <div className="message-mark">{message.role === "assistant" ? <Sparkles /> : "HR"}</div>
              <div className="message-body"><div className="message-meta"><strong>{message.role === "assistant" ? "Lumen" : "You"}</strong><span>{message.role === "assistant" ? "DOCUMENT ASSISTANT" : "JUST NOW"}</span></div><div className="message-copy">{renderText(message.content)}</div>
                {!!message.sources?.length && <div className="source-strip"><span>ANSWER GROUNDED IN</span>{message.sources.slice(0, 3).map((source, index) => <button key={`${source.file}-${index}`} onClick={() => setActiveSources(message.sources!)}><FileText /> {source.file} <small>{source.page ? `P.${source.page}` : source.slide ? `S.${source.slide}` : source.type.toUpperCase()}</small></button>)}<button className="all-sources" onClick={() => setActiveSources(message.sources!)}>View evidence</button></div>}
              </div>
            </article>)}
            {asking && <article className="message assistant thinking"><div className="message-mark"><Sparkles /></div><div className="message-body"><div className="message-meta"><strong>Lumen</strong><span>SEARCHING SOURCES</span></div><div className="thinking-line"><i /><i /><i /></div></div></article>}
            <div ref={end} />
          </div>
          {messages.length === 1 && <div className="starters"><span>TRY A STARTER</span><div>{starters.map((starter) => <button key={starter} onClick={() => setQuestion(starter)}>{starter}<ArrowUp /></button>)}</div></div>}
          <form className="composer" onSubmit={ask}><div className="composer-inner"><button className="attach" type="button" onClick={() => setUploadOpen(true)} aria-label="Attach sources"><Plus /></button><textarea value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void ask(); } }} placeholder={ready ? "Ask anything about your documents…" : "Add sources to begin asking questions…"} rows={1} /><button className="send" type="submit" disabled={!question.trim() || asking} aria-label="Send question"><ArrowUp /></button></div><span>LUMEN CAN MAKE MISTAKES · VERIFY IMPORTANT DETAILS IN THE CITED SOURCE</span></form>
        </div>
      </section>
      {uploadOpen && <div className="modal-layer" role="dialog" aria-modal="true" aria-labelledby="upload-title"><button className="modal-backdrop" onClick={() => !processing && setUploadOpen(false)} aria-label="Close upload dialog" /><div className="upload-modal">
        <div className="modal-head"><div><span className="overline"><span /> SOURCE LIBRARY</span><h2 id="upload-title">Build your knowledge base.</h2><p>Add documents and Lumen will extract text, understand visuals, and create a searchable index.</p></div><button onClick={() => setUploadOpen(false)} disabled={processing} aria-label="Close"><X /></button></div>
        <input ref={picker} hidden type="file" multiple accept=".pdf,.docx,.pptx,.png,.jpg,.jpeg" onChange={selectFiles} />
        <div className={`dropzone ${dragging ? "dragging" : ""}`} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={dropFiles}>{processing ? <><LoaderCircle className="spin" /><strong>Reading and indexing your documents…</strong><span>Visual analysis can take a little longer.</span></> : <><span className="upload-icon"><Upload /></span><strong>Drop your sources here</strong><span>or select files from your device</span><button onClick={() => picker.current?.click()}>Choose files</button><small>PDF · DOCX · PPTX · PNG · JPG</small></>}</div>
        {!!documents.length && <div className="document-list-head"><span>{documents.length} {documents.length === 1 ? "source" : "sources"} in this workspace</span><button onClick={() => void clearWorkspace()} disabled={processing}><Trash2 /> Clear all</button></div>}
        <div className="document-list">{documents.map((document) => { const Icon = fileIcon(document.type); return <div className="document-row" key={document.name}><span className="document-icon"><Icon /></span><div><strong>{document.name}</strong><span>{document.type.toUpperCase()} · {formatSize(document.size)}{document.chunks ? ` · ${document.chunks} chunks` : ""}</span></div><span className="indexed"><Check /> Indexed</span></div>; })}</div>
      </div></div>}
      {activeSources && <aside className="evidence-panel"><div className="evidence-head"><div><span className="overline"><span /> RETRIEVAL TRACE</span><h2>Evidence</h2></div><button onClick={() => setActiveSources(null)} aria-label="Close evidence"><X /></button></div><p>The answer was generated from these passages in your private source library.</p><div className="evidence-list">{activeSources.map((source, index) => <article key={`${source.file}-${index}`}><div><span>{String(index + 1).padStart(2, "0")}</span><strong>{source.file}</strong><small>{source.page ? `PAGE ${source.page}` : source.slide ? `SLIDE ${source.slide}` : source.type.toUpperCase()}</small></div><p>{source.snippet}</p></article>)}</div></aside>}
      {activeSources && <button className="panel-scrim" aria-label="Close evidence" onClick={() => setActiveSources(null)} />}
      {notice && <div className="toast"><span><Check /></span>{notice}</div>}
    </main>
  );
}
