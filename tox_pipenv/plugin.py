"""
Use `pipenv` to install dependencies.

Tox plugin overrides `install_deps` action to install dependencies
from a `Pipfile` into the current test environment.
"""
import itertools
import shlex
import sys
import os

import py.path
from tox import hookimpl
from tox.config import InstallcmdOption
import tox.venv


DEFAULT_PIPENV_ENV = {
    "PIPENV_YES": "1",  # Answer yes on recreation of virtual env
    "PIPENV_VENV_IN_PROJECT": "0",
    "PIPENV_VERBOSITY": "-1",  # suppress existing venv warning
    "PIPENV_NOSPIN": "1",  # suppress terminal animations
}
ENV_PIPENV_PIPFILE = "PIPENV_PIPFILE"
PIPFILE_PARENT = PIPFILE = PIPFILE_FALLBACK = PIPFILE_LOCK = PIPFILE_LOCK_ENV = None


class ToxPipenvError(Exception):
    """Raised when the plugin encounters some error."""


def _init_global_pipfile(pipenv_pipfile_str):
    global PIPFILE_PARENT, PIPFILE, PIPFILE_FALLBACK, PIPFILE_LOCK, PIPFILE_LOCK_ENV

    if pipenv_pipfile_str is not None:
        pipenv_pipfile = py.path.local(pipenv_pipfile_str)
        PIPFILE_PARENT = pipenv_pipfile.parts()[-2]
        PIPFILE = PIPFILE_FALLBACK = pipenv_pipfile.basename
    else:
        PIPFILE_PARENT = None
        PIPFILE_FALLBACK = "Pipfile"
        PIPFILE = PIPFILE_FALLBACK + "_{envname}"
    PIPFILE_LOCK = PIPFILE_FALLBACK + ".lock"
    PIPFILE_LOCK_ENV = PIPFILE + ".lock"


def _init_global_pipfile_from_env_var():
    _init_global_pipfile(pipenv_pipfile_str=os.environ.get(ENV_PIPENV_PIPFILE) or None)


_init_global_pipfile_from_env_var()


def _try_pipfile_names(venv):
    """Iterate possible Pipfile names for the current venv."""
    yield PIPFILE.format(envname=venv.envconfig.envname)
    yield PIPFILE_FALLBACK


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
    pipfile_lock_path = in_path.join(
        lock_file_fmt.format(envname=venv.envconfig.envname),
    )
    for pipfile_name in _try_pipfile_names(venv):
        pipfile_path = in_path.join(pipfile_name)
        if not pipfile_path.exists():
            pipfile_path = None
        else:
            break
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
    config = getattr(venv, "session", venv.envconfig).config
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
        venv_pipfile_path = venv.path.join(PIPFILE_FALLBACK)
        root_pipfile_path.copy(venv_pipfile_path)
    venv_pipfile_lock_path = None
    if root_pipfile_lock_path is not None:
        venv_pipfile_lock_path = venv.path.join(PIPFILE_LOCK)
        root_pipfile_lock_path.copy(venv_pipfile_lock_path)
    return venv_pipfile_path, venv_pipfile_lock_path


def _ensure_pipfile(venv):
    """Ensure that `pipfile_path` exists in venv, even if it's empty."""
    pipfile_path, pipfile_lock_path = _clone_pipfile(venv)
    if pipfile_path is None:
        # we need an actual Pipfile, even if its empty
        if pipfile_lock_path is not None:
            pipfile_path = pipfile_lock_path.parts()[-2] / PIPFILE_FALLBACK
        else:
            pipfile_path = venv.path / PIPFILE_FALLBACK
        pipfile_path.ensure()
    return pipfile_path, pipfile_lock_path


def _basepath(venv):
    """Get basepath for the venv and ensure it exists."""
    basepath = venv.path.dirpath()
    basepath.ensure(dir=True)
    return basepath


