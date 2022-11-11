import subprocess
import sys

import pytest

import tox_pipenv.plugin
from tox_pipenv.plugin import tox_testenv_install_deps, _pipenv_env


@pytest.mark.parametrize(
    "deps",
    (
        [],
        ["foo"],
    ),
)
@pytest.mark.usefixtures("mock_for_Popen")
def test_install_deps(
    venv,
    deps,
    action,
    has_pipfile,
    has_pipfile_lock,
    has_pip_pre,
    has_skip_pipenv,
    has_pipenv_update,
):
    """
    Test that the plugin is active when deps are empty and a Pipfile is present.
    """
    venv.deps = deps
    exp_plugin_ran = not (deps or has_skip_pipenv) and (has_pipfile or has_pipfile_lock)

    if has_pipenv_update and (not exp_plugin_ran or not has_pipfile):
        with pytest.raises(tox_pipenv.plugin.ToxPipenvError):
            _ = tox_testenv_install_deps(venv, action)
        return
    else:
        result = tox_testenv_install_deps(venv, action)

    exp_cmd = "install"
    exp_args = []
    if exp_plugin_ran:
        assert result is True
        if has_pipenv_update:
            exp_cmd = "update"
        elif has_pipfile_lock or has_pipenv_update:
            exp_cmd = "sync"
        if has_pip_pre:
            exp_args.append("--pre")
    else:
        assert result is None
        return

    if has_pipenv_update:
        toxinidir_lock_file = (
            venv.envconfig.config.toxinidir
            / tox_pipenv.plugin.PIPFILE_LOCK_ENV.format(
                envname=venv.envconfig.envname,
            )
        )
        assert toxinidir_lock_file.exists()
        assert toxinidir_lock_file.read() == has_pipenv_update
    assert subprocess.Popen.call_count == 1
    subprocess.Popen.assert_called_with(
        [
            sys.executable,
            "-m",
            "pipenv",
            exp_cmd,
        ]
        + exp_args,
        action=action,
        cwd=venv.path.dirpath(),
        env=_pipenv_env(venv),
    )


@pytest.mark.parametrize(
    "lock_file_name",
    (
        "Pipfile.lock",
        "Pipfile.lock.foo",
    ),
)
def test_pipfile_non_venv_lock(venv, mocker, action, lock_file_name):
    """
    Plugin is not active when `Pipfile.lock` or `Pipfile.lock.foo` present.
    """
    (venv.session.config.toxinidir / lock_file_name).ensure()
    mocker.patch.dict("os.environ")
    mocker.patch("subprocess.Popen")
    result = tox_testenv_install_deps(venv, action)
    assert result is None
    assert subprocess.Popen.call_count == 0


@pytest.mark.parametrize(
    "touch_file_name",
    (
        "Pipfile",
        "Pipfile.lock.mock",
    ),
)
@pytest.mark.parametrize(
    "set_where",
    (
        "venv",
        "environ",
    ),
)
def test_install_override(venv, mocker, action, touch_file_name, set_where):
    """
    Check that overrides are respected regardless of lock file state.
    """
    if touch_file_name is not None:
        (venv.session.config.toxinidir / touch_file_name).ensure()
    cmd = "foo"
    opts = "--deploy -v"
    opts_shlex = ["--deploy", "-v"]
    if set_where == "environ":
        mocker.patch.dict(
            "os.environ",
            {"TOX_PIPENV_INSTALL_CMD": cmd},
        )
        mocker.patch.dict(
            "os.environ",
            {"TOX_PIPENV_INSTALL_OPTS": opts},
        )
    else:
        venv.envconfig.pipenv_install_cmd = cmd
        venv.envconfig.pipenv_install_opts = opts
    mocker.patch("subprocess.Popen")
    exp_command = [
        sys.executable,
        "-m",
        "pipenv",
        cmd,
    ] + opts_shlex
    result = tox_testenv_install_deps(venv, action)
    assert result is True
    assert subprocess.Popen.call_count == 1
    subprocess.Popen.assert_called_once_with(
        exp_command,
        action=action,
        cwd=venv.path.dirpath(),
        env=_pipenv_env(venv),
    )
