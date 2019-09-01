
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

# Elements for creating Card-Fronts

# Header (all Cards)
X_CARD_FRONT_HD = """<div class="reference">
    {{%(ref)s}}
</div>
<span id="s1" style='display:none'>
    {{%(meta)s}}
</span>
<script>""" % \
                  {'ref': X_FLDS['rf'],
                   'meta': X_FLDS['mt']}

# JavaScript Card 1
X_CARD_FRONT_SR1 = """
    var meta = JSON.parse(document.getElementById("s1").textContent);
    var nAnswers = meta.answers.length;
    if(nAnswers > 1) {
        document.getElementById("h").innerHTML = "(1 / " + nAnswers + ")";
        document.getElementById("dots").innerHTML = '<li><span class="dots">...</span></li>';
    } else {
        document.getElementById("dots").innerHTML = '<span class="dots">...</span>';
    }"""

# JavaScript Card N
X_CARD_FRONT_SRN = """
    var meta = JSON.parse(document.getElementById("s1").textContent);
    var nAnswers = meta.answers.length;
    document.getElementById("h").innerHTML = "(%s / " + nAnswers + ")";"""

# Question (All Cards)
X_CARD_FRONT_QT = """
</script>
<hr id="question">
{{%s}}
<span id="h">
</span>
""" % X_FLDS['qt']

# Bottom (Card 1)
X_CARD_FRONT_BT1 = """<hr id="answer">
<span id="dots">
</span>"""

# Bottom (Card n)
X_CARD_FRONT_BTN = """<hr id="answer">
<li>
    <span class="dots">
        ...
    </span>
</li>"""

# Answer hint Card n
X_CARD_FRONT_HT = """<li>
    <span class="reference">
        {{%s}}
    </span>
</li>
"""
