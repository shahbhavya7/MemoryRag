"""Phase 8 — ingest a real git history into Code Memory (and Decision Memory).

Given a path to a local git repository, this walks the commit log, turns each
commit (its message + a capped diff) into text, chunks it, embeds it, and
stores it:

  * always into **code memory** — so the codebase's history is searchable, and
  * additionally into **decision memory** when the commit message reads like it
    is explaining a *why* (e.g. "we switched to X because ...").

Every stored entry uses the commit hash as its ``source_ref`` in the
``memories`` table, so an answer can cite the exact commit(s) it came from.

Reuses the shared ``store_memory`` writer (Phase 5) so each entry gets a
Postgres row AND a Pinecone vector in the correct namespace — nothing new about
the storage path, only a new *source* of memories.

Run as a CLI:
    python -m backend.services.git_ingest <repo_path> [--max-commits N] [--branch NAME]
"""

from __future__ import annotations

import argparse

import git
from sqlalchemy.orm import Session

from backend.embeddings.chunking import chunk_text
from backend.memory_writer import store_memory

# Cap the diff text we embed per commit. Diffs can be enormous (lockfiles,
# generated code); embedding megabytes of patch is slow and low-value, so we
# keep a readable, representative slice.
MAX_DIFF_CHARS = 6000

# If a commit message contains any of these, we treat it as explaining a
# decision ("why"), and ALSO store it in decision memory. Cheap heuristic —
# the roadmap's future work is to replace it with a classifier.
WHY_MARKERS = (
    "because",
    "reason",
    "in order to",
    "so that",
    "to avoid",
    "instead of",
    "rather than",
    "decided",
    "decision",
    "chose",
    "choose",
    "switch",
    "migrate",
    "rework",
    "rationale",
    "trade-off",
    "tradeoff",
    "why",
)


def _looks_like_decision(message: str) -> bool:
    lower = message.lower()
    return any(marker in lower for marker in WHY_MARKERS)


def _commit_diff_text(commit: "git.Commit") -> tuple[list[str], str]:
    """Return (changed file paths, a capped unified-diff string) for a commit."""
    if commit.parents:
        # Compare against the first parent (normal case).
        diffs = commit.parents[0].diff(commit, create_patch=True)
    else:
        # The very first commit has no parent — diff against the empty tree so
        # its initial files still show up.
        diffs = commit.diff(git.NULL_TREE, create_patch=True)

    files: list[str] = []
    patches: list[str] = []
    for d in diffs:
        path = d.b_path or d.a_path or "?"
        files.append(path)
        try:
            patch = d.diff.decode("utf-8", errors="replace") if isinstance(d.diff, bytes) else str(d.diff)
        except Exception:
            patch = ""
        patches.append(f"--- {path} ---\n{patch}")

    diff_text = "\n".join(patches)
    if len(diff_text) > MAX_DIFF_CHARS:
        diff_text = diff_text[:MAX_DIFF_CHARS] + "\n...[diff truncated]..."
    return files, diff_text


def _commit_document(commit: "git.Commit", files: list[str], diff_text: str) -> str:
    """Human-readable text for one commit — what actually gets embedded."""
    short = commit.hexsha[:8]
    date = commit.committed_datetime.strftime("%Y-%m-%d")
    message = commit.message.strip()
    file_list = ", ".join(files) if files else "(no files)"
    return (
        f"Commit {short} by {commit.author.name} on {date}\n"
        f"Message: {message}\n"
        f"Files changed: {file_list}\n\n"
        f"Diff:\n{diff_text}"
    )


def ingest_git_repo(
    db: Session,
    repo_path: str,
    max_commits: int | None = None,
    branch: str | None = None,
) -> dict:
    """Walk a repo's commit log and store commits into code (and decision) memory.

    Returns a summary dict with per-commit detail so callers (CLI, endpoint,
    demo) can show exactly what was ingested and cited.
    """
    try:
        repo = git.Repo(repo_path)
    except (git.InvalidGitRepositoryError, git.NoSuchPathError) as exc:
        raise ValueError(f"'{repo_path}' is not a valid git repository.") from exc

    commits = list(repo.iter_commits(rev=branch, max_count=max_commits))

    code_chunks_stored = 0
    decision_entries_stored = 0
    per_commit: list[dict] = []

    for commit in commits:
        sha = commit.hexsha
        short = sha[:8]
        subject = commit.message.strip().splitlines()[0] if commit.message.strip() else "(no message)"
        files, diff_text = _commit_diff_text(commit)
        document = _commit_document(commit, files, diff_text)

        # 1) Always store into CODE memory, chunked (message + diff can be long).
        chunks = chunk_text(document) or [document]
        for chunk in chunks:
            store_memory(db, "code", chunk, source_ref=sha)
            code_chunks_stored += 1

        # 2) If the message explains a "why", ALSO store the message in DECISION
        #    memory (the reasoning, not the whole diff).
        is_decision = _looks_like_decision(commit.message)
        if is_decision:
            decision_content = (
                f"Decision recorded in commit {short}: {commit.message.strip()}"
            )
            store_memory(db, "decision", decision_content, source_ref=sha)
            decision_entries_stored += 1

        per_commit.append(
            {
                "sha": sha,
                "short_sha": short,
                "subject": subject,
                "files_changed": len(files),
                "code_chunks": len(chunks),
                "stored_as_decision": is_decision,
            }
        )

    return {
        "repo_path": repo_path,
        "branch": branch or repo.active_branch.name if not repo.head.is_detached else branch,
        "commits_processed": len(commits),
        "code_chunks_stored": code_chunks_stored,
        "decision_entries_stored": decision_entries_stored,
        "commits": per_commit,
    }


def _main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a git history into MemoryRAG code/decision memory.")
    parser.add_argument("repo_path", help="Path to a local git repository.")
    parser.add_argument("--max-commits", type=int, default=None, help="Only ingest the N most recent commits.")
    parser.add_argument("--branch", default=None, help="Branch/ref to walk (default: current branch).")
    args = parser.parse_args()

    # Import here so the module is importable without DB config (e.g. in tests).
    from backend.database.session import SessionLocal
    from backend.models.memory import seed_memory_types

    db = SessionLocal()
    try:
        seed_memory_types(db)  # make sure the memory types exist
        summary = ingest_git_repo(db, args.repo_path, max_commits=args.max_commits, branch=args.branch)
    finally:
        db.close()

    print(f"Ingested {summary['commits_processed']} commit(s) from {summary['repo_path']}")
    print(f"  code chunks stored:     {summary['code_chunks_stored']}")
    print(f"  decision entries stored: {summary['decision_entries_stored']}")
    for c in summary["commits"]:
        tag = "  [+decision]" if c["stored_as_decision"] else ""
        print(f"  {c['short_sha']}  {c['subject']}{tag}")


if __name__ == "__main__":
    _main()
