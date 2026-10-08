"""Tests for the visualizer API server's access controls."""

import os
import tempfile

import pytest

pytest.importorskip("flask")
pytest.importorskip("flask_cors")

from antomnievo_visualizer import server


@pytest.fixture(scope="module", autouse=True)
def loopback_security():
    server.configure_security("127.0.0.1", 5173)
    yield
    server.ALLOWED_HOSTS = None


@pytest.fixture
def client():
    server.WORKSPACE_ROOT = None
    with server.app.test_client() as c:
        yield c
    server.WORKSPACE_ROOT = None


@pytest.fixture
def workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "candidates"))
        yield tmpdir


def _set_workspace(client, path):
    return client.post("/api/config/workspace", json={"path": path})


class TestWorkspaceConfig:
    def test_rejects_non_workspace_dir(self, client):
        resp = _set_workspace(client, "/")
        assert resp.status_code == 400
        assert server.WORKSPACE_ROOT is None

    def test_accepts_workspace_dir(self, client, workspace):
        resp = _set_workspace(client, workspace)
        assert resp.status_code == 200
        assert workspace == server.WORKSPACE_ROOT

    def test_file_outside_workspace_is_rejected(self, client, workspace):
        _set_workspace(client, workspace)
        resp = client.get("/api/file", query_string={"file": "/etc/hosts"})
        assert resp.status_code == 403

    def test_open_directory_rejects_traversal(self, client, workspace):
        _set_workspace(client, workspace)
        resp = client.post("/api/open-directory", json={"candidate_id": "../.."})
        assert resp.status_code == 403


class TestHostHeader:
    def test_loopback_host_allowed(self, client):
        assert client.get("/health", headers={"Host": "localhost:3001"}).status_code == 200
        assert client.get("/health", headers={"Host": "127.0.0.1:3001"}).status_code == 200
        assert client.get("/health", headers={"Host": "[::1]:3001"}).status_code == 200

    def test_foreign_host_rejected(self, client):
        resp = client.get("/health", headers={"Host": "attacker.example:3001"})
        assert resp.status_code == 403


class TestCors:
    def test_frontend_origin_allowed(self, client):
        resp = client.get("/health", headers={"Origin": "http://localhost:5173"})
        assert resp.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"

    def test_other_origin_not_allowed(self, client):
        resp = client.get("/health", headers={"Origin": "http://attacker.example"})
        assert "Access-Control-Allow-Origin" not in resp.headers


class TestCsrfOrigin:
    """State-changing requests must come from the frontend origin (or no origin)."""

    def test_cross_origin_post_rejected(self, client, workspace):
        resp = _set_workspace(client, workspace)
        assert resp.status_code == 200  # baseline: no Origin header -> allowed

        resp = client.post(
            "/api/config/workspace",
            json={"path": workspace},
            headers={"Origin": "http://attacker.example"},
        )
        assert resp.status_code == 403
        assert server.WORKSPACE_ROOT == workspace  # state not changed

    def test_frontend_origin_post_allowed(self, client, workspace):
        resp = client.post(
            "/api/config/workspace",
            json={"path": workspace},
            headers={"Origin": "http://localhost:5173"},
        )
        assert resp.status_code == 200

    def test_referer_used_when_origin_absent(self, client, workspace):
        resp = client.post(
            "/api/config/workspace",
            json={"path": workspace},
            headers={"Referer": "http://127.0.0.1:5173/some/page"},
        )
        assert resp.status_code == 200

        resp = client.post(
            "/api/config/workspace",
            json={"path": workspace},
            headers={"Referer": "http://attacker.example/some/page"},
        )
        assert resp.status_code == 403


class TestAllowedOrigins:
    def test_loopback_bind_allows_local_frontend(self):
        origins = server._allowed_origins("127.0.0.1", 5173, [])
        assert "http://localhost:5173" in origins
        assert "http://127.0.0.1:5173" in origins

    def test_concrete_bind_host_origin_added(self):
        origins = server._allowed_origins("192.168.1.5", 5173, [])
        assert "http://192.168.1.5:5173" in origins

    def test_extra_origins_appended(self):
        origins = server._allowed_origins("127.0.0.1", 5173, ["http://example.test:5173"])
        assert "http://example.test:5173" in origins

    def test_wildcard_bind_still_allows_local_frontend(self):
        origins = server._allowed_origins("0.0.0.0", 5173, [])
        assert "http://localhost:5173" in origins
        assert "http://127.0.0.1:5173" in origins
