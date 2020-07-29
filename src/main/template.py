from typing import Dict, List

from main.consts import SMR_NOTE_FIELD_NAMES, SMR_FIELD_IDENTIFIERS, X_MODEL_NAME, X_CARD_NAMES, X_MODEL_VERSION, \
    X_MAX_ANSWERS, X_SORT_FIELD

from anki import Collection
from anki.models import ModelManager, NoteType


def get_answer_field_name(answer_id: int) -> str:
    """
    gets the name of the field for the answer with the provided id
    :param answer_id: id of the answer to get the field name for
    :return: the name of the field
    """
    return SMR_NOTE_FIELD_NAMES[SMR_FIELD_IDENTIFIERS[answer_id + 1]]


# HTML for reference (all cards)
REFERENCE_HTML = """<div class="reference"> {reference} </div>
<span id="s1" style='display:none'>:;:{answer_fields}</span>
 <script> var nAnswers = (document.getElementById("s1").textContent.match(/:;:[^(:;:)]+/g) || []).length;""".format(
    reference="{{" + SMR_NOTE_FIELD_NAMES['rf'] + "}}",
    answer_fields="{{" + "}}:;:{{".join(get_answer_field_name(i) for i in range(1, X_MAX_ANSWERS + 1)) + "}}")

# JavaScript Card 1
JAVA_SCRIPT_CARD_1 = """
    if(nAnswers > 1) {
        document.getElementById("h").innerHTML = "(1 / " + nAnswers + ")"; 
        document.getElementById("dots").innerHTML = '<li>' + document.getElementById("dots").innerHTML + '</li>';
    }"""

# JavaScript Card N
JAVA_SCRIPT_CARD_N = """document.getElementById("h").innerHTML = "(%s / " + nAnswers + ")";"""

# HTML for Question (All Cards)
QUESTION_HTML = """
</script>
<hr id="question">
{{%s}}
<span id="h">
</span>
""" % SMR_NOTE_FIELD_NAMES['qt']

# HTML for dots or answer (first card)
BODY_CARD_1_HTML = """<hr id="answer">
<span id="dots">
    <span class="dots">
        %s
    </span>
</span>"""

# HTML for dots or answer (other cards)
BODY_CARD_N_HTML = """<hr id="answer">
<ul>
    <li>
        <span class="dots">
            %s
        </span>
    </li>
</ul>"""

# HTML for one previous answer
PREVIOUS_ANSWER_HTML = """<li>
    <span class="reference">
        {{%s}}
    </span>
</li>
"""

CSS = """.card {
    font-family: arial;
    font-size: 20px;
    text-align: left;
    color: black;
    background-color: white;
}
.reference {
    font-family: arial;
    font-size: 18px;
    text-align: left;
    color: black;
    background-color: white;
}
.dots {
    font-family: arial;
    font-size: 18px;
    text-align: left;
    color: blue;
    background-color: white;
    font-weight: bold;
}"""


def generate_card_template(answer_id: int):
    """
    Generates the front and back side template for a card for a certain answer
    :param answer_id: ordinal number of the answer for which to get the card's template
    :return: a list with the templates for the card's front and back side
    """
    answer_field_name = get_answer_field_name(answer_id)
    answer_field_placeholder: str = '{{' + answer_field_name + '}}'
    if answer_id == 1:
        card_front: str = REFERENCE_HTML + JAVA_SCRIPT_CARD_1 + QUESTION_HTML + BODY_CARD_1_HTML % '...'
        card_back: str = REFERENCE_HTML + JAVA_SCRIPT_CARD_1 + QUESTION_HTML +\
            BODY_CARD_1_HTML % answer_field_placeholder
    else:
        # generate HTML for previous answers
        previous_answers: str = '<ul>'
        for previous_answer_id in range(1, answer_id):
            previous_answers += PREVIOUS_ANSWER_HTML % get_answer_field_name(previous_answer_id)
        previous_answers += '</ul>'

        card_front = '{{#' + answer_field_name + '}}\n' + REFERENCE_HTML + JAVA_SCRIPT_CARD_N % answer_id + \
                     QUESTION_HTML + previous_answers + BODY_CARD_N_HTML % '...' + '\n{{/' + answer_field_name + '}}'
        card_back = '{{#' + answer_field_name + '}}\n' + REFERENCE_HTML + JAVA_SCRIPT_CARD_N % answer_id + \
                    QUESTION_HTML + previous_answers + BODY_CARD_N_HTML % answer_field_placeholder + \
                    '\n{{/' + answer_field_name + '}}'
    return [card_front, card_back]


def add_x_model(col: Collection) -> Dict[str, List[str]]:
    """
    Adds the smr model to the collection and returns it
    :param col: anki's collection
    :return: the smr model
    """
    models: ModelManager = col.models
    x_model: NoteType = models.new(X_MODEL_NAME)
    # Add fields:
    for field_identifier in SMR_FIELD_IDENTIFIERS:
        fld: Dict = models.newField(SMR_NOTE_FIELD_NAMES[field_identifier])
        models.addField(x_model, fld)
    # Add templates
    for cid, name in enumerate(X_CARD_NAMES, start=1):
        template: Dict = models.newTemplate(name)
        card: List[str] = generate_card_template(cid)
        template['qfmt'] = card[0]
        template['afmt'] = card[1]
        models.addTemplate(x_model, template)
    col.models.set_sort_index(nt=x_model, idx=SMR_FIELD_IDENTIFIERS.index(X_SORT_FIELD))
    set_x_model_fields(x_model)
    models.add(x_model)
    return x_model


def update_x_model(col):
    """
    Updates the smr model to the newest version. You can use this function to update the model when the addon was
    updated.
    :param col: anki's collection
    """
    old_model = col.models.byName(X_MODEL_NAME)
    # remove deprecated fields
    fields_2_remove = [field for field in old_model['flds'] if field['name'] not in SMR_NOTE_FIELD_NAMES.values()]
    for field in fields_2_remove:
        col.models.remove_field(m=old_model, field=field)

    for cid, name in enumerate(X_CARD_NAMES, start=1):
        card = generate_card_template(cid)
        old_model['tmpls'][cid - 1]['qfmt'] = card[0]
        old_model['tmpls'][cid - 1]['afmt'] = card[1]
    col.models.set_sort_index(nt=old_model, idx=SMR_FIELD_IDENTIFIERS.index(X_SORT_FIELD))
    set_x_model_fields(old_model)
    col.models.save(old_model)


def set_x_model_fields(x_model: NoteType):
    """
    Sets the model's css and vers fields to the specified values
    :param x_model: the smr model dictionary from the collection
    """
    x_model['css'] = CSS
    x_model['version'] = X_MODEL_VERSION
