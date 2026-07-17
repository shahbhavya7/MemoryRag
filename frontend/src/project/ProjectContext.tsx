// Tracks the list of projects and which one is currently selected. The top-bar
// project selector reads/writes this; feature pages (Chat, etc.) read the
// selected project id so their API calls are scoped to it.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api } from "../api/client";
import type { Project } from "../api/types";
import { useAuth } from "../auth/AuthContext";

interface ProjectState {
  projects: Project[];
  selectedProjectId: number | null;
  selectedProject: Project | null;
  loading: boolean;
  error: string | null;
  selectProject: (id: number) => void;
  refresh: () => Promise<void>;
  createProject: (name: string, description?: string) => Promise<Project>;
}

const ProjectContext = createContext<ProjectState | undefined>(undefined);

export function ProjectProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await api.listProjects();
      setProjects(list);
      // Default the selection to the first project if none chosen yet.
      setSelectedProjectId((current) => current ?? (list.length ? list[0].id : null));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }, []);

  const createProject = useCallback(
    async (name: string, description?: string) => {
      const project = await api.createProject(name, description);
      setProjects((prev) => [...prev, project]);
      setSelectedProjectId(project.id); // auto-select the new one
      return project;
    },
    [],
  );

  // Load projects once the user is authenticated; clear them on logout.
  useEffect(() => {
    if (isAuthenticated) {
      void refresh();
    } else {
      setProjects([]);
      setSelectedProjectId(null);
    }
  }, [isAuthenticated, refresh]);

  const selectedProject = useMemo(
    () => projects.find((p) => p.id === selectedProjectId) ?? null,
    [projects, selectedProjectId],
  );

  const value = useMemo<ProjectState>(
    () => ({
      projects,
      selectedProjectId,
      selectedProject,
      loading,
      error,
      selectProject: setSelectedProjectId,
      refresh,
      createProject,
    }),
    [projects, selectedProjectId, selectedProject, loading, error, refresh, createProject],
  );

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useProjects(): ProjectState {
  const ctx = useContext(ProjectContext);
  if (!ctx) throw new Error("useProjects must be used inside <ProjectProvider>");
  return ctx;
}
