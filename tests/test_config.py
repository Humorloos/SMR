import config
import pytest
from consts import X_MODEL_NAME, X_MODEL_VERSION


def test_get_or_create_model_model_up_to_date(mocker):
    # given
    models = {X_MODEL_NAME: {'vers': [X_MODEL_VERSION]}}
    mocker.patch("config.mw")
    config.mw.col.models.byName.side_effect = models.get
    # when
    act = config.get_or_create_model()
    # then
    assert act == models[X_MODEL_NAME]
    assert config.mw.col.models.byName.call_count == 1


def test_get_or_create_model_model_out_of_date(mocker):
    # given
    models = {X_MODEL_NAME: {'vers': ['0']}}
    mocker.patch("config.mw")
    config.mw.col.models.byName.side_effect = models.get
    mocker.patch("config.update_x_model")
    # when
    act = config.get_or_create_model()
    # then
    assert act == models[X_MODEL_NAME]
    assert config.mw.col.models.byName.call_count == 1
    assert config.update_x_model.call_count == 1


def test_get_or_create_model_no_model(mocker):
    # given
    models = {}
    mocker.patch("config.mw")
    config.mw.col.models.byName.side_effect = models.get
    mocker.patch("config.update_x_model")
    mocker.patch("config.add_x_model")
    # when
    config.get_or_create_model()
    # then
    assert config.mw.col.models.byName.call_count == 1
    assert config.add_x_model.call_count == 1
    assert not config.update_x_model.called


def test_get_or_create_smr_world(mocker):
    # given
    mocker.patch('config.SmrWorld')
    # when
    smr_world = config.get_or_create_smr_world()
    # then
    assert config.SmrWorld.set_up.call_count == 0
    assert config.SmrWorld.call_count == 1
