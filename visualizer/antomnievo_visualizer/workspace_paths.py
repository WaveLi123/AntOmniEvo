"""Workspace path helpers shared by the launcher and the API server.

Deliberately dependency-free (stdlib only) so ``manage.py`` can import it
without pulling in Flask or the optimization stack.
"""

import os


def is_workspace_dir(path: str) -> bool:
    """A workspace root is an optimization run directory, i.e. one with candidates/."""
    return os.path.isdir(os.path.join(path, 'candidates'))


def resolve_workspace(path: str) -> str:
    """Normalize a user-supplied workspace path and check it is a run directory.

    Expands ``~``, makes the path absolute, and verifies it exists and contains a
    ``candidates/`` directory. Returns the absolute path.

    Raises:
        ValueError: with a human-readable reason when the path is not a valid
            workspace (missing, not a directory, or no ``candidates/``).
    """
    resolved = os.path.abspath(os.path.expanduser(path))
    if not os.path.isdir(resolved):
        raise ValueError(f'path does not exist or is not a directory: {resolved}')
    if not is_workspace_dir(resolved):
        raise ValueError(f'not an optimization workspace (no candidates/ directory): {resolved}')
    return resolved
