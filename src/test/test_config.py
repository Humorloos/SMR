import main.config
from main.consts import X_MODEL_NAME, X_MODEL_VERSION


def test_create_or_update_model_model_up_to_date(mocker):
    # given
    models = {X_MODEL_NAME: {'vers': [X_MODEL_VERSION]}}
    mocker.patch("main.config.mw")
    main.config.mw.col.models.byName.side_effect = models.get
    mocker.patch("main.config.update_x_model")
    mocker.patch("main.config.add_x_model")
    # when
    main.config.create_or_update_model()
    # then
    assert main.config.mw.col.models.byName.call_count == 1
    assert main.config.update_x_model.call_count == 0
    assert main.config.add_x_model.call_count == 0


def test_create_or_update_model_model_out_of_date(mocker):
    # given
    models = {X_MODEL_NAME: {'vers': ['0']}}
    mocker.patch("main.config.mw")
    main.config.mw.col.models.byName.side_effect = models.get
    mocker.patch("main.config.add_x_model")
    mocker.patch("main.config.update_x_model")
    # when
    main.config.create_or_update_model()
    # then
    assert main.config.mw.col.models.byName.call_count == 1
    assert main.config.update_x_model.call_count == 1
    assert main.config.add_x_model.call_count == 0


def test_create_or_update_model_no_model(mocker):
    # given
    models = {}
    mocker.patch("main.config.mw")
    main.config.mw.col.models.byName.side_effect = models.get
    mocker.patch("main.config.update_x_model")
    mocker.patch("main.config.add_x_model")
    # when
    main.config.create_or_update_model()
    # then
    assert main.config.mw.col.models.byName.call_count == 1
    assert main.config.add_x_model.call_count == 1
    assert not main.config.update_x_model.called


def test_get_or_create_smr_world(mocker):
    # given
    mocker.patch('main.config.SmrWorld')
    # when
    main.config.get_or_create_smr_world()
    # then
    assert main.config.SmrWorld.set_up.call_count == 0
    assert main.config.SmrWorld.call_count == 1
