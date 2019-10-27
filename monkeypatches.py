"""monkey patches"""
import aqt.reviewer as reviewer

import anki.sched as scheduler

from .utils import *

# TODO: in xminder add crosslink topics to meta so that they can be
#  distinguished from normal siblings
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
    self.SMRMode = False
    if isSMRDeck(self.mw.col.decks.active()[0], self.mw.col):
        self.SMRMode = True
        self.learnHistory = list()
    self.nextCard()

reviewer.Reviewer.show = showReviewer


def reviewerNextCard(self):
    elapsed = self.mw.col.timeboxReached()
    if elapsed:
        part1 = ngettext("%d card studied in", "%d cards studied in",
                         elapsed[1]) % elapsed[1]
        mins = int(round(elapsed[0] / 60))
        part2 = ngettext("%s minute.", "%s minutes.", mins) % mins
        fin = _("Finish")
        diag = askUserDialog("%s %s" % (part1, part2),
                             [_("Continue"), fin])
        diag.setIcon(QMessageBox.Information)
        if diag.run() == fin:
            return self.mw.moveToState("deckBrowser")
        self.mw.col.startTimebox()
    if self.cardQueue:
        # undone/edited cards to show
        c = self.cardQueue.pop()
        c.startTimer()
        self.hadCardQueue = True
    else:
        if self.hadCardQueue:
            # the undone/edited cards may be sitting in the regular queue;
            # need to reset
            self.mw.col.reset()
            self.hadCardQueue = False
        if self.SMRMode:
            c = self.mw.col.sched.getCard(self.learnHistory)
        else:
            c = self.mw.col.sched.getCard()
    self.card = c
    clearAudioQueue()
    if not c:
        self.mw.moveToState("overview")
        return
    if self._reps is None or self._reps % 100 == 0:
        # we recycle the webview periodically so webkit can free memory
        self._initWeb()
    self._showQuestion()

reviewer.Reviewer.nextCard = reviewerNextCard

def schedGetCard(self, learnHistory=None):
    "Pop the next card from the queue. None if finished."
    self._checkDay()
    if not self._haveQueues:
        self.reset()
    if isinstance(learnHistory, list):
        card = self._getCard(learnHistory)
    else:
        card = self._getCard()
    if card:
        self.col.log(card)
        if not self._burySiblingsOnAnswer:
            self._burySiblings(card)
        self.reps += 1
        card.startTimer()
        return card

scheduler.Scheduler.getCard = schedGetCard

def sched_getCard(self, learnHistory=None):
    "Return the next due card id, or None."
    # learning card due?
    if isinstance(learnHistory, list):
        return self.getNextSMRCard(learnHistory)
    else:
        c = self._getLrnCard()
        if c:
            return c
        # new first, or time for one?
        if self._timeForNewCard():
            c = self._getNewCard()
            if c:
                return c
        # card due for review?
        c = self._getRevCard()
        if c:
            return c
        # day learning card due?
        c = self._getLrnDayCard()
        if c:
            return c
        # new cards left?
        c = self._getNewCard()
        if c:
            return c
        # collapse or finish
        return self._getLrnCard(collapse=True)

scheduler.Scheduler._getCard = sched_getCard

def getNextSMRCard(self, learnHistory):
    print('hi')

scheduler.Scheduler.getNextSMRCard = getNextSMRCard