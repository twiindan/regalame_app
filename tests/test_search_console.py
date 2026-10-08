import importlib
import json
import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

import pytest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"


@pytest.fixture
def sc():
    return importlib.import_module("jobs.search_console")


def test_reporting_window_uses_pacific_calendar(sc):
    start, end = sc.reporting_window(datetime(2026, 1, 1, 3, tzinfo=timezone.utc))
    assert (start, end) == ("2025-10-02", "2025-12-30")


def test_private_atomic_output(sc, tmp_path):
    target = tmp_path / "private" / "export.json"
    sc.write_private(target, {"rows": []})
    assert json.loads(target.read_text()) == {"rows": []}
    assert target.stat().st_mode & 0o777 == 0o600
    assert target.parent.stat().st_mode & 0o777 == 0o700
    sc.write_private(target, {"rows": [1]})
    assert json.loads(target.read_text()) == {"rows": [1]}
    assert list(target.parent.iterdir()) == [target]


@pytest.fixture
def oauth(sc, tmp_path, monkeypatch):
    client = tmp_path / "private" / "client.json"
    config = {"installed": {"client_id": "synthetic", "client_secret": "synthetic",
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token"}}
    sc.write_private(client, config)
    credentials = SimpleNamespace(valid=True, refresh_token="synthetic", scopes=[SCOPE],
                                  granted_scopes=None, client_id="synthetic")
    credentials.to_json = lambda: json.dumps({"scopes": [SCOPE], "client_id": "synthetic",
                                             "token_uri": "https://oauth2.googleapis.com/token"})
    credentials.refresh = Mock()
    flow = Mock()
    flow.run_local_server.return_value = credentials
    factory = Mock(return_value=flow)
    monkeypatch.setattr(InstalledAppFlow, "from_client_config", factory)
    loader = Mock(return_value=credentials)
    monkeypatch.setattr(Credentials, "from_authorized_user_info", loader)
    return SimpleNamespace(client=client, token=client.parent / "token.json", config=config,
                           credentials=credentials, flow=flow, factory=factory, loader=loader,
                           request=flow.oauth2session.request)


def test_oauth_pkce_loopback_and_bounded_requests(sc, oauth):
    assert sc.load_credentials(oauth.client, oauth.token) is oauth.credentials
    oauth.factory.assert_called_once_with(oauth.config, scopes=[sc.SCOPE],
                                          autogenerate_code_verifier=True)
    options = oauth.flow.run_local_server.call_args.kwargs
    assert options == {"host": "127.0.0.1", "bind_addr": "127.0.0.1", "port": 0,
                       "timeout_seconds": 180, "authorization_prompt_message": "",
                       "open_browser": True, "access_type": "offline", "prompt": "consent"}
    # requests-oauthlib fetch_token explicitly passes timeout=None by default.
    oauth.flow.oauth2session.request("POST", "https://oauth2.googleapis.com/token", timeout=None)
    assert oauth.request.call_args.kwargs["timeout"] == 30
    assert oauth.request.call_args.kwargs["allow_redirects"] is False
    assert oauth.flow.oauth2session.trust_env is False
    assert oauth.token.stat().st_mode & 0o777 == 0o600


def test_reuse_and_refresh_without_browser(sc, oauth):
    sc.write_private(oauth.token, json.loads(oauth.credentials.to_json()))
    assert sc.load_credentials(oauth.client, oauth.token) is oauth.credentials
    oauth.factory.assert_not_called()
    oauth.credentials.valid = False
    assert sc.load_credentials(oauth.client, oauth.token) is oauth.credentials
    request = oauth.credentials.refresh.call_args.args[0]
    assert request.keywords["timeout"] == 30
    assert request.keywords["allow_redirects"] is False
    assert request.func.session.trust_env is False
    oauth.factory.assert_not_called()


@pytest.mark.parametrize("fault", ["scope", "client", "revoked", "no_refresh", "malformed", "endpoint"])
def test_session_faults_require_explicit_reauthorization(sc, oauth, fault):
    data = json.loads(oauth.credentials.to_json())
    if fault == "scope":
        data["scopes"].append("unexpected")
    elif fault == "client":
        data["client_id"] = "different"
    elif fault == "endpoint":
        data["token_uri"] = "https://invalid.example/token"
    elif fault == "revoked":
        oauth.credentials.valid = False
        oauth.credentials.refresh.side_effect = ValueError("synthetic secret")
    elif fault == "no_refresh":
        oauth.credentials.valid = False
        oauth.credentials.refresh_token = None
    sc.write_private(oauth.token, data)
    if fault == "malformed":
        oauth.token.write_text("not JSON")
    with pytest.raises(sc.SafeError, match="--reauthorize") as caught:
        sc.load_credentials(oauth.client, oauth.token)
    assert "synthetic secret" not in str(caught.value)
    oauth.factory.assert_not_called()


def test_explicit_reauthorization_and_oauth_failure(sc, oauth):
    sc.write_private(oauth.token, {})
    sc.load_credentials(oauth.client, oauth.token, reauthorize=True)
    oauth.flow.run_local_server.side_effect = RuntimeError("synthetic secret")
    with pytest.raises(sc.SafeError, match="OAuth authorization failed") as caught:
        sc.load_credentials(oauth.client, oauth.token, reauthorize=True)
    assert "synthetic secret" not in str(caught.value)


def test_rejects_non_desktop_client_and_non_google_endpoint(sc, oauth):
    for config in [{"web": oauth.config["installed"]},
                   {"installed": {**oauth.config["installed"], "auth_uri": "https://invalid.example"}}]:
        sc.write_private(oauth.client, config)
        with pytest.raises(sc.SafeError, match="desktop client"):
            sc.load_credentials(oauth.client, oauth.token)
    oauth.factory.assert_not_called()


@pytest.mark.parametrize("kind", ["repository", "symlink", "parent_link", "public", "hardlink"])
def test_rejects_unsafe_storage(sc, tmp_path, kind):
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    target = private / "token.json"
    if kind == "repository":
        target = sc.REPO / "never-write-token.json"
    elif kind == "symlink":
        target.symlink_to(tmp_path / "elsewhere")
    elif kind == "parent_link":
        link = tmp_path / "link"
        link.symlink_to(private, target_is_directory=True)
        target = link / "token.json"
    elif kind == "public":
        private.chmod(0o755)
    else:
        target.write_text("synthetic")
        target.chmod(0o600)
        os.link(target, private / "other")
    with pytest.raises(sc.SafeError, match="storage"):
        sc.write_private(target, {})


def test_atomic_failure_keeps_existing_file(sc, tmp_path, monkeypatch):
    target = tmp_path / "private" / "token.json"
    sc.write_private(target, {"old": True})
    monkeypatch.setattr(sc.os, "replace", lambda *a: (_ for _ in ()).throw(OSError("private")))
    with pytest.raises(OSError):
        sc.write_private(target, {"new": True})
    assert json.loads(target.read_text()) == {"old": True}
    assert list(target.parent.iterdir()) == [target]


def test_official_library_pkce_and_state_without_network():
    from oauthlib.oauth2 import MismatchingStateError

    flow = InstalledAppFlow.from_client_config(
        {"installed": {"client_id": "synthetic", "client_secret": "synthetic",
                       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                       "token_uri": "https://oauth2.googleapis.com/token"}},
        scopes=[SCOPE], autogenerate_code_verifier=True,
    )
    url, state = flow.authorization_url()
    parameters = parse_qs(urlparse(url).query)
    assert parameters["code_challenge_method"] == ["S256"]
    assert bool(parameters["code_challenge"][0])
    assert parameters["state"] == [state]
    with pytest.raises(MismatchingStateError):
        flow.fetch_token(authorization_response="https://127.0.0.1/?state=wrong&code=synthetic")


def test_baseline_report_shape_and_section_order(sc):
    session = Mock()
    session.post.return_value = Mock(status_code=200, json=Mock(return_value={"rows": []}))
    export = sc.query_baseline(session, now=datetime(2026, 1, 1, 3, tzinfo=timezone.utc), row_limit=25000)
    assert session.post.call_count == len(sc.SECTIONS)
    for call, (name, dimensions) in zip(session.post.call_args_list, sc.SECTIONS):
        assert call.args == (sc.QUERY_URL,)
        assert call.kwargs == {
            "json": {"startDate": "2025-10-02", "endDate": "2025-12-30", "dimensions": dimensions,
                     "type": "web", "dataState": "final", "rowLimit": 25000, "startRow": 0},
            "timeout": 30, "allow_redirects": False,
        }
    assert export["property"] == "sc-domain:regalame.app"
    assert export["startDate"] == "2025-10-02"
    assert export["endDate"] == "2025-12-30"
    assert export["type"] == "web"
    assert export["dataState"] == "final"
    assert export["timezone"] == "America/Los_Angeles"
    assert "privacy" in export["limitations"]
    assert export["section_dimensions"] == {name: list(dimensions) for name, dimensions in sc.SECTIONS}
    assert export["sections"] == {name: [] for name, _ in sc.SECTIONS}
    assert "rows" not in export


def test_baseline_section_pagination_advances_start_row(sc):
    session = Mock()
    totals_full = Mock(status_code=200, json=Mock(return_value={"rows": [{"key": "totals"}]}))
    totals_short = Mock(status_code=200, json=Mock(return_value={"rows": []}))
    empties = [Mock(status_code=200, json=Mock(return_value={"rows": []})) for _ in range(4)]
    session.post.side_effect = [totals_full, totals_short, *empties]
    export = sc.query_baseline(session, now=datetime(2026, 1, 1, 3, tzinfo=timezone.utc), row_limit=1)
    assert export["sections"]["totals"] == [{"key": "totals"}]
    # Empty first pages stop immediately: one request for byDate plus the last three sections.
    assert session.post.call_count == 6
    first, second, *remaining = session.post.call_args_list
    assert first.kwargs["json"]["startRow"] == 0
    assert second.kwargs["json"]["startRow"] == 1
    assert first.kwargs["json"]["dimensions"] == []
    assert {key: value for key, value in second.kwargs["json"].items() if key != "startRow"} == \
           {key: value for key, value in first.kwargs["json"].items() if key != "startRow"}
    assert all(call.kwargs["json"]["startRow"] == 0 for call in remaining)


@pytest.mark.parametrize("fault", ["http", "network", "json", "shape"])
def test_api_errors_are_sanitized(sc, fault):
    session = Mock()
    if fault == "network":
        session.post.side_effect = RuntimeError("synthetic secret")
    elif fault == "shape":
        session.post.return_value = Mock(status_code=200, json=Mock(return_value={"rows": {}}))
    else:
        session.post.return_value = Mock(status_code=403 if fault == "http" else 200)
        session.post.return_value.json.side_effect = ValueError("synthetic secret")
    with pytest.raises(sc.SafeError, match="Search Console request failed") as caught:
        sc.query_baseline(session)
    assert "synthetic secret" not in str(caught.value)
    assert session.post.call_count == 1


def test_cli_fake_boundaries_repeat_run(sc, oauth, monkeypatch, capsys):
    import google.auth.transport.requests

    session = Mock()
    session.post.return_value = Mock(status_code=200, json=Mock(return_value={"rows": []}))
    factory = Mock(return_value=session)
    monkeypatch.setattr(google.auth.transport.requests, "AuthorizedSession", factory)
    output = oauth.client.parent / "export.json"
    args = ["--client-secret", str(oauth.client), "--token", str(oauth.token), "--output", str(output)]
    assert sc.main(args) == 0
    assert sc.main(args) == 0
    assert oauth.factory.call_count == 1
    assert oauth.loader.call_count == 1
    options = factory.call_args.kwargs
    assert options["refresh_timeout"] == 30
    assert options["max_refresh_attempts"] == 0
    assert options["auth_request"].func.session.trust_env is False
    assert options["auth_request"].keywords["allow_redirects"] is False
    assert session.close.call_count == 2
    assert session.trust_env is False
    saved = json.loads(output.read_text())
    assert saved["sections"] == {name: [] for name, _ in sc.SECTIONS}
    assert saved["section_dimensions"] == {name: list(dimensions) for name, dimensions in sc.SECTIONS}
    assert "rows" not in saved
    assert output.stat().st_mode & 0o777 == 0o600
    captured = capsys.readouterr()
    assert captured.out == "Private export saved.\n" * 2
    assert captured.err == ""


def test_cli_rejects_property_before_reading_client(sc, monkeypatch, capsys):
    loader = Mock()
    monkeypatch.setattr(sc, "load_credentials", loader)
    assert sc.main(["--property", "sc-domain:other.example", "--client-secret", "/synthetic",
                    "--token", "/synthetic-token", "--output", "/synthetic-export"]) == 1
    loader.assert_not_called()
    assert "Only sc-domain:regalame.app is permitted" in capsys.readouterr().err


def test_cli_sanitizes_unexpected_errors(sc, oauth, monkeypatch, capsys):
    monkeypatch.setattr(sc, "load_credentials", Mock(side_effect=ValueError("synthetic secret")))
    assert sc.main(["--client-secret", str(oauth.client), "--token", str(oauth.token),
                    "--output", str(oauth.client.parent / "export.json")]) == 1
    assert capsys.readouterr().err == "Local export failed; check private paths and authorization.\n"


def test_rejects_writable_ancestor(sc, tmp_path):
    public = tmp_path / "public"
    public.mkdir(mode=0o777)
    public.chmod(0o777)
    private = public / "private"
    private.mkdir(mode=0o700)
    with pytest.raises(sc.SafeError, match="storage"):
        sc.write_private(private / "token.json", {})


def test_cli_rejects_colliding_paths_before_auth(sc, oauth, monkeypatch, capsys):
    loader = Mock()
    monkeypatch.setattr(sc, "load_credentials", loader)
    assert sc.main(["--client-secret", str(oauth.client), "--token", str(oauth.token),
                    "--output", str(oauth.token)]) == 1
    loader.assert_not_called()
    assert "storage" in capsys.readouterr().err
