import pytest

from tox_pipenv.plugin import _pipenv_env, _venv_pipfile, ToxPipenvError


@pytest.mark.parametrize("pipfile_path", [None, "/tmp/foo/Pizfile"])
def test_pipenv_env(venv, has_pipfile, pipfile_path):
    exp_pipfile_path = pipfile_path
    if pipfile_path is None:
        if has_pipfile:
            exp_pipfile_path, _ = _venv_pipfile(venv)
    if exp_pipfile_path is None:
        with pytest.raises(ToxPipenvError):
            _ = _pipenv_env(venv, pipfile_path=pipfile_path)
        return
    env = _pipenv_env(venv, pipfile_path=pipfile_path)
    assert env["PIPENV_PIPFILE"] == str(exp_pipfile_path)
    assert env["VIRTUAL_ENV"] == str(venv.path)
