"""
Use `pipenv` to install or sync dependencies.

Tox plugin overrides `install_deps` action to either install or sync
dependencies from a `Pipfile` into the current test environment.
"""
import contextlib
import shlex
import sys
import os

import py.path
from tox import hookimpl
from tox import reporter


DEFAULT_PIPENV_ENV = {
    "PIPENV_YES": "1",  # Answer yes on recreation of virtual env
    "PIPENV_VENV_IN_PROJECT": "1",  # don't use pew
    "PIPENV_VERBOSITY": "-1",  # suppress existing venv warning
    "PIPENV_NOSPIN": "1",  # suppress terminal animations
}
DEFAULT_PIPENV_INSTALL_OPTS = []
ENV_PIPENV_INSTALL_OPTS = "TOX_PIPENV_INSTALL_OPTS"
ENV_PIPENV_INSTALL_CMD = "TOX_PIPENV_INSTALL_CMD"
ENV_PIPENV_PIPFILE = "PIPENV_PIPFILE"
PIPFILE_PARENT = PIPFILE = PIPFILE_LOCK = PIPFILE_LOCK_ENV = None


def _init_global_pipfile_from_env_var():
    global PIPFILE_PARENT, PIPFILE, PIPFILE_LOCK, PIPFILE_LOCK_ENV

    pipenv_pipfile_str = os.environ.get(ENV_PIPENV_PIPFILE)
    if pipenv_pipfile_str is not None:
        pipenv_pipfile = py.path.local(pipenv_pipfile_str)
        PIPFILE_PARENT = pipenv_pipfile.parts()[-2]
        PIPFILE = pipenv_pipfile.basename
    else:
        PIPFILE = "Pipfile"
    PIPFILE_LOCK = PIPFILE + ".lock"
    PIPFILE_LOCK_ENV = PIPFILE_LOCK + ".{envname}"


def _pipfile_if_exists(venv, in_path=None, lock_file_fmt=None):
    """
    Get Pipfile and Pipfile.lock paths for the given venv under in_path.

    If in_path is not given, default to `venv.path`.

    Return tuple of (pipfile_path, pipfile_lock_path).

    If either of these values are None, then the corresponding file did not
    exist in in_path.
    """
    if in_path is None:
        in_path = venv.path
    if lock_file_fmt is None:
        lock_file_fmt = PIPFILE_LOCK
    pipfile_path = in_path.join(PIPFILE)
    pipfile_lock_path = in_path.join(
        lock_file_fmt.format(envname=venv.envconfig.envname),
    )
    if not pipfile_path.exists():
        pipfile_path = None
    if not pipfile_lock_path.exists():
        pipfile_lock_path = None
    return pipfile_path, pipfile_lock_path


def _toxinidir_pipfile(venv):
    """
    Get Pipfile and Pipfile.lock.{envconfig} paths in the project directory.

    If PIPENV_PIPFILE is set, look for the path's basename and derived lock
    file in the parent directory.

    Return tuple of (pipfile_path, pipfile_lock_path).
    """
    config = getattr(venv, 'session', venv.envconfig).config
    return _pipfile_if_exists(
        venv,
        in_path=PIPFILE_PARENT or config.toxinidir,
        lock_file_fmt=PIPFILE_LOCK_ENV,
    )


def _venv_pipfile(venv):
    """
    Get Pipfile and Pipfile.lock paths in the given venv.

    Return tuple of (pipfile_path, pipfile_lock_path).
    """
    return _pipfile_if_exists(venv)


def _clone_pipfile(venv):
    """
    Copy project Pipfile and env-specific Pipfile.lock into venv.

    This function is called during tox_testenv_install_deps to create an
    isolated copy of the Pipfile and lock file, in case any commands modify it
    in the course of environment creation.

    Return tuple of (pipfile_path, pipfile_lock_path).

    If either of these values are None, then the corresponding file did not
    exist in toxinidir.
    """
    root_pipfile_path, root_pipfile_lock_path = _toxinidir_pipfile(venv)

    # venv path may not have been created yet
    venv.path.ensure(dir=True)

    venv_pipfile_path = None
    if root_pipfile_path is not None:
        venv_pipfile_path = venv.path.join(PIPFILE)
        root_pipfile_path.copy(venv_pipfile_path)
    venv_pipfile_lock_path = None
    if root_pipfile_lock_path is not None:
        venv_pipfile_lock_path = venv.path.join(PIPFILE_LOCK)
        root_pipfile_lock_path.copy(venv_pipfile_lock_path)
    return venv_pipfile_path, venv_pipfile_lock_path


def _basepath(venv):
    """Get basepath for the venv and ensure it exists."""
    basepath = venv.path.dirpath()
    basepath.ensure(dir=True)
    return basepath


def _pipenv_env(venv, pipfile_path=None):
    """Return environment variables for running `pipenv`."""
    if pipfile_path is None:
        pipfile_path, _ = _venv_pipfile(venv)
    env = DEFAULT_PIPENV_ENV.copy()
    env.update(os.environ)
    env["VIRTUAL_ENV"] = str(venv.path)
    env["PIPENV_PIPFILE"] = str(pipfile_path)
    return env


