import subprocess
import uuid

import attr
import pytest

import tox_pipenv.plugin


@attr.s
class MockOption(object):
    pipenv_update = attr.ib(default=False)


@attr.s
class MockConfig(object):
    _tmpdir = attr.ib()
    option = attr.ib(factory=MockOption)
    toxinidir = attr.ib()

    @toxinidir.default
    def _toxinitdir_default(self):
        toxinidir = self._tmpdir / "tox-ini-dir"
        toxinidir.ensure(dir=True)
        return toxinidir


@attr.s
class MockEnvironmentConfig(object):
    _tmpdir = attr.ib()
    config = attr.ib()
    envname = attr.ib(default="mock")
    envdir = attr.ib()
    sitepackages = attr.ib(default=False)
    pip_pre = attr.ib(default=False)
    skip_pipenv = attr.ib(default=False)
    pipenv_install_opts = attr.ib(default=None)
    pipenv_install_cmd = attr.ib(default=None)

    @envdir.default
    def _envdir_default(self):
        envdir = self._tmpdir / "dot-tox" / self.envname
        envdir.ensure(dir=True)
        return envdir


@attr.s
class MockSession(object):
    _tmpdir = attr.ib()
    config = attr.ib()

    @config.default
    def _config(self):
        return MockConfig(self._tmpdir)

    def make_emptydir(self, path):
        return True


@attr.s
class MockVenv(object):
    _tmpdir = attr.ib()
    session = attr.ib()
    envconfig = attr.ib()
    deps = attr.ib(factory=list)
    _pipfile = attr.ib(default=None)
    _pipfile_lock = attr.ib(default=None)

    @session.default
    def _session_default(self):
        return MockSession(self._tmpdir)

    @envconfig.default
    def _envconfig_default(self):
        return MockEnvironmentConfig(self._tmpdir, config=self.session.config)

    @property
    def path(self):
        """Path to environment base dir."""
        return self.envconfig.envdir

    def getsupportedinterpreter(self):
        return "test-python"

    def _pcall(self, *args, **kwargs):
        return subprocess.Popen(*args, **kwargs)

    def _getresolvedeps(self):
        return self.deps

    def get_resolved_dependencies(self):
        # _getresolvedeps was deprecated on tox 3.7.0 in favor of get_resolved_dependencies
        return self.deps


@attr.s
class MockAction(object):
    venv = attr.ib()
    activities = attr.ib(factory=list)

    def setactivity(self, *args, **kwargs):
        self.activities.append(args)

    def popen(self, *args, **kwargs):
        return subprocess.Popen(*args, **kwargs)


@pytest.fixture
def venv(tmpdir):
    return MockVenv(tmpdir)


@pytest.fixture(params=[True, False], ids=["has_Pipfile", "no_Pipfile"])
def has_pipfile(request, venv):
    if request.param:
        venv._pipfile = venv.session.config.toxinidir / "Pipfile"
        venv._pipfile.ensure()
    return request.param


@pytest.fixture(params=[True, False], ids=["has_Pipfile.lock", "no_Pipfile.lock"])
def has_pipfile_lock(request, venv):
    if request.param:
        venv._pipfile_lock = venv.session.config.toxinidir / "Pipfile.lock.{}".format(
            venv.envconfig.envname
        )
        venv._pipfile_lock.ensure()
    return request.param


@pytest.fixture(params=[True, False], ids=["has_pip_pre", "no_pip_pre"])
def has_pip_pre(request, venv):
    venv.envconfig.pip_pre = request.param
    return request.param


@pytest.fixture(params=[True, False], ids=["has_skip_pipenv", "no_skip_pipenv"])
def has_skip_pipenv(request, venv):
    venv.envconfig.skip_pipenv = request.param
    return request.param


@pytest.fixture(params=[True, False], ids=["has_pipenv_update", "no_pipenv_update"])
def has_pipenv_update(request, mocker, venv, action):
    venv.envconfig.config.option.pipenv_update = request.param
    if request.param:
        mock_lock_data = str(uuid.uuid4())

        _pipenv_command = tox_pipenv.plugin._pipenv_command

        def _make_lock_file(*args, **kwargs):
            (venv.path / tox_pipenv.plugin.PIPFILE_LOCK).write(mock_lock_data)
            return _pipenv_command(*args, **kwargs)

        mocker.patch("tox_pipenv.plugin._pipenv_command", side_effect=_make_lock_file)
        return mock_lock_data
    return False


@pytest.fixture
def actioncls():
    return MockAction


@pytest.fixture
def action(venv, actioncls):
    return actioncls(venv)


@pytest.fixture
def mock_for_Popen(mocker):
    mocker.patch.dict("os.environ")
    mocker.patch("subprocess.Popen")
