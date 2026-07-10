from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.dependencies import get_current_user
from backend.models.chat import Chat
from backend.models.project import Project
from backend.models.user import User
from backend.schemas import ChatCreate, ChatOut, ChatUpdate

router = APIRouter(prefix="/projects/{project_id}/chats", tags=["chats"])


def _get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_chat_or_404(db: Session, project_id: int, chat_id: int, user_id: int) -> Chat:
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.project_id == project_id, Chat.user_id == user_id)
        .first()
    )
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.post("", response_model=ChatOut, status_code=201)
def create_chat(
    project_id: int,
    payload: ChatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(db, project_id)
    chat = Chat(project_id=project_id, user_id=current_user.id, title=payload.title)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


@router.get("", response_model=list[ChatOut])
def list_chats(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(db, project_id)
    return (
        db.query(Chat)
        .filter(Chat.project_id == project_id, Chat.user_id == current_user.id)
        .order_by(Chat.id)
        .all()
    )


@router.get("/{chat_id}", response_model=ChatOut)
def get_chat(
    project_id: int,
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(db, project_id)
    return _get_chat_or_404(db, project_id, chat_id, current_user.id)


@router.put("/{chat_id}", response_model=ChatOut)
def update_chat(
    project_id: int,
    chat_id: int,
    payload: ChatUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(db, project_id)
    chat = _get_chat_or_404(db, project_id, chat_id, current_user.id)
    chat.title = payload.title
    db.commit()
    db.refresh(chat)
    return chat


@router.delete("/{chat_id}", status_code=204)
def delete_chat(
    project_id: int,
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(db, project_id)
    chat = _get_chat_or_404(db, project_id, chat_id, current_user.id)
    db.delete(chat)
    db.commit()
