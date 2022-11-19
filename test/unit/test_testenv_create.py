import subprocess
import sys

import pytest

from tox_pipenv.plugin import tox_testenv_create, _pipenv_env


@pytest.mark.usefixtures("mock_for_Popen")
def test_create(
    venv,
    action,
    has_pipfile,
    has_pipfile_lock,
    has_skip_pipenv,
    pipenv_venv,
    sitepackages,
):
    """
    Test that the plugin is active when deps are empty and a Pipfile is present.
    """
    exp_plugin_ran = (
        pipenv_venv and not has_skip_pipenv and (has_pipfile or has_pipfile_lock)
    )

    result = tox_testenv_create(venv, action)

    exp_args = []
    if exp_plugin_ran:
        assert result is True
        if sitepackages:
            exp_args.append("--site-packages")
        exp_args.extend(("--python", "test-python"))
    else:
        assert result is None
        return
    assert subprocess.Popen.call_count == 1
    subprocess.Popen.assert_called_with(
        [
            sys.executable,
            "-m",
            "pipenv",
        ]
        + exp_args,
        action=action,
        cwd=venv.path.dirpath(),
        env=_pipenv_env(venv),
    )
