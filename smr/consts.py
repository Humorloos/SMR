import os
from collections import OrderedDict

# SMR Template information
X_MODEL_VERSION = '0.1.1'
X_MODEL_NAME = 'Stepwise Map Retrieval'
X_MAX_ANSWERS = 20
X_CARD_NAMES = list(map(lambda aswid: 'Answer ' + str(aswid),
                        list(range(1, X_MAX_ANSWERS + 1))))

# Fields, use orderedDict to be able to access flds field in notes objects by
# postition of dictionary key
X_FLDS = OrderedDict((('rf', 'Reference'), ('qt', 'Question')))
for i in range(1, X_MAX_ANSWERS + 1):
    X_FLDS['a' + str(i)] = 'Answer ' + str(i)
X_FLDS.update({
    'id': 'ID',
    'mt': 'Meta'
})

# IDs of Fields
X_FLDS_IDS = ['rf', 'qt'] + \
             list(map(lambda aswid: 'a' + str(aswid),
                      list(range(1, X_MAX_ANSWERS + 1)))) + \
             ['id', 'mt']

# Elements for creating Card-Fronts and Backs

# Header (all Cards)
X_CARD_HD = """<div class="reference">
    {{%(ref)s}}
</div>
<span id="s1" style='display:none'>
    {{%(meta)s}}
</span>
<script>""" % \
            {'ref': X_FLDS['rf'],
             'meta': X_FLDS['mt']}

# JavaScript Card 1
X_CARD_SR1 = """
    var meta = JSON.parse(document.getElementById("s1").textContent);
    var nAnswers = meta.nAnswers;
    if(nAnswers > 1) {
        document.getElementById("h").innerHTML = "(1 / " + nAnswers + ")"; 
        document.getElementById("dots").innerHTML = '<li>' + document.getElementById("dots").innerHTML + '</li>';
    }"""

# JavaScript Card N
X_CARD_SRN = """
    var meta = JSON.parse(document.getElementById("s1").textContent);
    var nAnswers = meta.nAnswers;
    document.getElementById("h").innerHTML = "(%s / " + nAnswers + ")";"""

# Question (All Cards)
X_CARD_QT = """
</script>
<hr id="question">
{{%s}}
<span id="h">
</span>
""" % X_FLDS['qt']

# Bottom (Card 1)
X_CARD_BT1 = """<hr id="answer">
<span id="dots">
    <span class="dots">
        %s
    </span>
</span>"""

# Bottom (Card n)
X_CARD_BTN = """<hr id="answer">
<ul>
    <li>
        <span class="dots">
            %s
        </span>
    </li>
</ul>"""

# Answer hint Card n
X_CARD_HT = """<li>
    <span class="reference">
        {{%s}}
    </span>
</li>
"""

X_CARD_CSS = """.card {
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


ADDON_PATH = os.path.dirname(__file__)

ICONS_PATH = os.path.join(ADDON_PATH, "../icons")
