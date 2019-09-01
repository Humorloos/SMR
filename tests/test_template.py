from template import get_card_front
import nose


# get_card front returns correct Front card template for first card
def test_card_front():
    act = get_card_front(1)

    exp: str = """<div class="reference">
    {{Reference}}
</div>
<span id="s1" style='display:none'>
    {{Meta}}
</span>
<script>
    var meta = JSON.parse(document.getElementById("s1").textContent);
    var nAnswers = meta.answers.length;
    if(nAnswers > 1) {
        document.getElementById("h").innerHTML = "(1 / " + nAnswers + ")";
        document.getElementById("dots").innerHTML = '<li><span class="dots">...</span></li>';
    } else {
        document.getElementById("dots").innerHTML = '<span class="dots">...</span>';
    }
</script>
<hr id="question">
    {{Question}}
<span id="h">
</span>
<hr id="answer">
<span id="dots">
</span>"""

    assert act == exp


def test_card_front_five():
    act = get_card_front(5)

    exp: str = """{{#Answer 5}}
<div class="reference">
    {{Reference}}
</div>
<span id="s1" style='display:none'>
    {{Meta}}
</span>
<script>
    var meta = JSON.parse(document.getElementById("s1").textContent);
    var nAnswers = meta.answers.length;
    document.getElementById("h").innerHTML = "(5 / " + nAnswers + ")";
</script>
<hr id="question">
{{Question}}
<span id="h">
</span>
<li>
    <span class="reference">
        {{Answer 1}}
    </span>
</li>
<li>
    <span class="reference">
        {{Answer 2}}
    </span>
</li>
<li>
    <span class="reference">
        {{Answer 3}}
    </span>
</li>
<li>
    <span class="reference">
        {{Answer 4}}
    </span>
</li>
<hr id="answer">
<li>
    <span class="dots">
        ...
    </span>
</li>
{{/Answer 5}}"""
    assert act == exp


if __name__ == '__main__':
    nose.run()
