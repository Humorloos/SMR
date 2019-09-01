from template import get_card
import nose


# get_card returns correct card template for first card
def test_card():
    act = get_card(1)

    exp = """<div class="reference">
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
        document.getElementById("dots").innerHTML = '<li><span class="dots"> ... </span></li>';
    } else {
        document.getElementById("dots").innerHTML = '<span class="dots"> ... </span>';
    }
</script>
<hr id="question">
{{Question}}
<span id="h">
</span>
<hr id="answer">
<span id="dots">
</span>"""

    assert act[0] == exp

# get_card returns correct card template for answer 5
def test_card_five():
    act = get_card(5)

    exp = """{{#Answer 5}}
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
        {{Answer 5}}
    </span>
</li>
{{/Answer 5}}"""
    assert act[1] == exp

