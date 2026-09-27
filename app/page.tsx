"use client";

import { ChangeEvent, DragEvent, FormEvent, useEffect, useRef, useState } from "react";
import {
  ArrowUp, BookOpenText, Check, FileImage, FileText, Files, LoaderCircle,
  Menu, MessageCircleMore, Plus, Search, Sparkles, Trash2, Upload, X,
} from "lucide-react";

type Source = { file: string; type: string; snippet: string; page?: number; slide?: number };
type Message = { id: string; role: "user" | "assistant"; content: string; sources?: Source[] };
type DocumentInfo = { name: string; type: string; size?: number; chunks?: number };
type ServiceStatus = "checking" | "ready" | "unconfigured" | "offline";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const starters = [
  { label: "Executive summary", prompt: "Summarise the complete document and its key findings." },
  { label: "Study notes", prompt: "Turn the complete document into structured study notes." },
  { label: "Key decisions", prompt: "List the main decisions, recommendations, and action items." },
  { label: "Quiz me", prompt: "Create five useful quiz questions from the document." },
];
const initialMessages: Message[] = [{
  id: "welcome",
  role: "assistant",
  content: "Hello — I’m Lumen. Add a document, then ask a precise question or request a full summary. I’ll keep answers grounded in your sources and show the evidence I used.",
}];

function fileIcon(type: string) {
  return ["png", "jpg", "jpeg", "image"].includes(type.toLowerCase()) ? FileImage : FileText;
}

