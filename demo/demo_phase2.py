"""Walks the Phase 2 auth + multi-user lifecycle against a running MemoryRAG API.

Usage:
    python3 demo/demo_phase2.py [base_url]

Requires the API to already be running (see README: uvicorn backend.main:app).
"""

import sys
import uuid

import requests

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"


def show(label: str, response: requests.Response) -> None:
    print(f"\n--- {label} ---")
    print(f"{response.request.method} {response.request.url} -> {response.status_code}")
    if response.content:
        print(response.json())


def main() -> None:
    email = f"demo+{uuid.uuid4().hex[:8]}@example.com"
    password = "DemoPass123!"

    registered = requests.post(
        f"{BASE_URL}/auth/register",
        json={"email": email, "password": password},
    )
    show("Register user", registered)
    registered.raise_for_status()

    logged_in = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password},
    )
    show("Log in", logged_in)
    logged_in.raise_for_status()
    token = logged_in.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    created_project = requests.post(
        f"{BASE_URL}/projects",
        json={"name": "Phase 2 Demo Project", "description": "Multi-user CRUD walkthrough"},
        headers=headers,
    )
    show("Create project (authenticated)", created_project)
    created_project.raise_for_status()
    project_id = created_project.json()["id"]

    created_chat = requests.post(
        f"{BASE_URL}/projects/{project_id}/chats",
        json={"title": "First chat"},
        headers=headers,
    )
    show("Create chat under project", created_chat)
    created_chat.raise_for_status()

    listed_chats = requests.get(f"{BASE_URL}/projects/{project_id}/chats", headers=headers)
    show("List chats", listed_chats)
    listed_chats.raise_for_status()

    unauthenticated = requests.get(f"{BASE_URL}/projects")
    show("Unauthenticated request to protected route", unauthenticated)
    assert unauthenticated.status_code == 401, "Expected 401 without a token"

    print("\nAll Phase 2 auth + multi-user checks completed successfully.")


if __name__ == "__main__":
    main()
