import pytest

from main.consts import X_MODEL_NAME, X_MAX_ANSWERS, SMR_NOTE_FIELD_NAMES
from main.template import generate_card_template, add_x_model, update_x_model


@pytest.fixture
def template_card_one():
    yield ['<div class="reference"> {{Reference}} </div>\n<span id="s1" style=\'display:none\'>:;:{{Answer 1}}:;:{{'
            'Answer 2}}:;:{{Answer 3}}:;:{{Answer 4}}:;:{{Answer 5}}:;:{{Answer 6}}:;:{{Answer 7}}:;:{{Answer 8}}:;:{'
            '{Answer 9}}:;:{{Answer 10}}:;:{{Answer 11}}:;:{{Answer 12}}:;:{{Answer 13}}:;:{{Answer 14}}:;:{{Answer '
            '15}}:;:{{Answer 16}}:;:{{Answer 17}}:;:{{Answer 18}}:;:{{Answer 19}}:;:{{Answer 20}}</span>\n <script> '
            'var nAnswers = (document.getElementById("s1").textContent.match(/:;:[^(:;:)]+/g) || []).length;\n    if('
            'nAnswers > 1) {\n        document.getElementById("h").innerHTML = "(1 / " + nAnswers + ")"; \n        '
            'document.getElementById("dots").innerHTML = \'<li>\' + document.getElementById("dots").innerHTML + '
            '\'</li>\';\n    }\n</script>\n<hr id="question">\n{{Question}}\n<span id="h">\n</span>\n<hr '
            'id="answer">\n<span id="dots">\n    <span class="dots">\n        ...\n    </span>\n</span>',
            '<div class="reference"> {{Reference}} </div>\n<span id="s1" style=\'display:none\'>:;:{{Answer 1}}:;:{{'
            'Answer 2}}:;:{{Answer 3}}:;:{{Answer 4}}:;:{{Answer 5}}:;:{{Answer 6}}:;:{{Answer 7}}:;:{{Answer 8}}:;:{'
            '{Answer 9}}:;:{{Answer 10}}:;:{{Answer 11}}:;:{{Answer 12}}:;:{{Answer 13}}:;:{{Answer 14}}:;:{{Answer '
            '15}}:;:{{Answer 16}}:;:{{Answer 17}}:;:{{Answer 18}}:;:{{Answer 19}}:;:{{Answer 20}}</span>\n <script> '
            'var nAnswers = (document.getElementById("s1").textContent.match(/:;:[^(:;:)]+/g) || []).length;\n    if('
            'nAnswers > 1) {\n        document.getElementById("h").innerHTML = "(1 / " + nAnswers + ")"; \n        '
            'document.getElementById("dots").innerHTML = \'<li>\' + document.getElementById("dots").innerHTML + '
            '\'</li>\';\n    }\n</script>\n<hr id="question">\n{{Question}}\n<span id="h">\n</span>\n<hr '
            'id="answer">\n<span id="dots">\n    <span class="dots">\n        {{Answer 1}}\n    </span>\n</span>']


@pytest.fixture()
def template_card_five():
    yield ['{{#Answer 5}}\n<div class="reference"> {{Reference}} </div>\n<span id="s1" style=\'display:none\'>:;:{{'
           'Answer 1}}:;:{{Answer 2}}:;:{{Answer 3}}:;:{{Answer 4}}:;:{{Answer 5}}:;:{{Answer 6}}:;:{{Answer 7}}:;:{{'
           'Answer 8}}:;:{{Answer 9}}:;:{{Answer 10}}:;:{{Answer 11}}:;:{{Answer 12}}:;:{{Answer 13}}:;:{{Answer '
           '14}}:;:{{Answer 15}}:;:{{Answer 16}}:;:{{Answer 17}}:;:{{Answer 18}}:;:{{Answer 19}}:;:{{Answer '
           '20}}</span>\n <script> var nAnswers = (document.getElementById("s1").textContent.match(/:;:[^(:;:)]+/g) '
           '|| []).length;document.getElementById("h").innerHTML = "(5 / " + nAnswers + ")";\n</script>\n<hr '
           'id="question">\n{{Question}}\n<span id="h">\n</span>\n<ul><li>\n    <span class="reference">\n        {{'
           'Answer 1}}\n    </span>\n</li>\n<li>\n    <span class="reference">\n        {{Answer 2}}\n    '
           '</span>\n</li>\n<li>\n    <span class="reference">\n        {{Answer 3}}\n    </span>\n</li>\n<li>\n    '
           '<span class="reference">\n        {{Answer 4}}\n    </span>\n</li>\n</ul><hr id="answer">\n<ul>\n    '
           '<li>\n        <span class="dots">\n            ...\n        </span>\n    </li>\n</ul>\n{{/Answer 5}}',
           '{{#Answer 5}}\n<div class="reference"> {{Reference}} </div>\n<span id="s1" style=\'display:none\'>:;:{{'
           'Answer 1}}:;:{{Answer 2}}:;:{{Answer 3}}:;:{{Answer 4}}:;:{{Answer 5}}:;:{{Answer 6}}:;:{{Answer 7}}:;:{{'
           'Answer 8}}:;:{{Answer 9}}:;:{{Answer 10}}:;:{{Answer 11}}:;:{{Answer 12}}:;:{{Answer 13}}:;:{{Answer '
           '14}}:;:{{Answer 15}}:;:{{Answer 16}}:;:{{Answer 17}}:;:{{Answer 18}}:;:{{Answer 19}}:;:{{Answer '
           '20}}</span>\n <script> var nAnswers = (document.getElementById("s1").textContent.match(/:;:[^(:;:)]+/g) '
           '|| []).length;document.getElementById("h").innerHTML = "(5 / " + nAnswers + ")";\n</script>\n<hr '
           'id="question">\n{{Question}}\n<span id="h">\n</span>\n<ul><li>\n    <span class="reference">\n        {{'
           'Answer 1}}\n    </span>\n</li>\n<li>\n    <span class="reference">\n        {{Answer 2}}\n    '
           '</span>\n</li>\n<li>\n    <span class="reference">\n        {{Answer 3}}\n    </span>\n</li>\n<li>\n    '
           '<span class="reference">\n        {{Answer 4}}\n    </span>\n</li>\n</ul><hr id="answer">\n<ul>\n    '
           '<li>\n        <span class="dots">\n            {{Answer 5}}\n        </span>\n    </li>\n</ul>\n{{/Answer '
           '5}}']


def test_generate_card_template_card_one(template_card_one):
    """
    get_card returns correct card template for first card
    """
    act = generate_card_template(1)

    assert act == template_card_one


def test_generate_card_template_card_five(template_card_five):
    """
    get_card returns correct card template for answer 5
    """
    act = generate_card_template(5)

    assert act == template_card_five


def test_add_x_model_then_update_x_model(empty_anki_collection, template_card_one, template_card_five):
    col = empty_anki_collection
    act = add_x_model(col)

    assert len(act['flds']) == len(SMR_NOTE_FIELD_NAMES)
    assert len(act['tmpls']) == X_MAX_ANSWERS
    assert act['name'][:len(X_MODEL_NAME)] == X_MODEL_NAME

    x_model = col.models.byName(X_MODEL_NAME)
    for tmpl in x_model['tmpls']:
        tmpl['qfmt'] = None
        tmpl['afmt'] = None

    update_x_model(col)

    assert [x_model['tmpls'][0]['qfmt'], x_model['tmpls'][0]['afmt']] == template_card_one
    assert [x_model['tmpls'][4]['qfmt'], x_model['tmpls'][4]['afmt']] == template_card_five