def _pipenv_env(venv, pipfile_path=None):
    """Return environment variables for running `pipenv`."""
    if pipfile_path is None:
        pipfile_path, _ = _venv_pipfile(venv)
    if pipfile_path is None:
        raise ToxPipenvError(
            "Unable to generate environment variables, {} not found for {}".format(
                PIPFILE_FALLBACK,
                venv.envconfig.envname,
            )
        )
    env = DEFAULT_PIPENV_ENV.copy()
    env.update(os.environ)
    env["VIRTUAL_ENV"] = str(venv.path)
    env["PIPENV_PIPFILE"] = str(pipfile_path)
    # ensure we "create" the venv where tox would be expecting it
    env["WORKON_HOME"] = str(venv.path.parts()[-2])
    env["PIPENV_CUSTOM_VENV_NAME"] = str(venv.path.basename)
    return env


def _pipenv_command_line(*args):
    return [sys.executable, "-m", "pipenv"] + list(args)


def _expand_install_command(command, packages, options):
    def _expand_item(val):
        # expand an install command
        if val == "{packages}":
            for package in packages:
                yield package
        elif val == "{opts}":
            for opt in options:
                yield opt
        else:
            yield val

    if command[0] == "python":
        # expand "python" to the tox python, not the env python
        command = list(itertools.chain([sys.executable], command[1:]))
    return list(itertools.chain.from_iterable(_expand_item(val) for val in command))


def _has_default_install_command(venv):
    return venv.envconfig.install_command == shlex.split(InstallcmdOption.default)


@hookimpl
def tox_addoption(parser):
    parser.add_argument(
        "--pipenv-update",
        action="store_true",
        default=False,
        help="Run `pipenv update` and copy resulting Pipfile.lock into {toxinidir}",
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
        "pipenv_venv",
        type="bool",
        default=True,
        help="If true, use pipenv to create the virtual environment",
    )


@hookimpl
def tox_configure(config):
    _init_global_pipfile_from_env_var()


def _should_skip_create(venv):
    """Return a reason why this plugin should NOT proceed."""
    if venv.envconfig.skip_pipenv:
        return "environment {!r} has `skip_pipenv = {}`".format(
            venv.envconfig.envname,
            venv.envconfig.skip_pipenv,
        )
    if not venv.envconfig.pipenv_venv:
        return "environment {!r} has `pipenv_venv = {}`".format(
            venv.envconfig.envname,
            venv.envconfig.pipenv_venv,
        )
    pipfile_path, pipfile_lock_path = _toxinidir_pipfile(venv)
    if pipfile_path is None and pipfile_lock_path is None:
        # this plugin only operates when Pipfile is present
        tried_files = list(_try_pipfile_names(venv)) + [
            PIPFILE_LOCK_ENV.format(envname=venv.envconfig.envname),
        ]
        return "none of {!r} are present.".format(tried_files)


@hookimpl
def tox_testenv_create(venv, action):
    skip_reason = _should_skip_create(venv)
    if skip_reason:
        action.setactivity("create pipenv", "<disabled {!r}>".format(skip_reason))
        return
    config_interpreter = venv.getsupportedinterpreter()
    args = [sys.executable, "-m", "pipenv"]
    if venv.envconfig.sitepackages:
        args.append("--site-packages")

    args.extend(["--python", str(config_interpreter)])

    if hasattr(venv.envconfig, "make_emptydir"):
        venv.envconfig.make_emptydir(venv.path)
    else:
        # tox 3.8.0 removed make_emptydir, See tox #1219
        tox.venv.cleanup_for_venv(venv)

    # Pipfile must exist in the venv directory
    _ensure_pipfile(venv)
    venv._pcall(
        args, venv=False, action=action, cwd=_basepath(venv), env=_pipenv_env(venv)
    )

    # Return non-None to indicate the plugin has completed
    return True


def _deps(venv):
    try:
        return venv.get_resolved_dependencies()
    except AttributeError:  # pragma: no cover
        # _getresolvedeps was deprecated on tox 3.7.0 in favor of get_resolved_dependencies
        return venv._getresolvedeps()


