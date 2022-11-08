import shlex
import sys
import os
import tox
from tox import hookimpl
from tox import reporter
from tox.venv import cleanup_for_venv
import contextlib


ENV_PIPENV_INSTALL_ARGS = "TOX_PIPENV_INSTALL_ARGS"


def _env_install_args():
    args_str = os.environ.get(ENV_PIPENV_INSTALL_ARGS)
    if args_str:
        return list(shlex.split(args_str))


def _init_pipenv_environ():
    # Answer yes on recreation of virtual env
    os.environ["PIPENV_YES"] = "1"

    # don't use pew
    os.environ["PIPENV_VENV_IN_PROJECT"] = "1"


def _clone_pipfile(venv):
    if hasattr(venv, 'session'):
        root_pipfile_path = venv.session.config.toxinidir.join("Pipfile")
    else:
        root_pipfile_path = venv.envconfig.config.toxinidir.join("Pipfile")
    # first try for an environment-specific lock file
    root_pipfile_lock_path = root_pipfile_path + ".lock.{}".format(
        venv.envconfig.envname,
    )
    if not root_pipfile_lock_path.exists():
        root_pipfile_lock_path = root_pipfile_path + ".lock"

    # venv path may not have been created yet
    venv.path.ensure(dir=1)

    venv_pipfile_path = venv.path.join("Pipfile")
    venv_pipfile_lock_path = None
    if not os.path.exists(str(root_pipfile_path)):
        with open(str(venv_pipfile_path), "a"):
            os.utime(str(venv_pipfile_path), None)
    if root_pipfile_lock_path.exists():
        venv_pipfile_lock_path = venv_pipfile_path + ".lock"
        root_pipfile_lock_path.copy(venv_pipfile_lock_path)
    if not venv_pipfile_path.check():
        root_pipfile_path.copy(venv_pipfile_path)
    return venv_pipfile_path, venv_pipfile_lock_path


@contextlib.contextmanager
def wrap_pipenv_environment(venv, pipfile_path):
    old_pipfile = os.environ.get("PIPENV_PIPFILE", None)
    os.environ["PIPENV_PIPFILE"] = str(pipfile_path)
    yield
    if old_pipfile:
        os.environ["PIPENV_PIPFILE"] = old_pipfile


@hookimpl
def tox_testenv_install_deps(venv, action):
    _init_pipenv_environ()
    # TODO: If skip_install set, check existence of venv Pipfile
    try:
        deps = venv._getresolvedeps()
    except AttributeError:
        # _getresolvedeps was deprecated on tox 3.7.0 in favor of get_resolved_dependencies
        deps = venv.get_resolved_dependencies()
    basepath = venv.path.dirpath()
    basepath.ensure(dir=1)
    pipfile_path, pipfile_lock_path = _clone_pipfile(venv)

    install_args = _env_install_args()
    if install_args is None:
        if pipfile_lock_path is not None:
            # project provided a lock file, so sync deps
            install_args = ["sync", "--dev"]
        else:
            install_args = ["install", "--dev"]

    args = [sys.executable, "-m", "pipenv"] + install_args
    if venv.envconfig.pip_pre:
        args.append('--pre')
    with wrap_pipenv_environment(venv, pipfile_path):
        if deps:
            if "sync" in args:
                action.setactivity("installdeps", "<sync to Pipfile.lock>")
            else:
                action.setactivity("installdeps", "%s" % ",".join(list(map(str, deps))))
                args += list(map(str, deps))
        else:
            action.setactivity("installdeps", "[]")
        venv._pcall(args, action=action, cwd=basepath)

    # Return non-None to indicate the plugin has completed
    return True


@hookimpl
def tox_runenvreport(venv, action):
    _init_pipenv_environ()
    pipfile_path, pipfile_lock_path = _clone_pipfile(venv)

    basepath = venv.path.dirpath()
    basepath.ensure(dir=1)
    with wrap_pipenv_environment(venv, pipfile_path):
        action.setactivity("runenvreport", "")
        # call pipenv graph
        args = [sys.executable, "-m", "pipenv", "graph"]
        output = venv._pcall(args, action=action, cwd=basepath)

        output = output.split("\n")
    return output