function formatSize(bytes?: number) {
  if (!bytes) return "Document";
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function localReply(prompt: string) {
  const normalized = prompt.toLowerCase().replace(/[^a-z\s']/g, " ").replace(/\s+/g, " ").trim();
  if (/^(hi|hello|hey|hiya|yo|good morning|good afternoon|good evening)$/.test(normalized)) {
    return "Hi! What are you working on today? Upload a document whenever you’re ready, or ask me what I can help you do.";
  }
  if (/^(thanks|thank you|thx|great|cool|okay|ok)$/.test(normalized)) {
    return "You’re welcome. Send the next question whenever you’re ready.";
  }
  if (/^(how are you|how are you doing|what's up|whats up)$/.test(normalized)) {
    return "I’m ready to help. I can summarise a whole document, answer a targeted question, compare ideas, or create study material.";
  }
  if (/^(who are you|what can you do|help)$/.test(normalized)) {
    return "I’m Lumen, a document research assistant. I can read PDF, DOCX, PPTX, and image files; summarise the full material; answer questions with evidence; compare concepts; and create notes or quizzes.";
  }
  return null;
}

function isSummaryRequest(prompt: string) {
  return /\b(summarize|summarise|summary|overview|recap|key findings|executive brief)\b/i.test(prompt);
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
  const [searchMode, setSearchMode] = useState<"summary" | "search">("search");
  const [status, setStatus] = useState<ServiceStatus>("checking");
  const [notice, setNotice] = useState("");
  const [activeSources, setActiveSources] = useState<Source[] | null>(null);
  const [chunkCount, setChunkCount] = useState(0);

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((response) => response.ok ? response.json() : Promise.reject())
      .then((payload) => {
        const data = payload as { configured?: boolean; chunks?: number; documents?: DocumentInfo[] };
        setStatus(data.configured ? "ready" : "unconfigured");
        setChunkCount(data.chunks ?? 0);
        setDocuments(data.documents ?? []);
      })
      .catch(() => setStatus("offline"));
  }, []);

  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [messages, asking]);
  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => setNotice(""), 4800);
    return () => window.clearTimeout(timeout);
  }, [notice]);

  async function processFiles(files: File[]) {
    const valid = files.filter((file) => /\.(pdf|docx|pptx|png|jpe?g)$/i.test(file.name));
    if (!valid.length) { setNotice("Choose a PDF, DOCX, PPTX, PNG, or JPG file."); return; }
    if (status === "unconfigured") { setNotice("Add OPENAI_API_KEY in Render before uploading documents."); return; }
    setProcessing(true);
    const optimistic = valid.map((file) => ({ name: file.name, type: file.name.split(".").pop() ?? "file", size: file.size }));
    setDocuments((current) => [...current, ...optimistic]);
    try {
      const body = new FormData();
      valid.forEach((file) => body.append("files", file));
      const response = await fetch(`${API_URL}/documents/process`, { method: "POST", body });
      const data = await response.json() as { detail?: string; documents?: DocumentInfo[]; chunks?: number };
      if (!response.ok) throw new Error(data.detail ?? "The documents could not be processed.");
      setDocuments(data.documents ?? optimistic); setChunkCount(data.chunks ?? 0); setStatus("ready"); setUploadOpen(false);
      setNotice(`${valid.length} ${valid.length === 1 ? "document" : "documents"} indexed and ready.`);
    } catch (error) {
      setDocuments((current) => current.filter((item) => !optimistic.some((file) => file.name === item.name)));
      setNotice(error instanceof Error ? error.message : "Could not reach the document service.");
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
    const reply = localReply(prompt);
    setQuestion("");
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: "user", content: prompt }]);
    if (reply) {
      window.setTimeout(() => setMessages((current) => [...current, { id: crypto.randomUUID(), role: "assistant", content: reply }]), 180);
      return;
    }
    if (!chunkCount) {
      setMessages((current) => [...current, { id: crypto.randomUUID(), role: "assistant", content: "I can chat, but I need at least one indexed document for that request. Add a source and I’ll take it from there." }]);
      setUploadOpen(true);
      return;
    }
    const mode = isSummaryRequest(prompt) ? "summary" : "search";
    setSearchMode(mode); setAsking(true);
    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: prompt, mode }),
      });
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
  const statusLabel = status === "ready" ? "AI ready" : status === "unconfigured" ? "API key needed" : status === "offline" ? "Service offline" : "Connecting";

  return (
    <main className="app-shell">
      <header className="app-header">
        <a className="brand" href="#" aria-label="Lumen home"><span className="brand-glyph">L</span><span>Lumen</span></a>
        <nav className="header-nav" aria-label="Workspace navigation">
          <button className="active"><MessageCircleMore />Chat</button>
          <button onClick={() => setUploadOpen(true)}><Files />Sources <b>{documents.length}</b></button>
          <button><BookOpenText />Notebook</button>
        </nav>
        <div className="header-actions">
          <span className={`service-pill ${status}`}><i />{statusLabel}</span>
          <button className="round-button" aria-label="Search"><Search /></button>
          <button className="source-button" onClick={() => setUploadOpen(true)}><Plus />Add source</button>
          <button className="mobile-menu" onClick={() => setMobileNav(!mobileNav)} aria-label="Toggle menu"><Menu /></button>
        </div>
      </header>

      <div className="app-body">
        <aside className={`source-rail ${mobileNav ? "open" : ""}`}>
          <div className="rail-heading"><div><span>Source library</span><strong>{documents.length ? `${documents.length} active` : "Empty"}</strong></div><button onClick={() => setUploadOpen(true)} aria-label="Add a source"><Plus /></button></div>
          <div className="source-list">
            {documents.length ? documents.map((document) => {
              const Icon = fileIcon(document.type);
              return <button className="source-card" key={document.name} onClick={() => setUploadOpen(true)}><span className="source-icon"><Icon /></span><span><strong>{document.name}</strong><small>{document.type.toUpperCase()} · {formatSize(document.size)}</small></span><i /> </button>;
            }) : <button className="empty-sources" onClick={() => setUploadOpen(true)}><span><Upload /></span><strong>Drop in your first source</strong><small>PDF, DOCX, PPTX, PNG or JPG</small></button>}
          </div>
          <div className="rail-note"><Sparkles /><p><strong>Full-document summaries</strong><span>Summary requests read the entire indexed library—not just similar passages.</span></p></div>
          <div className="rail-profile"><span>HR</span><p><strong>Harsh Rathod</strong><small>Private workspace</small></p></div>
        </aside>

        <section className="chat-workspace">
          <div className="chat-column">
            <div className="hero">
              <span className="eyebrow"><i /> DOCUMENT INTELLIGENCE</span>
              <h1>Your documents,<br /><em>distilled.</em></h1>
              <p>Ask naturally. Get a direct answer, a complete summary, and the exact passages behind it.</p>
              <div className="hero-stats"><span><strong>{documents.length}</strong> sources</span><span><strong>{chunkCount.toLocaleString()}</strong> passages</span><span className={ready ? "ready" : "waiting"}><i />{ready ? "Ready to answer" : "Waiting for a source"}</span></div>
            </div>

            <div className="thread">
              {messages.map((message) => <article className={`message ${message.role}`} key={message.id}>
                <div className="message-avatar">{message.role === "assistant" ? <Sparkles /> : "HR"}</div>
                <div className="message-content">
                  <div className="message-meta"><strong>{message.role === "assistant" ? "Lumen" : "You"}</strong><span>{message.role === "assistant" ? "Research assistant" : "Now"}</span></div>
                  <div className="message-copy">{renderText(message.content)}</div>
                  {!!message.sources?.length && <div className="citation-row"><span>Sources</span>{message.sources.slice(0, 3).map((source, index) => <button key={`${source.file}-${index}`} onClick={() => setActiveSources(message.sources!)}><FileText />{source.file}<small>{source.page ? `p.${source.page}` : source.slide ? `s.${source.slide}` : ""}</small></button>)}<button className="evidence-link" onClick={() => setActiveSources(message.sources!)}>View evidence</button></div>}
                </div>
              </article>)}
              {asking && <article className="message assistant thinking"><div className="message-avatar"><Sparkles /></div><div className="message-content"><div className="message-meta"><strong>Lumen</strong><span>{searchMode === "summary" ? "Reading the full library" : "Finding the best evidence"}</span></div><div className="thinking-bar"><i /><i /><i /></div></div></article>}
              <div ref={end} />
            </div>

            {messages.length === 1 && <div className="starters"><span>Start with</span><div>{starters.map((starter) => <button key={starter.label} onClick={() => setQuestion(starter.prompt)}><strong>{starter.label}</strong><small>{starter.prompt}</small><ArrowUp /></button>)}</div></div>}
          </div>

          <form className="composer-wrap" onSubmit={ask}>
            <div className="composer"><button type="button" onClick={() => setUploadOpen(true)} aria-label="Attach sources"><Plus /></button><textarea value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void ask(); } }} placeholder={ready ? "Ask a question, or say “summarise this”..." : "Say hi, or add a document to begin..."} rows={1} /><button className="send" type="submit" disabled={!question.trim() || asking} aria-label="Send question"><ArrowUp /></button></div>
            <span>Answers are grounded in your uploaded sources. Verify important details.</span>
          </form>
        </section>
      </div>

      {uploadOpen && <div className="modal-layer" role="dialog" aria-modal="true" aria-labelledby="upload-title"><button className="modal-backdrop" onClick={() => !processing && setUploadOpen(false)} aria-label="Close upload dialog" /><div className="upload-modal">
        <div className="modal-head"><div><span className="eyebrow"><i /> SOURCE LIBRARY</span><h2 id="upload-title">Give Lumen something to read.</h2><p>Add documents or images. They’re parsed, indexed, and made ready for grounded questions.</p></div><button onClick={() => setUploadOpen(false)} disabled={processing} aria-label="Close"><X /></button></div>
        <input ref={picker} hidden type="file" multiple accept=".pdf,.docx,.pptx,.png,.jpg,.jpeg" onChange={selectFiles} />
        <div className={`dropzone ${dragging ? "dragging" : ""}`} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={dropFiles}>{processing ? <><LoaderCircle className="spin" /><strong>Reading and indexing…</strong><span>Images may need a little extra time.</span></> : <><span className="upload-mark"><Upload /></span><strong>Drop files here</strong><span>or choose them from your device</span><button onClick={() => picker.current?.click()}>Choose files</button><small>PDF · DOCX · PPTX · PNG · JPG · MAX 25 MB</small></>}</div>
        {!!documents.length && <div className="document-list-head"><span>{documents.length} {documents.length === 1 ? "source" : "sources"}</span><button onClick={() => void clearWorkspace()} disabled={processing}><Trash2 />Clear library</button></div>}
        <div className="document-list">{documents.map((document) => { const Icon = fileIcon(document.type); return <div className="document-row" key={document.name}><span><Icon /></span><div><strong>{document.name}</strong><small>{document.type.toUpperCase()} · {formatSize(document.size)}{document.chunks ? ` · ${document.chunks} passages` : ""}</small></div><b><Check />Indexed</b></div>; })}</div>
      </div></div>}

      {activeSources && <><button className="panel-backdrop" aria-label="Close evidence" onClick={() => setActiveSources(null)} /><aside className="evidence-panel"><div className="evidence-head"><div><span className="eyebrow"><i /> EVIDENCE</span><h2>Source passages</h2></div><button onClick={() => setActiveSources(null)} aria-label="Close evidence"><X /></button></div><p>These passages were used to produce the answer.</p><div>{activeSources.map((source, index) => <article key={`${source.file}-${index}`}><header><span>{String(index + 1).padStart(2, "0")}</span><strong>{source.file}</strong><small>{source.page ? `PAGE ${source.page}` : source.slide ? `SLIDE ${source.slide}` : source.type.toUpperCase()}</small></header><p>{source.snippet}</p></article>)}</div></aside></>}
      {notice && <div className="toast"><span><Check /></span>{notice}</div>}
    </main>
  );
}
