"""Tests for privacy-scoped, first-party conversion events.

Privacy scope: the table stores only an allowlisted event ``name`` and a naive
UTC ``occurred_at``. Every test here asserts that no identifying data ever
reaches storage.
"""

from sqlmodel import select

from models import Group, GroupMember, User, Wish


def _events(session, name):
    """All recorded conversion rows for one event name, refreshed from storage."""
    from models import ConversionEvent

    session.expire_all()
    return session.exec(select(ConversionEvent).where(ConversionEvent.name == name)).all()


def test_conversion_event_has_only_allowed_columns():
    from models import ConversionEvent

    columns = set(ConversionEvent.__table__.columns.keys())
    assert columns == {"id", "name", "occurred_at"}


def test_conversion_event_has_composite_name_occurred_at_index():
    from models import ConversionEvent

    composites = {
        tuple(column.name for column in index.columns)
        for index in ConversionEvent.__table__.indexes
    }
    assert ("name", "occurred_at") in composites


def test_allowlist_is_the_documented_set():
    from services import CONVERSION_EVENTS

    assert CONVERSION_EVENTS == frozenset({
        "signup", "login", "group_created", "invitation_accepted",
        "invitation_sent", "wish_added", "wish_reserved", "draw_performed",
    })


def test_record_conversion_stores_allowlisted_event(session):
    from models import ConversionEvent
    from services import record_conversion

    record_conversion(session, "signup")

    rows = session.exec(select(ConversionEvent)).all()
    assert [row.name for row in rows] == ["signup"]
    assert rows[0].occurred_at is not None


def test_record_conversion_ignores_unknown_name(session):
    from models import ConversionEvent
    from services import record_conversion

    record_conversion(session, "not_an_event")

    assert session.exec(select(ConversionEvent)).all() == []


def test_record_conversion_never_raises_on_storage_error():
    from services import record_conversion

    class BrokenSession:
        def __init__(self):
            self.rolled_back = False

        def add(self, instance):
            raise RuntimeError("storage down")

        def commit(self):
            raise RuntimeError("storage down")

        def rollback(self):
            self.rolled_back = True

    broken = BrokenSession()

    # Must be a no-op from the caller's perspective: the user action that
    # triggered the event must not fail because analytics storage is down.
    record_conversion(broken, "signup")

    assert broken.rolled_back is True


def test_conversion_counts_returns_totals_and_per_day(session):
    from datetime import datetime, timedelta

    from models import ConversionEvent
    from services import conversion_counts

    now = datetime(2026, 10, 8, 12, 0, 0)
    session.add_all([
        ConversionEvent(name="signup", occurred_at=now),
        ConversionEvent(name="signup", occurred_at=now),
        ConversionEvent(name="login", occurred_at=now),
        ConversionEvent(name="login", occurred_at=now - timedelta(days=1)),
    ])
    session.commit()

    counts = conversion_counts(session)

    assert counts["totals"] == {"signup": 2, "login": 2}
    assert counts["per_day"] == {"2026-10-08": 3, "2026-10-07": 1}


def test_conversion_counts_filters_by_since(session):
    from datetime import datetime, timedelta

    from models import ConversionEvent
    from services import conversion_counts

    now = datetime(2026, 10, 8, 12, 0, 0)
    session.add_all([
        ConversionEvent(name="signup", occurred_at=now),
        ConversionEvent(name="login", occurred_at=now),
        ConversionEvent(name="signup", occurred_at=now - timedelta(days=7)),
    ])
    session.commit()

    counts = conversion_counts(session, since=now - timedelta(days=1))

    assert counts["totals"] == {"signup": 1, "login": 1}
    assert counts["per_day"] == {"2026-10-08": 2}


# --- Route wiring: each action records exactly one matching event ---


def test_register_records_signup(client, session):
    client.post("/register", data={"email": "new@test.com", "password": "pass", "name": "New"})

    assert len(_events(session, "signup")) == 1


def test_register_succeeds_when_conversion_storage_fails(client, session, monkeypatch):
    import services

    class _Boom:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("storage down")

    # Patch the symbol record_conversion resolves at call time. The user action
    # must complete and persist even though analytics storage is broken.
    monkeypatch.setattr(services, "ConversionEvent", _Boom)

    response = client.post("/register", data={"email": "boom@test.com", "password": "pass", "name": "Boom"})

    assert response.status_code == 200
    assert response.headers["HX-Redirect"] == "/dashboard"
    assert session.exec(select(User).where(User.email == "boom@test.com")).first() is not None


def test_login_records_login(client, session, test_user):
    client.post("/login", data={"email": "test@example.com", "password": "password123"})

    assert len(_events(session, "login")) == 1