def _pipenv_command(venv, args, action, **kwargs):
    """
    Execute `pipenv` in the given venv.

    Additional kwargs are passed to venv._pcall.

    If kwarg "env" is specified, it will be combined with and override the
    os.environ and default _pipenv_env values.
    """
    env = _pipenv_env(venv)
    kwarg_env = kwargs.pop("env", {})
    env.update(kwarg_env)
    return venv._pcall(
        [sys.executable, "-m", "pipenv"] + list(args),
        cwd=kwargs.pop("cwd", _basepath(venv)),
        action=action,
        env=env,
    )


def _venv_pipenv_lock(venv, action):
    """Perform an explicit `pipenv lock` operation in the venv."""
    pipfile_path, _ = _venv_pipfile(venv)
    action.setactivity(
        "pipenvlock",
        "<{}>".format(pipfile_path),
    )
    _pipenv_command(venv, args=["lock"], action=action)
    return _venv_pipfile(venv)


@hookimpl
def tox_addoption(parser):
    parser.add_argument(
        "--pipenv-lock",
        action="store_true",
        default=False,
        help="Explicitly run `pipenv lock` to create or update a Pipfile.lock",
    )
    parser.add_testenv_attribute(
        "skip_pipenv",
        type="bool",
        default=False,
        help=(
            "If true, this plugin will not take any pipenv-related actions for "
            "the given environment. Useful for performing `pipenv` commands "
            "directly or specifying an environment without `deps` in a project "
            "that uses Pipfile."
        ),
    )
    parser.add_testenv_attribute(
        "pipenv_install_cmd",
        type="string",
        default=None,
        help=(
            "Override the `install` or `sync` command executed during installdeps. "
            "(var {})".format(ENV_PIPENV_INSTALL_CMD)
        ),
    )
    parser.add_testenv_attribute(
        "pipenv_install_opts",
        type="string",
        default=None,
        help=(
            "Override the opts passed to the install command. "
            "(default: {}) (var: {})".format(
                DEFAULT_PIPENV_INSTALL_OPTS,
                ENV_PIPENV_INSTALL_OPTS,
            )
        ),
    )


@hookimpl
def tox_configure(config):
    _init_global_pipfile_from_env_var()


def _should_skip(venv):
    """Return True if this plugin should NOT proceed."""
    if venv.envconfig.skip_pipenv:
        return True
    pipfile_path, pipfile_lock_path = _toxinidir_pipfile(venv)
    if pipfile_path is None and pipfile_lock_path is None:
        # this plugin only operates when Pipfile is present
        return True
    try:
        deps = venv.get_resolved_dependencies()
    except AttributeError:
        # _getresolvedeps was deprecated on tox 3.7.0 in favor of get_resolved_dependencies
        deps = venv._getresolvedeps()
    if deps:
        # this plugin only operates in the absense of testenv deps
        return True


def _install_args(venv):
    """
    Get the args passed `pipenv` for install_deps.

    If no user suppled args are available, return None.
    """
    pipfile_path, pipfile_lock_path = _venv_pipfile(venv)
    if pipfile_path is None:
        # we need an actual Pipfile, even if its empty
        pipfile_path = pipfile_lock_path.parts()[-2] / PIPFILE
        pipfile_path.ensure()

    args_str = os.environ.get(ENV_PIPENV_INSTALL_OPTS, venv.envconfig.pipenv_install_opts)
    if args_str:
        args = list(shlex.split(args_str))
    else:
        args = DEFAULT_PIPENV_INSTALL_OPTS
    install_cmd = os.environ.get(ENV_PIPENV_INSTALL_CMD, venv.envconfig.pipenv_install_cmd)
    if install_cmd is None:
        if pipfile_lock_path is None:
            install_cmd = "install"
            if venv.envconfig.pip_pre:
                args.append('--pre')
        else:
            # the project provides a lockfile for this environment, so sync to it
            install_cmd = "sync"
    return [install_cmd] + args


@hookimpl
def tox_testenv_install_deps(venv, action):
    if _should_skip(venv):
        return
    pipfile_path, pipfile_lock_path = _clone_pipfile(venv)
    g_config = venv.envconfig.config
    if g_config.option.pipenv_lock:
        # user requested explicit locking
        pipfile_path, pipfile_lock_path = _venv_pipenv_lock(venv, action)
        # copy the lock file back to project dir to be committed
        project_dir = PIPFILE_PARENT or g_config.toxinidir
        pipfile_lock_path.copy(
            project_dir / PIPFILE_LOCK_ENV.format(
                envname=venv.envconfig.envname,
            ),
        )
    install_args = _install_args(venv)
    action.setactivity(
        "pipenv",
        "<{} {}>".format(
            install_args,
            pipfile_lock_path if "sync" in install_args else pipfile_path,
        ),
    )
    _pipenv_command(
        venv,
        args=install_args,
        action=action,
    )
    # Return True to stop further plugins from installing deps
    return True


@hookimpl
def tox_runenvreport(venv, action):
    if _should_skip(venv):
        return
    action.setactivity("runenvreport", "")
    output = _pipenv_command(venv, args=["graph"], action=action).splitlines()
    return output
