from textwrap import dedent


TOX_INI_PIPFILE_SIMPLE = dedent(
    """
    [tox]
    skipsdist = True
    envlist = py

    [testenv]
    commands = pip freeze""",
)


TOX_INI_PIPFILE_INSTALL_COMMAND = dedent(
    """
    [tox]
    skipsdist = True
    envlist = py

    [testenv]
    install_command = {install_command}
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
