import py.path
import pytest

import tox_pipenv.plugin


DEFAULT_PIPFILE = "Pipfile"


@pytest.fixture(autouse=True)
def reset_pipfile_attributes():
    def _reset_and_assert_defaults():
        tox_pipenv.plugin._init_global_pipfile(None)
        assert tox_pipenv.plugin.PIPFILE_FALLBACK == DEFAULT_PIPFILE
        assert tox_pipenv.plugin.PIPFILE == DEFAULT_PIPFILE + "_{envname}"
        assert tox_pipenv.plugin.PIPFILE_LOCK == DEFAULT_PIPFILE + ".lock"
        assert tox_pipenv.plugin.PIPFILE_LOCK_ENV == DEFAULT_PIPFILE + "_{envname}.lock"
        assert tox_pipenv.plugin.PIPFILE_PARENT is None

    _reset_and_assert_defaults()
    yield
    _reset_and_assert_defaults()


@pytest.mark.parametrize(
    "variable_value, exp_pipfile, exp_pipfile_fallback, exp_pipfile_lock, exp_pipfile_parent",
    (
        (
            "",
            DEFAULT_PIPFILE + "_{envname}",
            DEFAULT_PIPFILE,
            DEFAULT_PIPFILE + ".lock",
            None,
        ),
        (
            DEFAULT_PIPFILE,
            DEFAULT_PIPFILE + "_{envname}",
            DEFAULT_PIPFILE,
            None,
            py.path.local("."),
        ),
        ("Poopfile", "Poopfile_{envname}", "Poopfile", None, py.path.local(".")),
        (
            "/tmp/foo/bar/Pabstfile",
            "Pabstfile_{envname}",
            "Pabstfile",
            None,
            py.path.local("/tmp/foo/bar"),
        ),
    ),
)
def test_pipenv_pipfile_is_set_after_configure(
    monkeypatch,
    variable_value,
    exp_pipfile,
    exp_pipfile_fallback,
    exp_pipfile_lock,
    exp_pipfile_parent,
):
    monkeypatch.setenv("PIPENV_PIPFILE", variable_value)
    tox_pipenv.plugin.tox_configure(None)
    assert tox_pipenv.plugin.PIPFILE == exp_pipfile
    assert tox_pipenv.plugin.PIPFILE_FALLBACK == exp_pipfile_fallback
    assert tox_pipenv.plugin.PIPFILE_LOCK == exp_pipfile_fallback + ".lock"
    assert tox_pipenv.plugin.PIPFILE_LOCK_ENV == exp_pipfile + ".lock"
    assert tox_pipenv.plugin.PIPFILE_PARENT == exp_pipfile_parent
