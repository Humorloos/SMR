"""monkey patches"""
import random
import time

from aqt.qt import *
from aqt.utils import askUserDialog
import aqt.reviewer as reviewer

# noinspection PyProtectedMember
from anki.lang import _, ngettext
from anki.sound import clearAudioQueue
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
    self.mw.col.reset()
    self.web.resetHandlers()
    self.mw.setStateShortcuts(self._shortcutKeys())
    self.web.onBridgeCmd = self._linkHandler
    self.bottom.web.onBridgeCmd = self._linkHandler
    self._reps = None
    ############################################################################
    self.SMRMode = False
    if isSMRDeck(self.mw.col.decks.active()[0], self.mw.col):
        self.SMRMode = True
        self.learnHistory = list()
    ############################################################################
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
        ########################################################################
        if self.SMRMode:
            c = self.mw.col.sched.getCard(self.learnHistory)
            if len(self.learnHistory) > 0 and self.learnHistory[-1][0] == c.nid:
                self.learnHistory[-1][1].append(c.id)
            else:
                self.learnHistory.append([c.nid, [c.id]])
        else:
            ####################################################################
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
    ############################################################################
    if isinstance(learnHistory, list):
        card = self._getCard(learnHistory)
    else:
        ########################################################################
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
    ############################################################################
    if isinstance(learnHistory, list):
        return self.getNextSMRCard(learnHistory)
    else:
        ########################################################################
        # learning card due?
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

    self._lrnQueue = self.col.db.list("""
    select id from cards where did in %s and queue = 1 and due < :lim""" %
                                      self._deckLimit(), lim=self.dayCutoff)

    self._revQueue = self.col.db.list("""
        select id from cards where did = ? and queue = 2 and due <= ?""",
                                      self._revDids[0], self.today)

    self._newQueue = self.col.db.list("""
        select id from cards where did = ? and queue = 0 order by due, ord""",
                                      self._revDids[0])

    lrnNids = list(set(self.col.db.list(
        """select nid from cards where id in """ + ids2str(self._lrnQueue))))
    revNids = list(set(self.col.db.list(
        """select nid from cards where id in """ + ids2str(self._revQueue))))
    newNids = list(set(self.col.db.list(
        """select nid from cards where id in """ + ids2str(self._newQueue))))
    allNids = lrnNids + revNids + newNids

    if len(learnHistory) == 0:
        # get shortest sortID among available notes
        minIDLength = self.col.db.list("""
            select min(length(sfld)) from notes where id in """ + ids2str(
            allNids))

        startingNotes = self.col.db.list(
            "select id from notes where LENGTH(sfld) = ? and id in " + ids2str(
                lrnNids), minIDLength[0])
        if len(startingNotes) == 0:
            startingNotes = self.col.db.list(
                "select id from notes where LENGTH(sfld) = ? and id in " +
                ids2str(revNids), minIDLength[0])
        if len(startingNotes) == 0:
            startingNotes = self.col.db.list(
                "select id from notes where LENGTH(sfld) = ? and id in " +
                ids2str(newNids), minIDLength[0])

        startingNote = random.choice(startingNotes)

        return self.getNextAnswer(startingNote, 0)

    lastNoteLst = learnHistory[-1]
    dueAnswers = self._lrnQueue + self._revQueue + self._newQueue
    dueAw2Note = list(self.col.db.execute(
        """select id, ord from cards where nid = ? and id in """ + ids2str(
            dueAnswers), lastNoteLst[0]))
    awOrds = list(map(lambda t: t[1], dueAw2Note))

    lastCard = self.col.getCard(lastNoteLst[1][-1])
    lastOrd = lastCard.ord

    if len(dueAw2Note) > 0 and max(awOrds) > lastOrd:
        return self.getNextAnswer(lastNoteLst[0], lastOrd + 1)


scheduler.Scheduler.getNextSMRCard = getNextSMRCard


def getNextAnswer(self, nid, aId):
    dueAnswers = self._lrnQueue + self._revQueue + self._newQueue
    dueAw2Note = list(self.col.db.execute(
        """select id, ord from cards where nid = ? and id in """ + ids2str(
            dueAnswers), nid))
    awOrds = list(map(lambda t: t[1], dueAw2Note))
    nextOrd = min(filter(lambda o: o >= aId, awOrds))
    answerId = dueAw2Note[awOrds.index(nextOrd)][0]

    return self.col.getCard(answerId)


scheduler.Scheduler.getNextAnswer = getNextAnswer


def schedAnswerLrnCard(self, card, ease):
    # ease 1=no, 2=yes, 3=remove
    conf = self._lrnConf(card)
    if card.odid and not card.wasNew:
        type = 3
    elif card.type == 2:
        type = 2
    else:
        type = 0
    leaving = False
    # lrnCount was decremented once when card was fetched
    lastLeft = card.left
    # immediate graduate?
    if ease == 3:
        self._rescheduleAsRev(card, conf, True)
        leaving = True
    # graduation time?
    elif ease == 2 and (card.left % 1000) - 1 <= 0:
        self._rescheduleAsRev(card, conf, False)
        leaving = True
    else:
        # one step towards graduation
        if ease == 2:
            # decrement real left count and recalculate left today
            left = (card.left % 1000) - 1
            card.left = self._leftToday(conf['delays'], left) * 1000 + left
        # failed
        else:
            card.left = self._startingLeft(card)
            resched = self._resched(card)
            if 'mult' in conf and resched:
                # review that's lapsed
                card.ivl = max(1, conf['minInt'], card.ivl * conf['mult'])
            else:
                # new card; no ivl adjustment
                pass
            if resched and card.odid:
                card.odue = self.today + 1
        delay = self._delayForGrade(conf, card.left)
        if card.due < time.time():
            # not collapsed; add some randomness
            delay *= random.uniform(1, 1.25)
        card.due = int(time.time() + delay)
        # due today?
        if card.due < self.dayCutoff:
            self.lrnCount += card.left // 1000
            # if the queue is not empty and there's nothing else to do, make
            # sure we don't put it at the head of the queue and end up showing
            # it twice in a row
            card.queue = 1
            if self._lrnQueue and not self.revCount and not self.newCount:
                smallestDue = self._lrnQueue[0][0]
                card.due = max(card.due, smallestDue + 1)
                ################################################################
            # heappush(self._lrnQueue, (card.due, card.id))
            ####################################################################
        else:
            # the card is due in one or more days, so we need to use the
            # day learn queue
            ahead = ((card.due - self.dayCutoff) // 86400) + 1
            card.due = self.today + ahead
            card.queue = 3
    self._logLrn(card, ease, conf, leaving, type, lastLeft)

scheduler.Scheduler._answerLrnCard = schedAnswerLrnCard