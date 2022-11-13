import pytest

from .data import (
    PIPFILE_SIMPLE,
    PIPFILE_SIMPLE_LOCK,
    TOX_INI_PIPFILE_SIMPLE,
    TOX_INI_PIPFILE_INSTALL_COMMAND,
)


@pytest.fixture(autouse=True)
def tox_testenv_passenv_all(monkeypatch):
    monkeypatch.setenv("TOX_TESTENV_PASSENV", "*")


@pytest.fixture(
    params=[True, "_py", False],
    ids=["Pipfile", "Pipfile_py", "no_Pipfile"],
)
def use_pipfile(request, pytester):
    if request.param:
        pipfile_name = "Pipfile"
        if not isinstance(request.param, bool):
            pipfile_name += request.param
        pytester.makefile("", **{pipfile_name: PIPFILE_SIMPLE})
    return request.param


@pytest.fixture(
    params=[True, False],
    ids=["Pipfile.lock", "no_Pipfile.lock"],
)
def use_pipfile_lock_env(request, pytester):
    if request.param:
        pytester.makefile(".lock", Pipfile_py=PIPFILE_SIMPLE_LOCK)
    return request.param


@pytest.fixture(params=[True, False], ids=["['--pipenv-update']", "[]"])
def pass_pipenv_update(request):
    return request.param


@pytest.fixture
def tox_ini(pytester):
    return pytester.makefile(".ini", tox=TOX_INI_PIPFILE_SIMPLE)


@pytest.fixture(
    params=[
        "pipenv install --dev {opts} {packages}",
        "pipenv update --pre {packages}",
        # XXX: can't use this because `python` is the venv python, not the tox python
        # "python -m pipenv update --pre {packages}",
        "echo {opts} {packages}",
        None,
    ],
    ids=["['install', '--dev']", "['update', '--pre']", "[echo]", "[]"],
)
def install_command(request, pytester, tox_ini):
    if request.param is not None:
        pytester.makefile(
            ".ini",
            tox=TOX_INI_PIPFILE_INSTALL_COMMAND.format(install_command=request.param),
        )
    return request.param


@pytest.fixture(params=[True, False], ids=["pip_pre=True", "pip_pre=False"])
def pip_pre(request, pytester, tox_ini, install_command):
    if request.param:
        tox_ini_content = tox_ini.read_text()
        tox_ini_content += "\npip_pre = true"
        pytester.makefile(".ini", tox=tox_ini_content)
    return request.param
