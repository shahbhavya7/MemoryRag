// Temporary empty page used by feature tabs until their real UI lands in
// Phases 9b–9d. Shows the selected project so we can see project scoping work.

import { GlassCard } from "../components/GlassPanel";
import { useProjects } from "../project/ProjectContext";

export default function PagePlaceholder({ title, phase }: { title: string; phase: string }) {
  const { selectedProject } = useProjects();
  return (
    <GlassCard className="max-w-2xl">
      <h1>{title}</h1>
      <p className="text-fg-muted mt-2">
        Active project:{" "}
        <strong className="text-fg">
          {selectedProject ? selectedProject.name : "— none selected —"}
        </strong>
      </p>
      <div className="text-fg-faint mt-5 inline-block rounded-full border border-dashed border-white/15 px-3 py-1.5 text-xs">
        Coming in {phase}
      </div>
    </GlassCard>
  );
}
