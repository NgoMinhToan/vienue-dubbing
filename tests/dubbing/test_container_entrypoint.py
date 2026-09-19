import runpy
from pathlib import Path

import pytest


@pytest.fixture
def entrypoint(monkeypatch):
    main = runpy.run_path(str(Path(__file__).resolve().parents[2] / "docker/entrypoint.py"))["main"]
    env = main.__globals__["os"]
    monkeypatch.delenv("UID", raising=False)
    monkeypatch.delenv("GID", raising=False)
    monkeypatch.setattr(env, "geteuid", lambda: 0, raising=False)
    monkeypatch.setattr(env, "getegid", lambda: 0, raising=False)
    calls = []
    for name in ("setgroups", "setgid", "setuid"):
        monkeypatch.setattr(env, name, lambda value, name=name: calls.append((name, value)), raising=False)
    monkeypatch.setattr(env, "execvp", lambda *args: calls.append(("exec", args)))
    monkeypatch.setattr(main.__globals__["sys"], "argv", ["entrypoint.py", "python", "scripts/start.py"])
    return main, calls, env


@pytest.mark.parametrize("values,expected", [({}, []), ({"UID": "1234", "GID": "2345"}, [1234, 2345]), ({"UID": "1234"}, [1234, 1000]), ({"GID": "2345"}, [1000, 2345]), ({"UID": "0", "GID": "0"}, [0, 0])])
def test_identity_and_exec(entrypoint, monkeypatch, values, expected):
    main, calls, _ = entrypoint
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    main()
    changes = [("setgroups", []), ("setgid", expected[1]), ("setuid", expected[0])] if expected else []
    assert calls == changes + [("exec", ("python", ["python", "scripts/start.py"]))]


@pytest.mark.parametrize("value", ["", "abc", "-1", "1.5", "4294967295", "１０００"])
def test_invalid_identity_stops_startup(entrypoint, monkeypatch, value):
    main, calls, _ = entrypoint
    monkeypatch.setenv("UID", value)
    with pytest.raises(SystemExit, match="1"):
        main()
    assert calls == []


def test_explicit_docker_user_is_preserved(entrypoint, monkeypatch):
    main, calls, env = entrypoint
    monkeypatch.setattr(env, "geteuid", lambda: 1234)
    main()
    assert [call[0] for call in calls] == ["exec"]


def test_conflicting_docker_user_stops_startup(entrypoint, monkeypatch):
    main, calls, env = entrypoint
    monkeypatch.setattr(env, "geteuid", lambda: 1234)
    monkeypatch.setenv("UID", "1000")
    with pytest.raises(SystemExit, match="1"):
        main()
    assert calls == []
