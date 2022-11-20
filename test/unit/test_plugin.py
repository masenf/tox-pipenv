"""
Miscellaneous plugin-specific unit tests.

Many of these tests are "brittle" and may need to be removed or rewritten when
plugin internals change.
"""
import pytest

import tox_pipenv.plugin


@pytest.mark.parametrize(
    "pipfile_parent",
    (True, None),
)
def test_try_pipfile_lock_names(monkeypatch, venv, pipfile_parent):
    """Test pipfile lock fallback when PIPFILE_PARENT is set (from PIPFILE_PIPENV)."""
    monkeypatch.setattr(tox_pipenv.plugin, "PIPFILE_PARENT", pipfile_parent)
    try_pipfile_lock_names = tox_pipenv.plugin._try_pipfile_lock_names(venv)
    assert next(try_pipfile_lock_names) == tox_pipenv.plugin.PIPFILE_LOCK_ENV.format(
        envname=venv.envconfig.envname
    )
    if pipfile_parent:
        assert next(try_pipfile_lock_names) == tox_pipenv.plugin.PIPFILE_LOCK
    else:
        with pytest.raises(StopIteration):
            next(try_pipfile_lock_names)
