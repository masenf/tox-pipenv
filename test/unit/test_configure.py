import py.path
import pytest

import tox_pipenv.plugin


DEFAULT_PIPFILE = "Pipfile"


@pytest.fixture(autouse=True)
def reset_pipfile_attributes():
    tox_pipenv.plugin._init_global_pipfile(None)
    yield
    tox_pipenv.plugin._init_global_pipfile(None)


@pytest.mark.parametrize(
    "variable_value, exp_pipfile, exp_pipfile_parent",
    (
        ("", DEFAULT_PIPFILE, None),
        ("Poopfile", "Poopfile", py.path.local(".")),
        ("/tmp/foo/bar/Pabstfile", "Pabstfile", py.path.local("/tmp/foo/bar")),
    ),
)
def test_pipenv_pipfile_is_set_after_configure(
    monkeypatch,
    variable_value,
    exp_pipfile,
    exp_pipfile_parent,
):
    monkeypatch.setenv("PIPENV_PIPFILE", variable_value)
    assert tox_pipenv.plugin.PIPFILE == DEFAULT_PIPFILE
    assert tox_pipenv.plugin.PIPFILE_LOCK == DEFAULT_PIPFILE + ".lock"
    assert tox_pipenv.plugin.PIPFILE_LOCK_ENV == DEFAULT_PIPFILE + ".lock.{envname}"
    assert tox_pipenv.plugin.PIPFILE_PARENT is None
    tox_pipenv.plugin.tox_configure(None)
    assert tox_pipenv.plugin.PIPFILE == exp_pipfile
    assert tox_pipenv.plugin.PIPFILE_LOCK == exp_pipfile + ".lock"
    assert tox_pipenv.plugin.PIPFILE_LOCK_ENV == exp_pipfile + ".lock.{envname}"
    assert tox_pipenv.plugin.PIPFILE_PARENT == exp_pipfile_parent
