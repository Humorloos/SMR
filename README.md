## Stepwise Map Retrieval

#### Table of Contents  
**[1. Creating a concept map](https://github.com/Humorloos/SMR#1-creating-a-concept-map)** <br>
<sup>
[Bridges](https://github.com/Humorloos/SMR#bridges)<br>
[Crosslinks](https://github.com/Humorloos/SMR#crosslinks)<br>
[Connections](https://github.com/Humorloos/SMR#connections)<br>
[Questions following multiple Answers](https://github.com/Humorloos/SMR#questions-following-multiple-answers)<br>
[Multimedia](https://github.com/Humorloos/SMR#multimedia)<br>
[Answer Limit](https://github.com/Humorloos/SMR#answer-limit)<br>
</sup>
**[2. Importing your concept maps](https://github.com/Humorloos/SMR#2-importing-your-concept-maps)**<br>
**[3. Synchronizing your concept maps](https://github.com/Humorloos/SMR#3-synchronizing-your-concept-maps)**<br>
<sup>
[Repair Checkbox](https://github.com/Humorloos/SMR#repair-checkbox)<br>
</sup>
**[4. Reviewing your cards](https://github.com/Humorloos/SMR#4-reviewing-your-cards)**

### 1. Creating a concept map
Stepwise Map Retrieval (SMR) imports and synchronizes concept maps written in [Xmind8](https://www.xmind.net/download/xmind8), so the first thing you want to do is write a concept map from the content you want to learn.

[Concept maps](https://en.wikipedia.org/wiki/Concept_map) consist of concepts and relationships. However, since Xmind 8 originally is a mind mapping software, you will write both concepts and relationships into nodes. SMR recognizes concepts and relationships by their position in the map. It considers nodes at even levels (e.g. "biological psychology" or "perception" in the example sheet "biological psychology") concepts and nodes at odd levels (e.g. "investigates" in the same sheet) relationships.
<p align="center">
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/example.png" alt="connection" width=100%/>
</p>

To be able to distinguish relationships and concepts, i recommend you style relationship nodes with a straight line and set up a custom key (preferences -> Keys -> Paste Style) for pasting node styles (I use ctrl + G). I usually use logic chart structure for my concept maps, but for SMR to work, any structure should be fine.

#### Bridges
If you want to structure your concept map without creating any cards, you can place an empty relationship between two concepts:
<p align="center">
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/bridge.png" alt="bridge" width=64%/>
    <br>
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/bridge_card.png" alt="bridge card" width=64%/>
</p>

#### Crosslinks
You can use hyperlinks to include crosslinks in your concept map. Including a Hyperlink in an Answer adds the text of the linked node to the answer:
<p align="center">
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/crosslink.png" alt="crosslink" width=64%/>
    <br>
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/crosslink_card.png" alt="crosslink card" width=64%/>
</p>
During card review, questions following linked nodes are treated with a priority one level below sibling questions.

#### Connections
If you want certain concepts to be connected in card review without creating any new cards, you can add hyperlinks in combination with bridges:
<p align="center">
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/connection.png" alt="connection" width=64%/>
</p>
During card review, questions following the concept "general psychology" (which is a concept form another sheet in the same Xmind document) will be treated with the same priority as questions following linked notes.
<br><br>
If you want to add a crosslink to a specific question to a concept, you can do so by adding a relationship with a hyperlink to the respective question:
<p align="center">
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/linkquestion.png" alt="linkquestion" width=64%/>
</p>
During card review, these questions are treated the same way as sibling questions.

#### Questions following multiple Answers
To include questions following multiple answers, you can place an empty concept next to the answers the relationship is supposed to refer to and add the question to that concept:
<p align="center">
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/mult.png" alt="mult" width=64%/>
    <br>
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/mult_card.png" alt="mult card" width=64%/>
</p>

#### Multimedia
SMR supports import of images, sound files (mp3, wav) and videos (mp4). When importing sounds or videos, make sure you add the files as an attachment to your map instead of just adding a link to the file:
<p align="center">
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/audio.png" alt="audio" width=64%/>
    <br>
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/video.png" alt="video" width=64%/>
</p>

#### Answer Limit
If a concept map contains questions with more than 20 answers, the import will not work. However, there is no limit to the number of questions following an answer.

### 2. Importing your concept maps
To import a concept map all you have to do is click the "Import File" button at the bottom of the main window and choose the Xmind file that contains the map you want to import. The dialogue that pops up will let you choose the deck you want to import the notes to, choose the sheets that you want to import and assign a name to each of the sheets. Notes that you create for a certain sheet will contain a tag with the name of the deck the sheet was imported into and the name that was assigned to it in this dialogue.
<p align="center">
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/sheetselector_1.png" alt="sheetselector 1" width=64%/>
    <br>
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/sheetselector_mult.png" alt="sheetselector mult" width=64%/>
</p>

### 3. Synchronizing your concept maps
To import changes made to your concept maps into your anki notes, all you have to do is import the corresponding sheets again.

#### Repair checkbox
Sometimes Xmind 8 experiences some serious bugs with the program crashing every time you try to edit a concept map. The only solution to this problem that I have found until now is to open the map with [Xmind Zen](https://www.xmind.net/download/), make the necessary changes, save it from there and open it again in Xmind 8. However, after doing this, SMR will no more recognize the concept map and won't synchronize an existing map but import it again. To be able to synchronize again, you need to import the map once with the repair checkbox checked. However, make sure that the map is the same as before you saved it in Xmind Zen because any notes affected by changes will be removed and imported again and your progress would be lost.

### 4. Reviewing your cards
SMR comes with a custom reviewing algorithm that roughly follows these preferences:
1. The first note you study will always be the note at the highest hierarchy level
2. If a note contains multiple answers, the first due answer will always be asked first, followed by subsequent answers
3. If a note has children (questions following answers), they will be asked next. If none are due, children of children will be asked etc.
4. If a note has Siblings (questions following the same parent node), they will be asked next.
5. If a note has connections, they will be asked last.
6. If no more subsequent notes are left, Anki will present you another note at the highest hierarchy level.

If there are multiple notes with the same priority, "learning" cards will be chosen first, then "review" cards and then "new" cards.