"""monkey patches"""
import aqt.reviewer as reviewer
from .utils import *

# def initReviewer(self, mw):
#     from .utils import isSMRDeck
#     self.isSMRDeck = isSMRDeck
#     self.mw = mw
#     self.web = mw.web
#     self.card = None
#     self.cardQueue = []
#     self.hadCardQueue = False
#     self._answeredIds = []
#     self._recordedAudio = None
#     self.typeCorrect = None # web init happens before this is set
#     self.state = None
#     self.bottom = aqt.toolbar.BottomBar(mw, mw.bottomWeb)
#     addHook("leech", self.onLeech)
#
# reviewer.Reviewer.__init__ = initReviewer

def showReviewer(self):
    """override for aqt.reviewer.Reviewer.show() method"""
    self.mw.col.reset()
    self.web.resetHandlers()
    self.mw.setStateShortcuts(self._shortcutKeys())
    self.web.onBridgeCmd = self._linkHandler
    self.bottom.web.onBridgeCmd = self._linkHandler
    self._reps = None
    if isSMRDeck(self.mw.col.decks.active()[0], self.mw.col):
        self.SMRMode = True
    self.nextCard()

reviewer.Reviewer.show = showReviewer
