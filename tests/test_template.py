import pytest
from template import generate_card_template, add_x_model, update_x_model
from consts import X_MODEL_NAME, X_MAX_ANSWERS, X_FLDS, X_SORT_FIELD


@pytest.fixture
def template_card_one():
    yield [
        '<div class="reference">\n    {{Reference}}\n</div>\n<span id="s1" style=\'display:none\'>\n    {{'
        'Meta}}\n</span>\n<script>\n    var meta = JSON.parse(document.getElementById("s1").textContent);\n    var '
        'nAnswers = meta.nAnswers;\n    if(nAnswers > 1) {\n        document.getElementById("h").innerHTML = "(1 / " '
        '+ nAnswers + ")"; \n        document.getElementById("dots").innerHTML = \'<li>\' + document.getElementById('
        '"dots").innerHTML + \'</li>\';\n    }\n</script>\n<hr id="question">\n{{Question}}\n<span '
        'id="h">\n</span>\n<hr id="answer">\n<span id="dots">\n    <span class="dots">\n        ...\n    '
        '</span>\n</span>',
        '<div class="reference">\n    {{Reference}}\n</div>\n<span id="s1" style=\'display:none\'>\n    {{'
        'Meta}}\n</span>\n<script>\n    var meta = JSON.parse(document.getElementById("s1").textContent);\n    var '
        'nAnswers = meta.nAnswers;\n    if(nAnswers > 1) {\n        document.getElementById("h").innerHTML = "(1 / " '
        '+ nAnswers + ")"; \n        document.getElementById("dots").innerHTML = \'<li>\' + document.getElementById('
        '"dots").innerHTML + \'</li>\';\n    }\n</script>\n<hr id="question">\n{{Question}}\n<span '
        'id="h">\n</span>\n<hr id="answer">\n<span id="dots">\n    <span class="dots">\n        {{Answer 1}}\n    '
        '</span>\n</span>']


@pytest.fixture()
def template_card_five():
    yield [
        '{{#Answer 5}}\n<div class="reference">\n    {{Reference}}\n</div>\n<span id="s1" style=\'display:none\'>\n   '
        ' {{Meta}}\n</span>\n<script>\n    var meta = JSON.parse(document.getElementById("s1").textContent);\n    var '
        'nAnswers = meta.nAnswers;\n    document.getElementById("h").innerHTML = "(5 / " + nAnswers + '
        '")";\n</script>\n<hr id="question">\n{{Question}}\n<span id="h">\n</span>\n<ul><li>\n    <span '
        'class="reference">\n        {{Answer 1}}\n    </span>\n</li>\n<li>\n    <span class="reference">\n        {{'
        'Answer 2}}\n    </span>\n</li>\n<li>\n    <span class="reference">\n        {{Answer 3}}\n    '
        '</span>\n</li>\n<li>\n    <span class="reference">\n        {{Answer 4}}\n    </span>\n</li>\n</ul><hr '
        'id="answer">\n<ul>\n    <li>\n        <span class="dots">\n            ...\n        </span>\n    '
        '</li>\n</ul>\n{{/Answer 5}}',
        '{{#Answer 5}}\n<div class="reference">\n    {{Reference}}\n</div>\n<span id="s1" style=\'display:none\'>\n   '
        ' {{Meta}}\n</span>\n<script>\n    var meta = JSON.parse(document.getElementById("s1").textContent);\n    var '
        'nAnswers = meta.nAnswers;\n    document.getElementById("h").innerHTML = "(5 / " + nAnswers + '
        '")";\n</script>\n<hr id="question">\n{{Question}}\n<span id="h">\n</span>\n<ul><li>\n    <span '
        'class="reference">\n        {{Answer 1}}\n    </span>\n</li>\n<li>\n    <span class="reference">\n        {{'
        'Answer 2}}\n    </span>\n</li>\n<li>\n    <span class="reference">\n        {{Answer 3}}\n    '
        '</span>\n</li>\n<li>\n    <span class="reference">\n        {{Answer 4}}\n    </span>\n</li>\n</ul><hr '
        'id="answer">\n<ul>\n    <li>\n        <span class="dots">\n            {{Answer 5}}\n        </span>\n    '
        '</li>\n</ul>\n{{/Answer 5}}']


# get_card returns correct card template for first card
def test_generate_card_template_card_one(template_card_one):
    act = generate_card_template(1)

    assert act == template_card_one


# get_card returns correct card template for answer 5
def test_card_five(template_card_five):
    act = generate_card_template(5)

    assert act == template_card_five


def test_add_and_then_update_x_model(empty_anki_collection, template_card_one, template_card_five):
    col = empty_anki_collection
    act = add_x_model(col)

    assert len(act['flds']) == len(X_FLDS)
    assert len(act['tmpls']) == X_MAX_ANSWERS
    assert act['name'][:len(X_MODEL_NAME)] == X_MODEL_NAME
    assert act['sortf'] == list(X_FLDS).index(X_SORT_FIELD)

    x_model = col.models.byName(X_MODEL_NAME)
    for tmpl in x_model['tmpls']:
        tmpl['qfmt'] = None
        tmpl['afmt'] = None

    update_x_model(col)

    assert [x_model['tmpls'][0]['qfmt'], x_model['tmpls'][0]['afmt']] == template_card_one
    assert [x_model['tmpls'][4]['qfmt'], x_model['tmpls'][4]['afmt']] == template_card_five
