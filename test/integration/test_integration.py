import sys
import shlex
from textwrap import dedent

import pytest


pytest_plugins = ["pytester"]

TOX_INI_PIPFILE_SIMPLE = dedent(
    """
    [tox]
    skipsdist = True
    envlist = py

    [testenv]
    commands = pip freeze""",
)


TOX_INI_DEPS_SIMPLE = dedent(
    """
    [tox]
    skipsdist = True
    envlist = py

    [testenv]
    deps = iterlist == 0.4
    commands = pip freeze""",
)


TOX_INI_SKIP_PIPENV = dedent(
    """
    [tox]
    skipsdist = True
    envlist = py

    [testenv]
    skip_pipenv = true
    commands_pre = pip install iterlist==0.4
    commands = pip freeze""",
)


PIPFILE_SIMPLE = dedent(
    """
    [[source]]
    url = "https://pypi.org/simple"
    verify_ssl = true
    name = "pypi"

    [packages]
    iterlist = "==0.4"
    """
)


PIPFILE_SIMPLE_LOCK = dedent(
    """
    {
        "_meta": {
            "hash": {
                "sha256": "6cf5b9a51d8ce224ffee8d38b6061b14822e71e495b4d50fd89176a668edbbe0"
            },
            "pipfile-spec": 6,
            "requires": {},
            "sources": [
                {
                    "name": "pypi",
                    "url": "https://pypi.org/simple",
                    "verify_ssl": true
                }
            ]
        },
        "default": {
            "iterlist": {
                "hashes": [
                    "sha256:ac8db5cec4245e6ab1a1b65a5a103e1561352213b4e648bef6d7556d59987bc8",
                    "sha256:bae41e52d3c90f001ba009c349f1bc550f5409901fe628e87ac68c716cd877bc"
                ],
                "index": "pypi",
                "version": "==0.4"
            }
        },
        "develop": {}
    }
    """
).lstrip("\n")


@pytest.fixture(autouse=True)
def tox_testenv_passenv_all(monkeypatch):
    monkeypatch.setenv("TOX_TESTENV_PASSENV", "*")


@pytest.fixture(
    params=[True, False],
    ids=["Pipfile", "no_Pipfile"],
)
def use_Pipfile(request, pytester):
    if request.param:
        pytester.makefile("", Pipfile=PIPFILE_SIMPLE)
    return request.param


@pytest.fixture(
    params=[True, False],
    ids=["Pipfile.lock", "no_Pipfile.lock"],
)
def use_Pipfile_lock_env(request, pytester):
    if request.param:
        pytester.makefile(".lock.py", Pipfile=PIPFILE_SIMPLE_LOCK)
    return request.param


@pytest.fixture(params=[True, False], ids=["['--pipenv-update']", "[]"])
def pass_pipenv_update(request):
    return request.param


@pytest.fixture(
    params=["install --dev", "update --pre", None],
    ids=["['install', '--dev']", "['update', '--pre']", "[]"],
)
def pipenv_install_opts(request, monkeypatch):
    if request.param:
        monkeypatch.setenv("TOX_PIPENV_INSTALL_OPTS", request.param)
    return request.param


def _expect_tox_to_fail(
    pass_pipenv_update,
    pipenv_install_opts,
    use_Pipfile,
    use_Pipfile_lock_env,
):
    """
    Return True if we expect tox to fail under the given circumstances.

    An attempt to express these complicated combinations in ways that
    might make sense to future maintainers.
    """
    # condition raised early in tox_testenv_install_deps near _should_skip
    want_update_but_will_raise = (
        pass_pipenv_update and not use_Pipfile and not use_Pipfile_lock_env
    )
    # will hit this in plugin._install_args if _should_skip lets us through
    custom_update_but_no_pipfile = (
        pipenv_install_opts
        and "update" in pipenv_install_opts
        and not use_Pipfile
        and use_Pipfile_lock_env
    )
    # condition raised in plugin._install_args
    want_update_but_no_pipfile = pass_pipenv_update and not use_Pipfile
    # condition raised at the bottom of plugin._install_args
    non_update_custom_mixed_with_update_arg = (
        pass_pipenv_update
        and pipenv_install_opts
        and "update" not in pipenv_install_opts
    )
    return (
        want_update_but_will_raise
        or custom_update_but_no_pipfile
        or want_update_but_no_pipfile
        or non_update_custom_mixed_with_update_arg
    )


