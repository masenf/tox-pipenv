import tox_pipenv.plugin


def test_tox_addoption_smoke(mocker):
    parser = mocker.Mock()
    tox_pipenv.plugin.tox_addoption(parser)
    assert parser.add_argument.call_args[0] == ("--pipenv-update",)
    assert parser.add_testenv_attribute.call_args_list[0][0] == ("skip_pipenv",)
    assert parser.add_testenv_attribute.call_args_list[1][0] == ("pipenv_install_opts",)