def test_failed_login_records_nothing(client, session, test_user):
    client.post("/login", data={"email": "test@example.com", "password": "wrong"})

    assert _events(session, "login") == []


def test_create_group_records_group_created(auth_client, session, test_user):
    auth_client.post("/create-group", data={"name": "Grupo", "emails": ""})

    assert len(_events(session, "group_created")) == 1


def test_join_records_invitation_accepted_only_for_new_member(auth_client, session, test_user):
    group = Group(name="Grupo", code="JOINCODE", admin_id=test_user.id)
    session.add(group)
    session.commit()
    session.refresh(group)

    auth_client.post(f"/join/{group.code}")
    assert len(_events(session, "invitation_accepted")) == 1

    auth_client.post(f"/join/{group.code}")
    assert len(_events(session, "invitation_accepted")) == 1


def test_invite_records_invitation_sent_when_emails_present(auth_client, session, test_user):
    group = Group(name="Grupo", code="INVCODE", admin_id=test_user.id)
    session.add(group)
    session.commit()
    session.refresh(group)

    auth_client.post(f"/group/{group.id}/invite", data={"emails": "a@b.com, c@d.com"})

    assert len(_events(session, "invitation_sent")) == 1


def test_invite_records_nothing_when_email_list_empty(auth_client, session, test_user):
    group = Group(name="Grupo", code="INVCODE2", admin_id=test_user.id)
    session.add(group)
    session.commit()
    session.refresh(group)

    auth_client.post(f"/group/{group.id}/invite", data={"emails": " , "})

    assert _events(session, "invitation_sent") == []


def _make_two_member_group(session, test_user, code):
    other = User(email=f"other-{code}@t.com", name="Other", hashed_password="x")
    session.add(other)
    session.commit()
    session.refresh(other)
    group = Group(name="Grupo", code=code, admin_id=test_user.id)
    session.add(group)
    session.commit()
    session.refresh(group)
    session.add_all([
        GroupMember(group_id=group.id, user_id=test_user.id),
        GroupMember(group_id=group.id, user_id=other.id),
    ])
    session.commit()
    return group


def test_draw_records_draw_performed(auth_client, session, test_user):
    group = _make_two_member_group(session, test_user, "DRAWCODE")

    auth_client.post(f"/group/{group.id}/draw")

    assert len(_events(session, "draw_performed")) == 1


def test_failed_draw_records_nothing(auth_client, session, test_user):
    group = Group(name="Grupo", code="DRAWCODE2", admin_id=test_user.id)
    session.add(group)
    session.commit()
    session.refresh(group)
    session.add(GroupMember(group_id=group.id, user_id=test_user.id))
    session.commit()

    response = auth_client.post(f"/group/{group.id}/draw")

    assert response.status_code == 200
    assert _events(session, "draw_performed") == []


def test_add_wish_records_wish_added(auth_client, session, test_user):
    auth_client.post("/wishes", data={"content": "Un libro"})

    assert len(_events(session, "wish_added")) == 1


def test_reserve_records_only_when_setting(auth_client, session, test_user):
    owner = User(email="owner@t.com", name="Owner", hashed_password="x")
    session.add(owner)
    session.commit()
    session.refresh(owner)
    wish = Wish(user_id=owner.id, title="Cosa")
    session.add(wish)
    session.commit()
    session.refresh(wish)

    auth_client.post(f"/wishes/{wish.id}/toggle-reserve")
    assert len(_events(session, "wish_reserved")) == 1

    # Un-reserving is not a conversion.
    auth_client.post(f"/wishes/{wish.id}/toggle-reserve")
    assert len(_events(session, "wish_reserved")) == 1


# --- Read-only report CLI ---


def test_conversion_report_help_exits_zero(capsys):
    import importlib

    import pytest

    report = importlib.import_module("jobs.conversion_report")

    # argparse prints help and exits 0 without ever touching the database.
    with pytest.raises(SystemExit) as excinfo:
        report.main(["--help"])

    assert excinfo.value.code == 0
    assert "--days" in capsys.readouterr().out


def test_conversion_report_prints_aggregates(session, capsys, monkeypatch):
    import importlib
    from datetime import datetime

    import database
    from models import ConversionEvent

    report = importlib.import_module("jobs.conversion_report")

    session.add_all([
        ConversionEvent(name="signup", occurred_at=datetime(2026, 10, 8, 10, 0)),
        ConversionEvent(name="signup", occurred_at=datetime(2026, 10, 8, 11, 0)),
        ConversionEvent(name="login", occurred_at=datetime(2026, 10, 8, 12, 0)),
    ])
    session.commit()

    monkeypatch.setattr(database, "get_session", lambda: iter([session]))

    exit_code = report.main(["--days", "3650"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "signup: 2" in output
    assert "login: 1" in output
    assert "2026-10-08: 3" in output
