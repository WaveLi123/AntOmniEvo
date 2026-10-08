import os


def get_latest_mtime(dir_path: str) -> float:
    """Return the most recent modification time of any file under dir_path."""
    latest = 0.0
    for root, _, files in os.walk(dir_path):
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                mt = os.path.getmtime(fpath)
                if mt > latest:
                    latest = mt
            except OSError:
                continue
    return latest


def is_noise(name: str) -> bool:
    """True for an entry that is editor / VCS / interpreter noise.

    Hidden entries (leading dot) and Python bytecode caches (``__pycache__``)
    are never part of a tunable artifact.
    """
    return name.startswith(".") or name == "__pycache__"


def snapshot_files(dir_path: str) -> dict[str, tuple[int, int]]:
    """Return ``{relative_path: (mtime_ns, size)}`` for every file under dir_path.

    Comparing two snapshots detects added, modified, and deleted files; the
    latest mtime alone misses deletions, since removing a file leaves the
    remaining files' timestamps unchanged.

    Entries for which ``is_noise`` holds are skipped, so that merely importing
    the artifacts is not mistaken for mutating them.
    """
    snapshot: dict[str, tuple[int, int]] = {}
    for root, dirs, files in os.walk(dir_path):
        dirs[:] = [d for d in dirs if not is_noise(d)]
        for fname in files:
            if is_noise(fname):
                continue
            fpath = os.path.join(root, fname)
            try:
                st = os.stat(fpath)
            except OSError:
                continue
            snapshot[os.path.relpath(fpath, dir_path)] = (st.st_mtime_ns, st.st_size)
    return snapshot


def file_written_since(path: str, since_ts: float, eps: float = 1e-3) -> bool:
    """True if `path` exists and was modified at or after `since_ts` (epoch seconds).

    Used to verify an agent actually (re)wrote its output file during its run —
    a pre-existing stale file does not count. `eps` tolerates coarse filesystem
    timestamp granularity.
    """
    try:
        return os.path.getmtime(path) >= since_ts - eps
    except OSError:
        return False
