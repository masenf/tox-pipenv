import tox_pipenv.plugin


def test_tox_addoption_smoke(mocker):
    parser = mocker.Mock()
    tox_pipenv.plugin.tox_addoption(parser)
    assert parser.add_argument.mock_calls[0].args == ("--pipenv-update",)
    assert parser.add_testenv_attribute.mock_calls[0].args == ("skip_pipenv",)
    assert parser.add_testenv_attribute.mock_calls[1].args == ("pipenv_install_opts",)
