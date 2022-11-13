import subprocess
import sys

import pytest

from tox_pipenv.plugin import (
    tox_runenvreport,
    _pipenv_env,
    _clone_pipfile,
    ToxPipenvError,
)


@pytest.mark.usefixtures("default_install_command")
@pytest.mark.parametrize(
    "do_clone_pipfile",
    [True, False],
)
@pytest.mark.parametrize(
    "deps",
    (
        [],
        ["foo"],
    ),
)
@pytest.mark.usefixtures("mock_for_Popen")
def test_runenvreport(
    venv, deps, action, has_pipfile, has_pipfile_lock, has_skip_pipenv, do_clone_pipfile
):
    """
    Test that report only runs when the plugin is active.
    """
    venv.deps = deps
    exp_plugin_ran = not (deps or has_skip_pipenv)

    if exp_plugin_ran:
        cloned_pipfile = None
        if do_clone_pipfile:
            # the report will skip unless venv-specific Pipfile is present
            cloned_pipfile, cloned_pipfile_lock = _clone_pipfile(venv)

            if has_pipfile:
                assert cloned_pipfile is not None
            else:
                assert cloned_pipfile is None

            if has_pipfile_lock:
                assert cloned_pipfile_lock is not None
            else:
                assert cloned_pipfile_lock is None

        if (has_pipfile or has_pipfile_lock) and cloned_pipfile is None:
            # running the report without Pipfile or `_clone_pipfile` is always an error
            with pytest.raises(ToxPipenvError):
                _ = tox_runenvreport(venv, action)
            return

    result = tox_runenvreport(venv, action)

    if not exp_plugin_ran or not has_pipfile:
        assert result is None
        return
    assert result is not None
    subprocess.Popen.assert_called_once_with(
        [
            sys.executable,
            "-m",
            "pipenv",
            "graph",
        ],
        action=action,
        cwd=venv.path.dirpath(),
        env=_pipenv_env(venv),
    )
