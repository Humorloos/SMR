from consts import X_FLDS, X_FLDS_IDS, X_CARD_HD, X_CARD_SR1, X_CARD_QT, X_CARD_BT1, X_CARD_HT, X_CARD_SRN, X_CARD_BTN, \
    X_MODEL_NAME, X_CARD_NAMES, X_CARD_CSS, X_MODEL_VERSION, X_SORT_FIELD


def generate_card_template(answer_id):
    """
    Generates the front and back side template for a card for a certain answer
    :param answer_id: ordinal number of the answer for which to get the card's template
    :return: a list with the templates for the card's front and back side
    """
    asw = '{{' + X_FLDS[X_FLDS_IDS[answer_id + 1]] + '}}'
    if answer_id == 1:
        card_front = X_CARD_HD + X_CARD_SR1 + X_CARD_QT + X_CARD_BT1 % '...'
        card_back = X_CARD_HD + X_CARD_SR1 + X_CARD_QT + X_CARD_BT1 % asw
    else:
        hint = '<ul>'
        for x in range(1, answer_id):
            hint = hint + X_CARD_HT % X_FLDS[X_FLDS_IDS[x + 1]]
        hint += '</ul>'
        card_front = '{{#' + X_FLDS[X_FLDS_IDS[answer_id + 1]] + '}}\n' + \
                     X_CARD_HD + X_CARD_SRN % answer_id + \
                     X_CARD_QT + hint + X_CARD_BTN % '...' + \
                     '\n{{/' + X_FLDS[X_FLDS_IDS[answer_id + 1]] + '}}'
        card_back = '{{#' + X_FLDS[X_FLDS_IDS[answer_id + 1]] + '}}\n' + \
                    X_CARD_HD + X_CARD_SRN % answer_id + \
                    X_CARD_QT + hint + X_CARD_BTN % asw + \
                    '\n{{/' + X_FLDS[X_FLDS_IDS[answer_id + 1]] + '}}'
    return [card_front, card_back]


def add_x_model(col):
    """
    Adds the smr model to the collection and returns it
    :param col: anki's collection
    :return: the smr model
    """
    models = col.models
    x_model = models.new(X_MODEL_NAME)
    # Add fields:
    for fldId in X_FLDS_IDS:
        fld = models.newField(X_FLDS[fldId])
        models.addField(x_model, fld)
    # Add templates
    for cid, name in enumerate(X_CARD_NAMES, start=1):
        template = models.newTemplate(name)
        card = generate_card_template(cid)
        template['qfmt'] = card[0]
        template['afmt'] = card[1]
        models.addTemplate(x_model, template)
    set_x_model_fields(x_model)

    models.add(x_model)
    return x_model


def update_x_model(col):
    """
    Updates the smr model to the newest version. You can use this function to update the model when the addon was
    updated.
    :param col: anki's collection
    """
    x_model = col.models.byName(X_MODEL_NAME)
    for cid, name in enumerate(X_CARD_NAMES, start=1):
        card = generate_card_template(cid)
        x_model['tmpls'][cid - 1]['qfmt'] = card[0]
        x_model['tmpls'][cid - 1]['afmt'] = card[1]
    set_x_model_fields(x_model)
    col.models.save()


def set_x_model_fields(x_model):
    """
    Sets the model's css, sortf, and vers fields to the specified values
    :param x_model: the smr model dictionary from the collection
    """
    x_model['css'] = X_CARD_CSS
    x_model['sortf'] = list(X_FLDS).index(X_SORT_FIELD)  # set sortfield to ID
    x_model['vers'].append(X_MODEL_VERSION)
