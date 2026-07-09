"""Walks the full Project CRUD lifecycle against a running MemoryRAG API.

Usage:
    python demo_phase1.py [base_url]

Requires the API to already be running (see README: uvicorn backend.main:app).
"""

import sys

import requests

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"


def show(label: str, response: requests.Response) -> None:
    print(f"\n--- {label} ---")
    print(f"{response.request.method} {response.request.url} -> {response.status_code}")
    if response.content:
        print(response.json())


def main() -> None:
    health = requests.get(f"{BASE_URL}/health")
    show("Health check", health)
    health.raise_for_status()

    created = requests.post(
        f"{BASE_URL}/projects",
        json={"name": "MemoryRAG Demo", "description": "Phase 1 CRUD walkthrough"},
    )
    show("Create project", created)
    created.raise_for_status()
    project_id = created.json()["id"]

    listed = requests.get(f"{BASE_URL}/projects")
    show("List projects", listed)
    listed.raise_for_status()

    fetched = requests.get(f"{BASE_URL}/projects/{project_id}")
    show("Get project by id", fetched)
    fetched.raise_for_status()

    updated = requests.put(
        f"{BASE_URL}/projects/{project_id}",
        json={"name": "MemoryRAG Demo (updated)", "description": "Now with an update"},
    )
    show("Update project", updated)
    updated.raise_for_status()

    deleted = requests.delete(f"{BASE_URL}/projects/{project_id}")
    show("Delete project", deleted)
    deleted.raise_for_status()

    confirm_404 = requests.get(f"{BASE_URL}/projects/{project_id}")
    show("Confirm 404 after delete", confirm_404)
    assert confirm_404.status_code == 404, "Expected 404 after delete"

    print("\nAll CRUD operations completed successfully.")


if __name__ == "__main__":
    main()
