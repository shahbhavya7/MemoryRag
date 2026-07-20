// Upload page (Phase 9c): add a typed memory (POST /memories) or upload a plain
// text document (POST /documents/upload). Feedback is inline glass toasts.

import { useRef, useState, type FormEvent } from "react";

import { api, ApiError } from "../api/client";
import { MEMORY_TYPES } from "../api/types";
import { GlassCard } from "../components/GlassPanel";
import { ToastStack, useToasts } from "../components/Toast";
import { memoryMeta } from "../lib/memoryTypes";
import { useProjects } from "../project/ProjectContext";

export default function UploadPage() {
  const { selectedProjectId, selectedProject } = useProjects();
  const { toasts, push, dismiss } = useToasts();

  // --- Add-memory form ---
  const [memoryType, setMemoryType] = useState<string>("decision");
  const [content, setContent] = useState("");
  const [sourceRef, setSourceRef] = useState("");
  const [savingMemory, setSavingMemory] = useState(false);

  // --- Upload-document form ---
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  async function submitMemory(e: FormEvent) {
    e.preventDefault();
    if (!content.trim() || !selectedProjectId) return;
    setSavingMemory(true);
    try {
      await api.createMemory(selectedProjectId, memoryType, content.trim(), sourceRef.trim() || undefined);
      push("success", `Saved to ${memoryMeta(memoryType).label} memory in ${selectedProject?.name}.`);
      setContent("");
      setSourceRef("");
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Failed to save memory.");
    } finally {
      setSavingMemory(false);
    }
  }

  async function submitDocument(e: FormEvent) {
    e.preventDefault();
    if (!file || !selectedProjectId) return;
    setUploading(true);
    try {
      const res = await api.uploadDocument(selectedProjectId, file);
      push("success", `Uploaded “${res.source_filename}” ${res.chunks_created} chunk(s) embedded.`);
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Failed to upload document.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="mb-1">Upload</h1>
      <p className="text-fg-muted mb-6">Add knowledge to a memory type, or upload a text document.</p>

      <div className="grid gap-5 md:grid-cols-2">
        {/* Add a memory */}
        <GlassCard>
          <h2>Add a memory</h2>
          <p className="text-fg-muted mt-1 text-sm">Stored in the chosen type's namespace.</p>
          <form onSubmit={submitMemory}>
            <label className="field-label" htmlFor="mtype">
              Memory type
            </label>
            <select id="mtype" value={memoryType} onChange={(e) => setMemoryType(e.target.value)}>
              {MEMORY_TYPES.map((t) => (
                <option key={t} value={t}>
                  {memoryMeta(t).label}
                </option>
              ))}
            </select>

            <label className="field-label" htmlFor="content">
              Content
            </label>
            <textarea
              id="content"
              rows={5}
              className="resize-y"
              placeholder="e.g. We decided to adopt trunk-based development to reduce merge pain."
              value={content}
              onChange={(e) => setContent(e.target.value)}
              required
            />

            <label className="field-label" htmlFor="sref">
              Source ref <span className="normal-case opacity-60">(optional)</span>
            </label>
            <input
              id="sref"
              placeholder="e.g. adr/0012-trunk-based"
              value={sourceRef}
              onChange={(e) => setSourceRef(e.target.value)}
            />

            {!selectedProjectId && (
              <p className="mt-3 text-xs" style={{ color: "var(--danger)" }}>
                Select a project in the top bar first.
              </p>
            )}

            <button
              type="submit"
              className="primary mt-5 w-full"
              disabled={savingMemory || !content.trim() || !selectedProjectId}
            >
              {savingMemory ? "Saving…" : "Save memory"}
            </button>
          </form>
        </GlassCard>

        {/* Upload a document */}
        <GlassCard>
          <h2>Upload a document</h2>
          <p className="text-fg-muted mt-1 text-sm">
            Plain text (.txt) is chunked + embedded into document memory for{" "}
            <strong className="text-fg">{selectedProject?.name ?? "—"}</strong>.
          </p>
          <form onSubmit={submitDocument}>
            <label className="field-label" htmlFor="file">
              Text file
            </label>
            <input
              id="file"
              ref={fileInput}
              type="file"
              accept=".txt,text/plain"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="file:mr-3 file:rounded-lg file:border-0 file:bg-white/10 file:px-3 file:py-1.5 file:text-fg"
            />
            {file && <p className="text-fg-muted mt-2 text-xs">Selected: {file.name}</p>}

            {!selectedProjectId && (
              <p className="mt-3 text-xs" style={{ color: "var(--danger)" }}>
                Select a project in the top bar first.
              </p>
            )}

            <button
              type="submit"
              className="primary mt-5 w-full"
              disabled={uploading || !file || !selectedProjectId}
            >
              {uploading ? "Uploading…" : "Upload document"}
            </button>
          </form>
        </GlassCard>
      </div>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}
