# tox-pipenv2

A reimplementation of [`tox-dev/tox-pipenv`](https://github.com/tox-dev/tox-pipenv) to address
existing issues and rough edges encountered in a "strict-pinning" workflow.


[![tox-pipenv on PyPI](https://img.shields.io/pypi/v/tox-pipenv2.svg)](https://pypi.python.org/pypi/tox-pipenv2)

[![Test Package Compatibility](https://github.com/tox-dev/tox-pipenv/workflows/Test%20Package%20Compatibility/badge.svg)](https://github.com/tox-dev/tox-pipenv/actions)

![PyPI downloads](https://img.shields.io/pypi/dw/tox-pipenv2)

A tox plugin to replace the default use of pip with Pipenv.

* Use `Pipfile` with multiple version of Python
* Use `tox` to deploy strict-pinned dependencies from `Pipfile.lock.{envname}`
  * Update lock files for multiple environments

# Usage

## `tox.ini`

Add `tox-pipenv` to the top level `requires` list. Tox will automatically
provision an environment with the given requirements.

    [tox]
    requires = tox-pipenv

    [testenv]
    command = {posargs}

## `{toxinidir}/Pipfile`

Use `pipenv` to create a `Pipfile` in the project directory, next to `tox.ini`.

For tox environments without `deps`, this plugin will automatically use
`pipenv install` to apply the `Pipfile` to the tox virtualenv.

Environments that specify any `deps` will be _ignored_ by this plugin, as
if `skip_pipenv = true` were set.

### `{toxinidir}/Pipfile.lock.{envname}`

If a lock file exists that matches the current tox environment name, this
plugin will use `pipenv sync` to apply the lockfile into the tox virtualenv.

# Regenerating the lock file

When using lock files ("strict pinning"), the per-environment
`Pipfile.lock.{envname}` must be regenerated whenever `Pipfile` changes or when
updating dependency pins.

```
tox --recreate --pipenv-update
```

Can be used to have this plugin explicitly re-lock the dependencies for each
environment and copy the result to `{toxinidir}/Pipfile.lock.{envname}`.

Subsequent tox invocations without `--pipenv-update` will install the
dependencies specified in the lockfile associated with the environment.

To achieve repeatable deployments, it is recommended to keep the `Pipfile` and
environment-specific lock files in version control.

# Options

## `skip_pipenv`

_bool_. Specified per `[testenv]` section.

If true, this plugin will not take any action in the environment.

## `pipenv_install_opts`

_string_. Specified per `[testenv]` section.

Override the args passed to `pipenv` during the `install_deps` stage.

By default, the plugin will use `install --ignore-pipfile` if a `Pipfile.lock.{envname}` file is present
and `install` when only a `Pipfile` is available.

If this option is specified, the plugin will not modify or augment the argument list,
however if `--pipenv-update` is specified and `update` is not present in the opts, an
exception is raised.

### `TOX_PIPENV_INSTALL_OPTS`

_string_. Environment Variable.

Global override for `pipenv_install_opts` will apply to all environments.

# Virtual Environments

This plugin will use whatever virtualenv tox creates for the test environment,
it does NOT override `tox_testenv_create`.  This allows `tox-pipenv` to work
with other `tox` or `virtualenv` plugins and simplifies the implementation of
the plugin.

Additionally, the environment will not be recreated automatically, even if the
Pipfile or Pipfile.lock are modified.  To re-install or re-sync dependencies,
an explicit `tox --recreate` should be used.

The Pipfile used by an environment will exist in `.tox/{env}/Pipfile` and
`.tox/{env}/Pipfile.lock`.

Note: The 1.x version of this plugin used `pipenv` itself to create the
virtualenv for the test environment.

# Installing requirements

Any test environment that specifies `deps` will NOT use the `Pipfile`.

Similarly if the project does not contain a `Pipfile` or
`Pipfile.lock.{envname}`, then `pipenv` will not be used at all.

To migrate from explicit deps or requirements.txt, use `pipenv install -r
path/to/requirements.txt` to create a new `Pipfile` and edit it accordingly.

# Executing tests

Commands specified in the test environment will run in the virtualenv.
Typically no changes are needed to the commands to take advantage of Pipfile or
locking features.

To execute commands via `pipenv`, for example, scripts defined in the
`Pipfile`, specify `pipenv run whatever` explicitly in the `[testenv]`
`commands` section.

Note: The 1.x version of this plugin used `pipenv` itself to run commands
listed in the test environment.  In the current version, `pipenv` is only used
to install and manage dependencies.

# Example `tox.ini`

This example will test against Python 2.7 and 3.6 using pytest to execute the
tests.

```
[tox]
requires = tox-pipenv
envlist = py27, py36
skipsdist = true

[testenv]
commands = python -m pytest test/
```

## Example `Pipfile`

```
[[source]]
url = "https://pypi.org/simple"
verify_ssl = true
name = "pypi"

[packages]
pytest = "*"
pytest-mock = "*"

[dev-packages]
```

## Locking it Down

```
tox --recreate --pipenv-update --notest
```

Look for the new `Pipfile.lock.py27` and `Pipfile.lock.py36` files created in
the `tox.ini` directory. These may be checked in to version control for
repeatable deployment of locked dependencies.

# Frequently asked questions

## Where to install

`tox-pipenv` should be installed in the same environment as Tox, whether that
is in a virtual environment, system environment or user environment.
`tox-pipenv` depends on Tox 3.0 or newer.

Starting with tox-3.2.0, `tox-pipenv` may be specified in the `[tox]`
`requires` list and automatically provisioned, see examples above.

## Is user expected to create `Pipfile` and `Pipfile.lock.{envname}` before executing `tox` with this plugin?

### Yes

In the absense of `Pipfile` in `toxinidir`, this plugin won't do anything!

### Optional lock file

If a lock file associated with a particular environment exists in `toxinidir`,
then the plugin will use `pipenv sync` to install the locked dependencies.

Without a lock file, `pipenv install` is used to install the latest versions
possible from the Pipfile specification.

#### Note: `Pipfile.lock` is _ignored_

It doesn't make sense to share a lock file between environments, so an
unqualified lock file is not used by this plugin.

#### Is `Pipfile.lock.{envname}` expected to be under source control?

According to `pipenv` documentation, `Pipfile.lock` is not recommended under
source control if it is going to be used under multiple Python versions.

However you may commit environment-specific lock files used by this plugin
to achieve repeatable deployments.

# What is the role of `requirements.txt` file?

`Pipfile` replaces `requirements.txt`.

If your tox environment is currently using `requirements.txt` or
`test_requirements.txt` it is recommended to migrate those dependencies to
`pipenv` and remove the `requirements.txt` file.

# Is `tox.ini` `deps` section really in control?

This plugin _ignores_ any environment with `deps` specified. If an environment
should use Pipfile, then remove the `deps` and manage all dependencies via
`pipenv`.


Authors
-------

* Masen Furer (2.0 rewrite)
* Anthony Shaw
* Omer Katz
* Almog Cohen
