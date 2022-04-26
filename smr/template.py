from .consts import *


# receives an id that represents the card to be created and returns a list with
# front and back template
def get_card(cid):
    asw = '{{' + X_FLDS[X_FLDS_IDS[cid + 1]] + '}}'
    if cid == 1:
        card_front = X_CARD_HD + X_CARD_SR1 + X_CARD_QT + X_CARD_BT1 % '...'
        card_back = X_CARD_HD + X_CARD_SR1 + X_CARD_QT + X_CARD_BT1 % asw
    else:
        hint = '<ul>'
        for x in range(1, cid):
            hint = hint + X_CARD_HT % X_FLDS[X_FLDS_IDS[x + 1]]
        hint += '</ul>'
        card_front = '{{#' + X_FLDS[X_FLDS_IDS[cid + 1]] + '}}\n' + \
                     X_CARD_HD + X_CARD_SRN % cid + \
                     X_CARD_QT + hint + X_CARD_BTN % '...' + \
                     '\n{{/' + X_FLDS[X_FLDS_IDS[cid + 1]] + '}}'
        card_back = '{{#' + X_FLDS[X_FLDS_IDS[cid + 1]] + '}}\n' + \
                    X_CARD_HD + X_CARD_SRN % cid + \
                    X_CARD_QT + hint + X_CARD_BTN % asw + \
                    '\n{{/' + X_FLDS[X_FLDS_IDS[cid + 1]] + '}}'
    return [card_front, card_back]


# adds the default smr model to the collection and returns it
def add_x_model(col):
    models = col.models
    x_model = models.new(X_MODEL_NAME)
    # Add fields:
    for fldId in X_FLDS_IDS:
        fld = models.new_field(X_FLDS[fldId])
        models.addField(x_model, fld)
    # Add templates
    for cid, name in enumerate(X_CARD_NAMES, start=1):
        template = models.new_template(name)
        card = get_card(cid)
        template['qfmt'] = card[0]
        template['afmt'] = card[1]
        models.addTemplate(x_model, template)
    set_x_model_fields(x_model)

    models.add(x_model)
    # Set the sort index after adding the model and save again because it is reset to 0 otherwise (see
    # https://forums.ankiweb.net/t/saving-a-model-sets-the-sort-field-index-to-0/2299)
    col.models.set_sort_index(notetype=x_model, idx=list(X_FLDS.keys()).index('id'))
    col.models.save(x_model)
    return x_model

def update_x_model(col):
    x_model = col.models.by_name(X_MODEL_NAME)
    for cid, name in enumerate(X_CARD_NAMES, start=1):
        card = get_card(cid)
        x_model['tmpls'][cid - 1]['qfmt'] = card[0]
        x_model['tmpls'][cid - 1]['afmt'] = card[1]
    set_x_model_fields(x_model)
    col.models.save(x_model)

def set_x_model_fields(x_model):
    x_model['css'] = X_CARD_CSS
    x_model['version'] = X_MODEL_VERSION
