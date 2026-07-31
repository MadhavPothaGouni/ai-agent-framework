from sqlalchemy.orm import Session

from app.models.message import Message


def save_message(db: Session, session_id: str, user_id: int, role: str, content: str) -> Message:
    message = Message(session_id=session_id, user_id=user_id, role=role, content=content)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_history(
    db: Session, session_id: str, user_id: int, limit: int = 50
) -> list[dict[str, str]]:
    rows = (
        db.query(Message)
        .filter(Message.session_id == session_id, Message.user_id == user_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
        .all()
    )
    return [{"role": row.role, "content": row.content} for row in rows]