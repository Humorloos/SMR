import smr.config as config
from smr.consts import X_MODEL_NAME, X_MODEL_VERSION


def test_create_or_update_model_model_up_to_date(mocker):
    # given
    models = {X_MODEL_NAME: {'vers': [X_MODEL_VERSION]}}
    mocker.patch("smr.config.mw")
    config.mw.col.models.byName.side_effect = models.get
    mocker.patch("smr.config.update_x_model")
    mocker.patch("smr.config.add_x_model")
    # when
    config.create_or_update_model()
    # then
    assert config.mw.col.models.byName.call_count == 1
    assert config.update_x_model.call_count == 0
    assert config.add_x_model.call_count == 0


def test_create_or_update_model_model_out_of_date(mocker):
    # given
    models = {X_MODEL_NAME: {'vers': ['0']}}
    mocker.patch("smr.config.mw")
    config.mw.col.models.byName.side_effect = models.get
    mocker.patch("smr.config.add_x_model")
    mocker.patch("smr.config.update_x_model")
    # when
    config.create_or_update_model()
    # then
    assert config.mw.col.models.byName.call_count == 1
    assert config.update_x_model.call_count == 1
    assert config.add_x_model.call_count == 0


def test_create_or_update_model_no_model(mocker):
    # given
    models = {}
    mocker.patch("smr.config.mw")
    config.mw.col.models.byName.side_effect = models.get
    mocker.patch("smr.config.update_x_model")
    mocker.patch("smr.config.add_x_model")
    # when
    config.create_or_update_model()
    # then
    assert config.mw.col.models.byName.call_count == 1
    assert config.add_x_model.call_count == 1
    assert not config.update_x_model.called


def test_get_or_create_smr_world(mocker):
    # given
    mocker.patch('smr.config.SmrWorld')
    # when
    config.get_or_create_smr_world()
    # then
    assert config.SmrWorld.set_up.call_count == 0
    assert config.SmrWorld.call_count == 1