def _should_skip(venv):
    """Return a reason why this plugin should NOT proceed."""
    if venv.envconfig.skip_pipenv:
        return "environment {!r} has `skip_pipenv = {}`".format(
            venv.envconfig.envname,
            venv.envconfig.skip_pipenv,
        )
    if not _has_default_install_command(venv):
        install_command = venv.envconfig.install_command
        if "pipenv" not in install_command:
            return "custom 'install_command' {!r} doesn't contain `pipenv`".format(
                install_command,
            )
        return  # pipfile checks are ignored if a custom install_command is given
    else:
        deps = _deps(venv)
        if deps:
            # this plugin only operates in the absense of testenv deps
            return (
                "environment {!r} has `deps = {}`, and does not "
                "define an install_command".format(venv.envconfig.envname, deps)
            )
    pipfile_path, pipfile_lock_path = _toxinidir_pipfile(venv)
    if pipfile_path is None and pipfile_lock_path is None:
        # this plugin only operates when Pipfile is present
        tried_files = list(_try_pipfile_names(venv)) + [
            PIPFILE_LOCK_ENV.format(envname=venv.envconfig.envname),
        ]
        return "none of {!r} are present.".format(tried_files)


def _install_command(venv):
    """
    Get the install command (using `pipenv`) for install_deps.
    """
    if not _has_default_install_command(venv):
        # don't override the user's install_command
        return venv.envconfig.install_command, []

    g_config = venv.envconfig.config
    pipfile_path, pipfile_lock_path = _venv_pipfile(venv)

    install_cmd = "install"
    opts = []
    if g_config.option.pipenv_update:
        install_cmd = "update"
        toxinidir_pipfile_path, _ = _toxinidir_pipfile(venv)
        if toxinidir_pipfile_path is None:
            raise ToxPipenvError(
                "Unable to update for {}, none of {} found in {}".format(
                    venv.envconfig.envname,
                    set(_try_pipfile_names(venv)),
                    g_config.toxinidir,
                )
            )
    elif pipfile_lock_path is not None:
        # the project provides a lockfile for this environment, so install
        # from the lockfile by ignoring the Pipfile
        opts.append("--ignore-pipfile")
    return _pipenv_command_line(install_cmd, "{opts}", "{packages}"), opts


@hookimpl
def tox_testenv_install_deps(venv, action):
    g_config = venv.envconfig.config
    skip_reason = _should_skip(venv)
    if skip_reason:
        if g_config.option.pipenv_update:
            raise ToxPipenvError(
                "--pipenv-update is specified, but {}".format(skip_reason)
            )
        action.setactivity("pipenv", "<disabled {!r}>".format(skip_reason))
        return
    pipfile_path, pipfile_lock_path = _ensure_pipfile(venv)
    install_command, opts = _install_command(venv)
    if venv.envconfig.pip_pre:
        opts.append("--pre")
    expanded_command = _expand_install_command(
        install_command,
        packages=_deps(venv),
        options=opts,
    )
    action.setactivity(
        "pipenv",
        "<{} {}>".format(
            expanded_command,
            pipfile_lock_path
            if "--ignore-pipfile" in expanded_command
            else pipfile_path,
        ),
    )
    # XXX: for custom install_command, but not sure if this is what we want...
    venv.envconfig.allowlist_externals.append("pipenv")
    venv._pcall(
        expanded_command,
        cwd=_basepath(venv),
        action=action,
        env=_pipenv_env(venv),
    )
    if g_config.option.pipenv_update:
        # copy the lock file back to project dir to be committed
        _, pipfile_lock_path = _venv_pipfile(venv)
        project_dir = PIPFILE_PARENT or g_config.toxinidir
        if pipfile_lock_path:
            pipfile_lock_path.copy(
                project_dir
                / PIPFILE_LOCK_ENV.format(
                    envname=venv.envconfig.envname,
                ),
            )
    # Return True to stop further plugins from installing deps
    return True


@hookimpl
def tox_runenvreport(venv, action):
    if _should_skip(venv):
        return
    action.setactivity("runenvreport", "")
    return venv._pcall(
        _pipenv_command_line("graph"),
        cwd=_basepath(venv),
        action=action,
        env=_pipenv_env(venv),
    ).splitlines()
