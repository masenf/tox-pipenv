import pytest
from tox_pipenv.plugin import tox_testenv_install_deps
import subprocess
import os
import sys


def test_install_no_deps(venv, mocker, actioncls):
    """
    Test that nothing is called when there are no deps
    """
    action = actioncls(venv)
    venv.deps = []
    mocker.patch.dict("os.environ")
    mocker.patch("subprocess.Popen")
    result = tox_testenv_install_deps(venv, action)
    assert result == True
    assert subprocess.Popen.call_count == 1
    subprocess.Popen.assert_called_once_with(
        [
            sys.executable,
            "-m",
            "pipenv",
            "install",
            "--dev",
        ],
        action=action,
        cwd=venv.path.dirpath(),
        venv=False,
    )


def test_install_special_deps(venv, mocker, actioncls):
    """
    Test that nothing is called when there are no deps
    """
    action = actioncls(venv)

    venv.deps = ["foo-package", "foo-two-package"]
    mocker.patch.dict("os.environ")
    mocker.patch("subprocess.Popen")
    result = tox_testenv_install_deps(venv, action)
    assert result == True
    assert subprocess.Popen.call_count == 1
    subprocess.Popen.assert_called_once_with(
        [
            sys.executable,
            "-m",
            "pipenv",
            "install",
            "--dev",
            "foo-package",
            "foo-two-package",
        ],
        action=action,
        cwd=venv.path.dirpath(),
        venv=False,
    )



def test_install_pip_pre_deps(venv, mocker, actioncls):
    """
    Test that nothing is called when there are no deps
    """
    action = actioncls(venv)

    venv.deps = ["foo-package", "foo-two-package"]
    mocker.patch.dict("os.environ")
    mocker.patch.object(action.venv.envconfig, 'pip_pre', True)
    mocker.patch("subprocess.Popen")
    result = tox_testenv_install_deps(venv, action)
    assert result == True
    assert subprocess.Popen.call_count == 1
    subprocess.Popen.assert_called_once_with(
        [
            sys.executable,
            "-m",
            "pipenv",
            "install",
            "--dev",
            "--pre",
            "foo-package",
            "foo-two-package",
        ],
        action=action,
        cwd=venv.path.dirpath(),
        venv=False,
    )


@pytest.mark.parametrize(
    "lock_file_name",
    (
        "Pipfile.lock",
        "Pipfile.lock.mock",
    )
)
@pytest.mark.parametrize(
    "deps",
    (
        [],
        ["foo-package", "foo-two-package"],
    ),
)
def test_install_sync(venv, mocker, actioncls, lock_file_name, deps):
    """
    `pipenv sync` is used when a Pipfile.lock is present.

    When `pipenv sync` is used, do not pass a dependency list.
    """
    (venv.session.config.toxinidir / lock_file_name).ensure()
    action = actioncls(venv)

    venv.deps = deps
    mocker.patch.dict("os.environ")
    mocker.patch("subprocess.Popen")
    result = tox_testenv_install_deps(venv, action)
    assert result == True
    assert subprocess.Popen.call_count == 1
    subprocess.Popen.assert_called_once_with(
        [
            sys.executable,
            "-m",
            "pipenv",
            "sync",
        ],
        action=action,
        cwd=venv.path.dirpath(),
        venv=False,
    )
    if not deps:
        assert action.activities == [("installdeps", "[]")]
    else:
        assert action.activities == [("installdeps", "<sync to Pipfile.lock>")]


@pytest.mark.parametrize(
    "lock_file_name",
    (
        None,
        "Pipfile.lock",
        "Pipfile.lock.mock",
    )
)
@pytest.mark.parametrize(
    "deps",
    (
        [],
        ["foo-package", "foo-two-package"],
    ),
)
def test_install_args_override(venv, mocker, actioncls, lock_file_name, deps):
    """
    Check that TOX_PIPENV_INSTALL_ARGS are respected regardless of lock file state.
    """
    if lock_file_name is not None:
        (venv.session.config.toxinidir / lock_file_name).ensure()
    action = actioncls(venv)

    venv.deps = deps
    mocker.patch.dict(
        "os.environ",
        {"TOX_PIPENV_INSTALL_ARGS": "install --deploy -v"},
    )
    mocker.patch("subprocess.Popen")
    exp_command = [
            sys.executable,
            "-m",
            "pipenv",
            "install",
            "--deploy",
            "-v",
    ] + deps
    result = tox_testenv_install_deps(venv, action)
    assert result == True
    assert subprocess.Popen.call_count == 1
    subprocess.Popen.assert_called_once_with(
        exp_command,
        action=action,
        cwd=venv.path.dirpath(),
        venv=False,
    )
