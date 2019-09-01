
X_MODEL_NAME = 'Stepwise Map Retrieval'

X_MAX_ANSWERS = 20
X_CARD_NAMES = list(map(lambda aswid: 'Answer ' + str(aswid), list(range(1, X_MAX_ANSWERS + 1))))

X_FLDS = {
    'id': 'ID',
    'qt': 'Question',
}
for i in range(1, X_MAX_ANSWERS + 1):
    X_FLDS['a' + str(i)] = 'Answer ' + str(i)
X_FLDS.update({
    'rf': 'Reference',
    'mt': 'Meta'
               })

X_FLDS_IDS = ['id', 'qt'] + \
             list(map(lambda aswid: 'a' + str(aswid), list(range(1, X_MAX_ANSWERS + 1)))) + \
             ['rf', 'mt']
