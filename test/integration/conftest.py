import pytest

from .data import PIPFILE_SIMPLE, PIPFILE_SIMPLE_LOCK


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


@pytest.fixture(
    params=["install --dev", "update --pre", None],
    ids=["['install', '--dev']", "['update', '--pre']", "[]"],
)
def pipenv_install_opts(request, monkeypatch):
    if request.param:
        monkeypatch.setenv("TOX_PIPENV_INSTALL_OPTS", request.param)
    return request.param
