import sys
from textwrap import dedent

import pytest


pytest_plugins = ["pytester"]

TOX_INI_PIPFILE_SIMPLE = dedent(
    """
    [tox]
    skipsdist = True
    envlist = py

    [testenv]
    commands_pre = env
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


@pytest.fixture(params=[True, False], ids=["['--pipenv-lock']", "[]"])
def pass_pipenv_lock(request):
    return request.param


def test_end_to_end(pytester, use_Pipfile, use_Pipfile_lock_env, pass_pipenv_lock):
    """Call tox and validate the `pip freeze` output."""
    pytester.makefile(".ini", tox=TOX_INI_PIPFILE_SIMPLE)
    command = [sys.executable, "-m", "tox"]
    if not use_Pipfile_lock_env:
        assert not (pytester.path / "Pipfile.lock.py").exists()
    if pass_pipenv_lock:
        command.append("--pipenv-lock")

    result = pytester.run(*command)
    if pass_pipenv_lock and not use_Pipfile:
        # can't lock without a Pipfile
        assert result.ret != 0
        return
    assert result.ret == 0

    result.stdout.fnmatch_lines(
        [
            "py run-test: commands[0] | pip freeze",
        ]
    )
    if pass_pipenv_lock:
        result.stdout.fnmatch_lines(
            [
                "py pipenvlock: <{}/.tox/py/Pipfile>".format(pytester.path),
            ]
        )
    else:
        result.stdout.no_fnmatch_line("py pipenvlock:.*")
    if pass_pipenv_lock or use_Pipfile_lock_env:
        result.stdout.fnmatch_lines(
            [
                "py pipenv: <['sync'] {}/.tox/py/Pipfile.lock>".format(pytester.path),
                "iterlist==0.4",
            ]
        )
    elif use_Pipfile:
        result.stdout.fnmatch_lines(
            [
                "py pipenv: <['install'] {}/.tox/py/Pipfile>".format(pytester.path),
                "iterlist==0.4",
            ]
        )
    else:
        result.stdout.no_fnmatch_line("iterlist==*")
    if pass_pipenv_lock and not use_Pipfile_lock_env:
        new_lock_file = pytester.path / "Pipfile.lock.py"
        assert new_lock_file.exists()
        new_lock_file_contents = new_lock_file.read_text()
        print(new_lock_file_contents)
        print(PIPFILE_SIMPLE_LOCK)
        assert new_lock_file_contents == PIPFILE_SIMPLE_LOCK
