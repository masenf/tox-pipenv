import pytest
import subprocess


class MockOption(object):
    def __init__(self):
        self.pipenv_lock = False


class MockConfig(object):
    def __init__(self, tmpdir):
        self._tmpdir = tmpdir
        self.option = MockOption()
        self.toxinidir = tmpdir / "tox-ini-dir"
        self.toxinidir.ensure(dir=True)


class MockEnvironmentConfig(object):
    def __init__(self, tmpdir, config):
        self.config = config
        self.envname = "mock"
        self.envdir = tmpdir / "dot-tox" / self.envname
        self.envdir.ensure(dir=True)
        self.sitepackages = False
        self.pip_pre = False
        self.skip_pipenv = False
        self.pipenv_install_opts = None
        self.pipenv_install_cmd = None


class MockSession(object):
    def __init__(self, tmpdir):
        self.config = MockConfig(tmpdir)

    def make_emptydir(self, path):
        return True


class MockVenv(object):
    def __init__(self, tmpdir, *args, **kwargs):
        self.tmpdir = tmpdir
        self.session = MockSession(tmpdir)
        self.envconfig = MockEnvironmentConfig(tmpdir, config=self.session.config)
        self.deps = []
        self._pipfile = None
        self._pipfile_lock = None

    @property
    def path(self):
        """ Path to environment base dir. """
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


class MockAction(object):
    def __init__(self, venv=None):
        self.venv = venv
        self.activities = []

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
        venv._pipfile_lock = venv.session.config.toxinidir / "Pipfile.lock.{}".format(venv.envconfig.envname)
        venv._pipfile_lock.ensure()
    return request.param


@pytest.fixture(params=[True, False], ids=["has_pip_pre", "no_pip_pre"])
def has_pip_pre(request, venv):
    venv.envconfig.pip_pre = request.param
    return request.param


@pytest.fixture
def actioncls():
    return MockAction


@pytest.fixture
def action(venv, actioncls):
    return actioncls(venv)

