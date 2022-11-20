import shlex
import subprocess
import sys

import pytest

import tox_pipenv.plugin
from tox_pipenv.plugin import tox_testenv_install_deps, _pipenv_env


@pytest.mark.usefixtures("default_install_command")
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
    result = tox_testenv_install_deps(venv, action)

    exp_cmd = "install"
    exp_args = []
    if exp_plugin_ran:
        assert result is True
        if has_pipenv_update:
            exp_cmd = "update"
        elif has_pipfile_lock:
            exp_args.append("--ignore-pipfile")
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
        None,
        "Pipfile",
        "Pipfile_mock.lock",
    ),
)
@pytest.mark.parametrize(
    "install_command",
    (
        "pipenv install --deploy -v {opts} {packages}",
        "python -m pipenv update {opts}",
        "foo bar",
    ),
)
@pytest.mark.parametrize(
    "deps",
    (
        [],
        ["foo"],
    ),
)
def test_install_override(
    venv,
    mocker,
    action,
    touch_file_name,
    install_command,
    deps,
    has_pipenv_update,
):
    """
    Check that overrides are respected regardless of lock file state.
    """
    if touch_file_name is not None:
        (venv.session.config.toxinidir / touch_file_name).ensure()
    install_command_shlex = shlex.split(install_command)
    venv.envconfig.install_command = install_command_shlex
    if deps:
        mocker.patch("tox_pipenv.plugin._deps", return_value=deps)
    mocker.patch("subprocess.Popen")
    if "pipenv" not in install_command_shlex:
        if has_pipenv_update:
            with pytest.raises(tox_pipenv.plugin.ToxPipenvError):
                _ = tox_testenv_install_deps(venv, action)
            return
    result = tox_testenv_install_deps(venv, action)
    if "pipenv" not in install_command_shlex:
        assert result is None
        return
    assert result is True
    assert subprocess.Popen.call_count == 1
    subprocess.Popen.assert_called_once_with(
        shlex.split(
            install_command.replace("python", sys.executable).format(
                opts="", packages=" ".join(deps)
            )
        ),
        action=action,
        cwd=venv.path.dirpath(),
        env=_pipenv_env(venv),
    )
