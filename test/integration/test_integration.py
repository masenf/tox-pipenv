import glob
import sys
import shlex

import pytest

from .data import (
    PIPFILE_SIMPLE,
    PIPFILE_SIMPLE_LOCK,
    TOX_INI_DEPS_SIMPLE,
    TOX_INI_PIPFILE_SIMPLE,
    TOX_INI_SKIP_PIPENV,
)


pytest_plugins = ["pytester"]


def _expect_tox_to_fail(
    pass_pipenv_update,
    install_command,
    use_pipfile,
    use_pipfile_lock_env,
):
    """
    Return True if we expect tox to fail under the given circumstances.

    An attempt to express these complicated combinations in ways that
    might make sense to future maintainers.
    """
    # condition raised early in tox_testenv_install_deps near _should_skip
    want_update_but_will_raise = (
        pass_pipenv_update and not use_pipfile and not use_pipfile_lock_env
    )
    # condition raised in plugin._install_args
    want_update_but_no_pipfile = pass_pipenv_update and not use_pipfile
    default_install_command = install_command is None
    want_update_but_no_pipenv_in_command = install_command and (
        pass_pipenv_update and "pipenv" not in install_command
    )
    return (
        default_install_command
        and (want_update_but_will_raise or want_update_but_no_pipfile)
        or want_update_but_no_pipenv_in_command
    )


def test_end_to_end(
    pytester,
    tox_ini,
    use_pipfile,
    use_pipfile_lock_env,
    pass_pipenv_update,
    install_command,
    pip_pre,
):
    """Call tox and validate the `pip freeze` output."""
    command = [sys.executable, "-m", "tox"]
    if not use_pipfile_lock_env:
        assert not (pytester.path / "Pipfile_py.lock").exists()
    if pass_pipenv_update:
        command.append("--pipenv-update")
    result = pytester.run(*command)

    if _expect_tox_to_fail(
        pass_pipenv_update=pass_pipenv_update,
        install_command=install_command,
        use_pipfile=use_pipfile,
        use_pipfile_lock_env=use_pipfile_lock_env,
    ):
        assert result.ret != 0
        return
    assert result.ret == 0

    result.stdout.fnmatch_lines(
        [
            "py run-test: commands[0] | pip freeze",
        ]
    )
    if install_command:
        if "pipenv" not in install_command:
            result.stdout.fnmatch_lines(["py pipenv: <disabled *"])
            return
        if install_command.startswith("python"):
            install_command = install_command.replace("python", sys.executable)
        exp_install_cmd = list(
            shlex.split(install_command.format(opts="", packages=""))
        )
    elif pass_pipenv_update:
        exp_install_cmd = [sys.executable, "-m", "pipenv", "update"]
    else:
        exp_install_cmd = [sys.executable, "-m", "pipenv", "install"]
    if use_pipfile_lock_env and not pass_pipenv_update and not install_command:
        exp_install_cmd.append("--ignore-pipfile")
    if pip_pre:
        if install_command is None or "{opts}" in (install_command or ""):
            exp_install_cmd.append("--pre")
    exp_path = pytester.path / ".tox" / "py" / "Pipfile"
    if "--ignore-pipfile" in exp_install_cmd:
        exp_path = str(exp_path) + ".lock"
    if pass_pipenv_update or use_pipfile or use_pipfile_lock_env:
        result.stdout.fnmatch_lines(
            [
                glob.escape(r"py pipenv: <{} {}>".format(exp_install_cmd, exp_path)),
            ]
        )
        if (use_pipfile and exp_install_cmd[0] in ("install", "update")) or (
            use_pipfile_lock_env and "--ignore-pipfile" in exp_install_cmd
        ):
            result.stdout.fnmatch_lines(["iterlist==0.4"])
    else:
        result.stdout.no_fnmatch_line("iterlist==*")
    if pass_pipenv_update and not use_pipfile_lock_env and not install_command:
        new_lock_file = pytester.path / "Pipfile_py.lock"
        assert new_lock_file.exists()
        new_lock_file_contents = new_lock_file.read_text()
        assert new_lock_file_contents == PIPFILE_SIMPLE_LOCK


@pytest.mark.parametrize(
    "tox_ini",
    (
        TOX_INI_DEPS_SIMPLE,
        TOX_INI_SKIP_PIPENV,
    ),
    ids=("deps", "skip_pipenv"),
)
def test_end_to_end_deps(pytester, use_pipfile, pass_pipenv_update, tox_ini):
    """Call tox with deps= specified and validate the `pip freeze` output."""
    pytester.makefile(".ini", tox=tox_ini)
    command = [sys.executable, "-m", "tox"]
    if pass_pipenv_update:
        command.append("--pipenv-update")
    result = pytester.run(*command)
    if pass_pipenv_update:
        # can't lock if `deps` are specified or skip_pipenv = true
        assert result.ret != 0
        return
    assert result.ret == 0

    result.stdout.no_fnmatch_line("py pipenv:.*")
    if "deps" in tox_ini:
        result.stdout.fnmatch_lines(["py installdeps: iterlist == 0.4"])
    result.stdout.fnmatch_lines(
        [
            "py pipenv: <disabled *",
            "py run-test: commands[0] | pip freeze",
            "iterlist==0.4",
        ]
    )
    result.stdout.no_fnmatch_line(
        "WARNING: test command found but not installed in testenv"
    )


def test_alt_pipfile(pytester, monkeypatch):
    pytester.makefile(".ini", tox=TOX_INI_PIPFILE_SIMPLE)
    pytester.makefile("", Poopfile=PIPFILE_SIMPLE)
    monkeypatch.setenv("PIPENV_PIPFILE", "Poopfile")
    command = [sys.executable, "-m", "tox"]
    result = pytester.run(*command)
    assert result.ret == 0
    exp_path = pytester.path / ".tox" / "py" / "Poopfile"
    result.stdout.fnmatch_lines(
        [
            glob.escape(
                "py pipenv: <{} {}>".format(
                    [sys.executable, "-m", "pipenv", "install"], exp_path
                )
            ),
            "py run-test: commands[0] | pip freeze",
            "iterlist==0.4",
        ],
    )


def test_no_deps_or_pipfile(pytester):
    pytester.makefile(".ini", tox=TOX_INI_PIPFILE_SIMPLE)
    command = [sys.executable, "-m", "tox"]
    result = pytester.run(*command)
    assert result.ret == 0
    result.stdout.fnmatch_lines(["py pipenv: <disabled *"])
    result.stdout.no_fnmatch_line("iterlist==*")
