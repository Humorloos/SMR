from consts import *

def get_card_front(cid):
    if cid == 1:
        card_front = X_CARD_FRONT_HD + X_CARD_FRONT_SR1 + X_CARD_FRONT_QT + X_CARD_FRONT_BT1
    else:
        # hint = '    '
        hint = ''
        for x in range(1, cid):
            hint = hint + X_CARD_FRONT_HT % X_FLDS[X_FLDS_IDS[x + 1]]
        card_front = '{{#' + X_FLDS[X_FLDS_IDS[cid + 1]] + '}}\n' + X_CARD_FRONT_HD + X_CARD_FRONT_SRN % cid + \
                     X_CARD_FRONT_QT + hint + X_CARD_FRONT_BTN + '\n{{/' + X_FLDS[X_FLDS_IDS[cid + 1]] + '}}'
    return card_front
