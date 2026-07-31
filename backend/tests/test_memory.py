from app.memory import manager as memory


def test_save_and_get_history_round_trip(db_session):
    from app.models.user import User
    from app.core.security import hash_password

    user = User(email="mem@example.com", hashed_password=hash_password("pw"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    memory.save_message(db_session, "s1", user.id, "user", "first message")
    memory.save_message(db_session, "s1", user.id, "assistant", "first reply")
    memory.save_message(db_session, "s1", user.id, "user", "second message")

    history = memory.get_history(db_session, "s1", user.id)

    assert [h["content"] for h in history] == [
        "first message",
        "first reply",
        "second message",
    ]


def test_get_history_scoped_to_session_and_user(db_session):
    from app.models.user import User
    from app.core.security import hash_password

    user_a = User(email="mem-a@example.com", hashed_password=hash_password("pw"))
    user_b = User(email="mem-b@example.com", hashed_password=hash_password("pw"))
    db_session.add_all([user_a, user_b])
    db_session.commit()
    db_session.refresh(user_a)
    db_session.refresh(user_b)

    memory.save_message(db_session, "shared-session-id", user_a.id, "user", "user a's message")
    memory.save_message(db_session, "shared-session-id", user_b.id, "user", "user b's message")

    history_a = memory.get_history(db_session, "shared-session-id", user_a.id)
    assert [h["content"] for h in history_a] == ["user a's message"]