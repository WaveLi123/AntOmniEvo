"""Tests for the shared workspace path helpers (stdlib-only, no Flask needed)."""

import pytest

from antomnievo_visualizer.workspace_paths import is_workspace_dir, resolve_workspace


@pytest.fixture
def run_dir(tmp_path):
    (tmp_path / "candidates").mkdir()
    return tmp_path


class TestIsWorkspaceDir:
    def test_true_when_candidates_present(self, run_dir):
        assert is_workspace_dir(str(run_dir))

    def test_false_without_candidates(self, tmp_path):
        assert not is_workspace_dir(str(tmp_path))

    def test_false_for_missing_path(self, tmp_path):
        assert not is_workspace_dir(str(tmp_path / "nope"))


class TestResolveWorkspace:
    def test_returns_the_absolute_path(self, run_dir):
        assert resolve_workspace(str(run_dir)) == str(run_dir)

    def test_expands_user_home(self, run_dir, monkeypatch):
        monkeypatch.setenv("HOME", str(run_dir.parent))
        assert resolve_workspace(f"~/{run_dir.name}") == str(run_dir)

    def test_rejects_missing_dir(self, tmp_path):
        with pytest.raises(ValueError, match="not a directory"):
            resolve_workspace(str(tmp_path / "nope"))

    def test_rejects_dir_without_candidates(self, tmp_path):
        with pytest.raises(ValueError, match="no candidates/"):
            resolve_workspace(str(tmp_path))
