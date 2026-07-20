// The top-bar project selector, backed by the /projects endpoints.
// Switch the active project or create a new one inline.

import { Plus } from "lucide-react";
import { useState, type FormEvent } from "react";

import { useProjects } from "../project/ProjectContext";

export default function ProjectSelector() {
  const { projects, selectedProjectId, selectProject, createProject, loading } = useProjects();
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createProject(name.trim());
      setName("");
      setCreating(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create project");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center gap-3">
      <span className="text-eyebrow">Project</span>
      <select
        aria-label="Select project"
        className="!w-auto min-w-[170px]"
        value={selectedProjectId ?? ""}
        onChange={(e) => selectProject(Number(e.target.value))}
        disabled={loading || projects.length === 0}
      >
        {projects.length === 0 && <option value="">No projects yet</option>}
        {projects.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>

      {creating ? (
        <form onSubmit={handleCreate} className="flex items-center gap-2">
          <input
            autoFocus
            className="!w-[170px]"
            placeholder="New project name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button type="submit" className="primary" disabled={busy}>
            {busy ? "…" : "Add"}
          </button>
          <button type="button" className="ghost" onClick={() => setCreating(false)}>
            Cancel
          </button>
        </form>
      ) : (
        <button
          type="button"
          className="ghost inline-flex items-center gap-1.5"
          onClick={() => setCreating(true)}
        >
          <Plus size={15} /> New
        </button>
      )}
      {error && <span className="text-[var(--danger)] text-xs">{error}</span>}
    </div>
  );
}
