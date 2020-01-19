from aqt.deckbrowser import DeckBrowser
from aqt.main import AnkiQt


# noinspection PyUnresolvedReferences
def smr_linkhandler(self, url):
    if ":" in url:
        (cmd, arg) = url.split(":")
    else:
        cmd = url
    if cmd == "open":
        self._selDeck(arg)
    elif cmd == "opts":
        self._showOptions(arg)
    elif cmd == "shared":
        self._onShared()
    elif cmd == "import":
        self.mw.onImport()
    elif cmd == "lots":
        openHelp("using-decks-appropriately")
    elif cmd == "hidelots":
        self.mw.pm.profile['hideDeckLotsMsg'] = True
        self.refresh()
    elif cmd == "create":
        deck = getOnlyText(_("Name for deck:"))
        if deck:
            self.mw.col.decks.id(deck)
            self.refresh()
    elif cmd == "drag":
        draggedDeckDid, ontoDeckDid = arg.split(',')
        self._dragDeckOnto(draggedDeckDid, ontoDeckDid)
    elif cmd == "collapse":
        self._collapse(arg)
    ############################################################################
    elif cmd == "sync":
        self.mw.onSMRSync()
    ############################################################################
    return False


def onSync(self):
    print()


DeckBrowser._linkHandler = smr_linkhandler
AnkiQt.onSMRSync = onSync
