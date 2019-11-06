This addon creates notes based on concept maps that are written in Xmind 8. (see <a href="https://en.wikipedia.org/wiki/Concept_map" rel="nofollow">https://en.wikipedia.org/wiki/Concept_map</a> for an explanation of concept maps) It uses the relationships in the concept maps as questions, concepts following relationships are considered Answers to these questions. Prior relationships and concepts are displayed in a reference on top of the cards created by this addon

You can synchronize your anki notes with the concept map by importing the concept map again.

I will post a github link to this project in the near future, for questions: email me: l.loos95@gmail.com

###How to:
####1. Creating a Concept Map
This addon imports and synchronizes concept maps written in Xmind 8, so the first thing you want to do is write a concept map from the content you want to learn.

[Concept maps](https://en.wikipedia.org/wiki/Concept_map) consist of concepts and relationships. However, since Xmind 8 originally is a mind mapping software, you will write both concepts and relationships into nodes. The Addon recognizes concepts and relationships by their position in the map. It considers nodes at even levels concepts (e.g. "biological psychology" or "perception" in the example sheet "biological psychology") and nodes at odd levels relationships (e.g. "investigates" in the same sheet).

To be able to distinguish relationships and concepts, i recommend you style relationship nodes with a straight line and set up a custom key (preferences -> Keys -> Paste Style) for pasting node styles (I use ctrl + G).

#####Bridges
If you want to structure your concept map without creating any cards, you can place an empty relationship between two concepts.

<img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/bridge.png" alt="bridge" width=64%/> <img src="https://raw.githubusercontent.com/Humorloos/SMR/master/screenshots/bridge_card.png" alt="bridge" width=30%/>

Example: This concept map leads to the creation of the following cards:
<img src="https://imgur.com/vEdMltN.png">

<img src="https://imgur.com/JUvKq7b.png"> 
<img src="https://imgur.com/Wlifi8v.png">
<img src="https://imgur.com/GOAayVp.png">
<img src="https://imgur.com/nOIc6nW.png">
<img src="https://imgur.com/j64DZC7.png">
<img src="https://imgur.com/bSFDllD.png">
<img src="https://imgur.com/D73Ma6o.png">

