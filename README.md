This addon creates notes based on concept maps that are written in Xmind 8. (see <a href="https://en.wikipedia.org/wiki/Concept_map" rel="nofollow">https://en.wikipedia.org/wiki/Concept_map</a> for an explanation of concept maps) It uses the relationships in the concept maps as questions, concepts following relationships are considered Answers to these questions. Prior relationships and concepts are displayed in a reference at the beginning of each card.

It also modifies the reviewer so that concept maps are retrieved in a logical order that matches the concept map's structure

You can synchronize your anki notes with the concept map by importing the concept map again.

### How to:
#### 1. Creating a Concept Map
This addon imports and synchronizes concept maps written in Xmind 8, so the first thing you want to do is write a concept map from the content you want to learn.

[Concept maps](https://en.wikipedia.org/wiki/Concept_map) consist of concepts and relationships. However, since Xmind 8 originally is a mind mapping software, you will write both concepts and relationships into nodes. The Addon recognizes concepts and relationships by their position in the map. It considers nodes at even levels concepts (e.g. "biological psychology" or "perception" in the example sheet "biological psychology") and nodes at odd levels relationships (e.g. "investigates" in the same sheet).

To be able to distinguish relationships and concepts, i recommend you style relationship nodes with a straight line and set up a custom key (preferences -> Keys -> Paste Style) for pasting node styles (I use ctrl + G).

##### Bridges
If you want to structure your concept map without creating any cards, you can place an empty relationship between two concepts:
<p align="center">
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/bridge.png" alt="bridge" width=64%/>
    <br>
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/bridge_card.png" alt="bridge card" width=64%/>
</p>

##### Crosslinks
You can use hyperlinks to include crosslinks in your concept map. Including a Hyperlink in an Answer adds the text of the linked node to the answer:
<p align="center">
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/crosslink.png" alt="crosslink" width=64%/>
    <br>
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/crosslink_card.png" alt="crosslink card" width=64%/>
</p>
During card review, questions following linked nodes are treated with a priority one level below sibling questions.

##### Connections
If you don't want certain concepts to be connected in card review without creating any new cards, you can add hyperlinks in combination with bridges:
<p align="center">
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/connection.png" alt="connection" width=64%/>
</p>
During card review, questions following the concept "general psychology" (which is a concept form another sheet in the same Xmind document) are treated with the same priority as questions following linked notes.
<br><br>
If you want to add a crosslink to a specific question to a concept, you can do so by adding a relationship with a hyperlink to the respective question:
<p align="center">
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/linkquestion.png" alt="linkquestion" width=64%/>
</p>
During card review, these questions are treated the same way as sibling questions.

##### Questions following multiple Answers
To include questions following multiple answers, you can place an empty concept next to the answers the relationship is supposed to refer to and add the question to that concept:
<p align="center">
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/mult.png" alt="mult" width=64%/>
    <br>
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/mult_card.png" alt="mult card" width=64%/>
</p>

##### Multimedia
This add on supports import of images, sound files (mp3, wav) and videos (mp4). When importing sounds or videos, make sure you add the files as an attachment to your map instead of just adding a link to the file:
<p align="center">
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/audio.png" alt="audio" width=64%/>
    <br>
    <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/video.png" alt="video" width=64%/>
</p>

Example: This concept map leads to the creation of the following cards:
<img src="https://imgur.com/vEdMltN.png">

<img src="https://imgur.com/JUvKq7b.png"> 
<img src="https://imgur.com/Wlifi8v.png">
<img src="https://imgur.com/GOAayVp.png">
<img src="https://imgur.com/nOIc6nW.png">
<img src="https://imgur.com/j64DZC7.png">
<img src="https://imgur.com/bSFDllD.png">
<img src="https://imgur.com/D73Ma6o.png">