@pytest.mark.parametrize(
    "pip_pre", [True, False], ids=["pip_pre=True", "pip_pre=False"]
)
def test_end_to_end(
    pytester,
    use_Pipfile,
    use_Pipfile_lock_env,
    pass_pipenv_update,
    pipenv_install_opts,
    pip_pre,
):
    """Call tox and validate the `pip freeze` output."""
    tox_ini_content = TOX_INI_PIPFILE_SIMPLE
    if pip_pre:
        tox_ini_content += "\npip_pre = true"
    pytester.makefile(".ini", tox=tox_ini_content)
    command = [sys.executable, "-m", "tox"]
    if not use_Pipfile_lock_env:
        assert not (pytester.path / "Pipfile.lock.py").exists()
    if pass_pipenv_update:
        command.append("--pipenv-update")
    result = pytester.run(*command)

    if _expect_tox_to_fail(
        pass_pipenv_update=pass_pipenv_update,
        pipenv_install_opts=pipenv_install_opts,
        use_Pipfile=use_Pipfile,
        use_Pipfile_lock_env=use_Pipfile_lock_env,
    ):
        assert result.ret != 0
        return
    assert result.ret == 0

    result.stdout.fnmatch_lines(
        [
            "py run-test: commands[0] | pip freeze",
        ]
    )
    if pipenv_install_opts:
        exp_install_cmd = list(shlex.split(pipenv_install_opts))
    elif pass_pipenv_update:
        exp_install_cmd = ["update"]
    else:
        exp_install_cmd = ["install"]
    if use_Pipfile_lock_env and not pass_pipenv_update and not pipenv_install_opts:
        exp_install_cmd.append("--ignore-pipfile")
    if pip_pre and not pipenv_install_opts:
        exp_install_cmd.append("--pre")
    exp_path = pytester.path / ".tox" / "py" / "Pipfile"
    if "--ignore-pipfile" in exp_install_cmd:
        exp_path = str(exp_path) + ".lock"
    if pipenv_install_opts and not use_Pipfile:
        # overriding the install command allows use w/o Pipfile
        exp_path = None
    if pass_pipenv_update or use_Pipfile or use_Pipfile_lock_env:
        result.stdout.fnmatch_lines(
            [
                "py pipenv: <{} {}>".format(exp_install_cmd, exp_path),
            ]
        )
        if (use_Pipfile and exp_install_cmd[0] in ("install", "update")) or (
            use_Pipfile_lock_env and "--ignore-pipfile" in exp_install_cmd
        ):
            result.stdout.fnmatch_lines(["iterlist==0.4"])
    else:
        result.stdout.no_fnmatch_line("iterlist==*")
    if pass_pipenv_update and not use_Pipfile_lock_env:
        new_lock_file = pytester.path / "Pipfile.lock.py"
        assert new_lock_file.exists()
        new_lock_file_contents = new_lock_file.read_text()
        print(new_lock_file_contents)
        print(PIPFILE_SIMPLE_LOCK)
        assert new_lock_file_contents == PIPFILE_SIMPLE_LOCK


@pytest.mark.parametrize(
    "tox_ini",
    (
        TOX_INI_DEPS_SIMPLE,
        TOX_INI_SKIP_PIPENV,
    ),
    ids=("deps", "skip_pipenv"),
)
def test_end_to_end_deps(pytester, use_Pipfile, pass_pipenv_update, tox_ini):
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
            "py run-test: commands[0] | pip freeze",
            "iterlist==0.4",
        ]
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
            "py pipenv: <['install'] {}>".format(exp_path),
            "py run-test: commands[0] | pip freeze",
            "iterlist==0.4",
        ],
    )


def test_no_deps_or_pipfile(pytester):
    pytester.makefile(".ini", tox=TOX_INI_PIPFILE_SIMPLE)
    command = [sys.executable, "-m", "tox"]
    result = pytester.run(*command)
    assert result.ret == 0
    result.stdout.no_fnmatch_line("iterlist==*")
    result.stdout.no_fnmatch_line("py pipenv:*")
