"""monkey patches"""

# noinspection PyProtectedMember
import json
import random
import time
import os
from typing import Callable, Union, Any, cast

from anki import scheduler
from anki.cards import CardId
from anki.utils import ids2str
from anki.hooks import wrap
from anki.importing.noteimp import NoteImporter
from aqt import importing, deckbrowser, reviewer
from aqt.deckbrowser import DeckBrowser
from aqt.importing import ImportDialog
from aqt.main import AnkiQt
from aqt.utils import tooltip, showText

from .consts import X_FLDS
from .exportsync import MapSyncer
from .utils import isSMRDeck, getDueAnswersToNote, getNotesFromQIds
from .xminder import XmindImporter
from .ui.deckselectiondialog import DeckSelectionDialog

IMPORT_CANCELLED_MESSAGE = 'Import cancelled'


def patch_import_dialog(self: ImportDialog, mw: AnkiQt, importer: Union[NoteImporter, XmindImporter],
                        _old: Callable) -> None:
    """
    Wraps around ImportDialog constructor to show the SMR deck selection dialog instead when importing an xmind file
    :param self: the ImportDialog around which this function wraps
    :param mw: the Anki main window
    :param importer: the NoteImporter instance that is used with the import dialog
    :param _old: the constructor around which this function wraps
    """
    if type(importer) == XmindImporter:
        # noinspection PyUnresolvedReferences
        deck_selection_dialog = DeckSelectionDialog(mw=mw, filename=os.path.basename(importer.file))
        deck_selection_dialog.deck.cleanup()
        user_inputs = deck_selection_dialog.get_inputs()
        if user_inputs.running:
            # noinspection PyUnresolvedReferences
            importer.importSheets(user_inputs)
            log = "\n".join(importer.log)
        else:
            log = IMPORT_CANCELLED_MESSAGE
        if "\n" not in log:
            tooltip(log)
        else:
            showText(log)
        return
    _old(self, mw, importer)


importing.ImportDialog.__init__ = wrap(importing.ImportDialog.__init__, patch_import_dialog, pos="around")


# noinspection PyPep8Naming
def patch__linkHandler(self, url: str, _old: Callable) -> Any:
    """
    Wraps around Deckbrowser's method _linkHandler() to trigger smr synchronization when users click the smr sync
    button in deckbrowser
    :param self: the deckbrowser
    :param url: the command the linkhandler is supposed to be called with
    :param _old: The actual _linkHandler() method around which this function wraps
    :return: Nothing when the called with "sync", else the _linkHandler()'s return value
    """
    if url == "sync":
        mapSyncer = MapSyncer()
        mapSyncer.syncMaps()
        return
    return _old(self, url)


deckbrowser.DeckBrowser._linkHandler = wrap(DeckBrowser._linkHandler, patch__linkHandler, pos="around")


def patch_show(self):
    self.SMRMode = False
    if isSMRDeck(self.mw.col.decks.active()[0], self.mw.col):
        self.SMRMode = True
        self.learnHistory = list()


reviewer.Reviewer.show = wrap(old=reviewer.Reviewer.show, new=patch_show, pos='before')


def patch__get_next_v1_v2_card(self, _old):
    if self.SMRMode:
        c = self.mw.col.sched.getNextSMRCard(self.learnHistory)
        if not c:
            self.mw.moveToState("overview")
            return
        if len(self.learnHistory) > 0 and self.learnHistory[-1][0] == c.nid:
            self.learnHistory[-1][1].append(c.id)
        else:
            self.learnHistory.append([c.nid, [c.id]])
        c.start_timer()
        self.card = c
        return
    _old(self)


reviewer.Reviewer._get_next_v1_v2_card = wrap(old=reviewer.Reviewer._get_next_v1_v2_card,
                                              new=patch__get_next_v1_v2_card, pos='around')


def getNextSMRCard(self, learnHistory):
    self._lrnQueue = self.col.db.all("""
        select due, id from cards where did in %s and queue = 1 and due < ?""" %
                                     self._deck_limit(), time.time())
    self._lrnQueue = [cast(tuple[int, CardId], tuple(e)) for e in self._lrnQueue]
    self.lrnCount = len(self._lrnQueue)

    self._revQueue = self.col.db.list("""
        select id from cards where did = ? and queue = 2 and due <= ?""",
                                      self._lrnDids[0], self.today)
    self.revCount = len(self._revQueue)

    self._newQueue = self.col.db.list("""
        select id from cards where did = ? and queue = 0 order by due, ord""",
                                      self._lrnDids[0])
    self.newCount = len(self._newQueue)

    nidList = dict()
    nidList['lrn'] = list(set(self.col.db.list(
        """select nid from cards where id in """ + ids2str([t[1] for t in self._lrnQueue]))))
    nidList['rev'] = list(set(self.col.db.list(
        """select nid from cards where id in """ + ids2str(self._revQueue))))
    nidList['new'] = list(set(self.col.db.list(
        """select nid from cards where id in """ + ids2str(self._newQueue))))
    nidList['all'] = nidList['lrn'] + nidList['rev'] + nidList['new']

    # if the user starts studying or a branch was completely studied
    if len(learnHistory) == 0:
        # get shortest sortID among available notes
        minIDLength = self.col.db.list("""
            select min(length(sfld)) from notes where id in """ + ids2str(
            nidList['all']))
        startingNotes = self.col.db.list(
            "select id from notes where LENGTH(sfld) = ? and id in " + ids2str(
                nidList['lrn']), minIDLength[0])
        if len(startingNotes) == 0:
            startingNotes = self.col.db.list(
                "select id from notes where LENGTH(sfld) = ? and id in " +
                ids2str(nidList['rev']), minIDLength[0])
        if len(startingNotes) == 0:
            startingNotes = self.col.db.list(
                "select id from notes where LENGTH(sfld) = ? and id in " +
                ids2str(nidList['new']), minIDLength[0])
        if len(startingNotes) == 0:
            return None

        startingNote = random.choice(startingNotes)

        return self.getNextAnswer(startingNote, 0)

    # get last from last note that was studied
    lastNoteLst = learnHistory[-1]
    dueAnswers = [t[1] for t in self._lrnQueue] + self._revQueue + self._newQueue
    dueAw2Note = getDueAnswersToNote(nId=lastNoteLst[0], dueAnswers=dueAnswers,
                                     col=self.col)
    awOrds = list(map(lambda t: t['ord'], dueAw2Note))

    lstCrd = self.col.get_card(lastNoteLst[1][-1])

    # if that note has further due answers that follow it, return the next
    # Answer
    if len(dueAw2Note) > 0 and max(awOrds) > lstCrd.ord:
        return self.getNextAnswer(lastNoteLst[0], lstCrd.ord + 1)

    # get Children of the answers that were answered for the last note
    lastNote = self.col.get_note(lastNoteLst[0])
    lstNtMt = json.loads(lastNote.fields[list(X_FLDS.keys()).index('mt')])
    lstCrds = list(map(lambda o: dict(ord=o), self.col.db.list(
        "select ord from cards where id in " + ids2str(lastNoteLst[1]))))
    nextNotes = self.getCardData(dueAnswers=dueAnswers, cards=lstCrds,
                                 ntMt=lstNtMt)

    # if any of these children have due answers, return their first due answer
    if len(nextNotes) > 0:
        nextNote = self.getUrgentNote(nextNotes, nidList)
        return self.getNextAnswer(nextNote, 0)

    # check whether children of these children have due answers
    answerFurtherDown = self.getAnswerFurtherDown(notes=nextNotes,
                                                  dueAnswers=dueAnswers,
                                                  nidList=nidList)
    if answerFurtherDown:
        return answerFurtherDown

    # get Children of answers that were not answered in the last note
    skippedCards = list(map(lambda o: dict(ord=o), self.col.db.list(
        "select ord from cards where nid = ? and id not in " + ids2str(
            lastNoteLst[1]), lastNoteLst[0])))
    nextNotes = self.getCardData(dueAnswers=dueAnswers, cards=skippedCards,
                                 ntMt=lstNtMt)
    # if any of these children have due answers, return their first due answer
    if len(nextNotes) > 0:
        nextNote = self.getUrgentNote(nextNotes, nidList)
        return self.getNextAnswer(nextNote, 0)

    # check whether children of these children have due answers
    answerFurtherDown = self.getAnswerFurtherDown(notes=nextNotes,
                                                  dueAnswers=dueAnswers,
                                                  nidList=nidList)
    if answerFurtherDown:
        return answerFurtherDown

    # if no children nor children of children are due, check whether a sibling
    # question is due and return it if necessary
    dueSiblingNotes = []
    siblings = []
    for nId in getNotesFromQIds(qIds=lstNtMt['siblings'], col=self.col):
        siblings.append(dict(nid=nId))
        siblings[-1]['dueCards'] = getDueAnswersToNote(nId=nId,
                                                       dueAnswers=dueAnswers,
                                                       col=self.col)
        if len(siblings[-1]['dueCards']) > 0:
            dueSiblingNotes.append(
                dict(dueCards=siblings[-1]['dueCards'], nId=nId))

    if len(dueSiblingNotes) > 0:
        nextNote = self.getUrgentNote(dueSiblingNotes, nidList)
        return self.getNextAnswer(nid=nextNote, aId=0)

    # if no siblings are due, check whether connections are due and return them
    # if necessary
    connections, dueConnectionNotes = self.getDueConnectionNotes(
        dueAnswers=dueAnswers, meta=lstNtMt)

    if len(dueConnectionNotes) > 0:
        nextNote = self.getUrgentNote(dueConnectionNotes, nidList)
        return self.getNextAnswer(nid=nextNote, aId=0)

    nxtLvlConnections = []
    dueNxtLvlConnectionNotes = []
    # Also check whether connections of connections have due questions
    for connection in connections:
        connection['note'] = self.col.getNote(connection['nid'])
        connection['meta'] = json.loads(
            connection['note'].fields[list(X_FLDS.keys()).index('mt')])
        nLCons, dNLConNts = self.getDueConnectionNotes(
            dueAnswers=dueAnswers, meta=connection['meta'])
        nxtLvlConnections.extend(nLCons)
        dueNxtLvlConnectionNotes.extend(dNLConNts)
    if len(dueNxtLvlConnectionNotes) > 0:
        nextNote = self.getUrgentNote(dueNxtLvlConnectionNotes, nidList)
        return self.getNextAnswer(nid=nextNote, aId=0)

    # If the last note did not have any further questions, remove the last Item
    # from the history and search again
    del learnHistory[-1]
    return self.getNextSMRCard(learnHistory)


scheduler.v2.Scheduler.getNextSMRCard = getNextSMRCard


def getDueConnectionNotes(self, dueAnswers, meta):
    dueConnectionNotes = []
    connections = []
    for nId in getNotesFromQIds(qIds=meta['connections'], col=self.col):
        connections.append(dict(nid=nId))
        connections[-1]['dueCards'] = getDueAnswersToNote(nId=nId,
                                                          dueAnswers=dueAnswers,
                                                          col=self.col)
        if len(connections[-1]['dueCards']) > 0:
            dueConnectionNotes.append(
                dict(dueCards=connections[-1]['dueCards'], nId=nId))
    return connections, dueConnectionNotes


scheduler.v2.Scheduler.getDueConnectionNotes = getDueConnectionNotes


def getUrgentNote(self, nextNotes, nidList):
    # study notes in lrnQueue frist
    noteCandidates = self.col.db.list(
        "select id from notes where id in %s and id in %s" % (ids2str(
            nidList['lrn']), ids2str(map(lambda n: n['nId'], nextNotes))))
    if len(noteCandidates) == 0:
        noteCandidates = self.col.db.list(
            "select id from notes where id in %s and id in %s" % (ids2str(
                nidList['rev']), ids2str(
                map(lambda n: n['nId'], nextNotes))))
    if len(noteCandidates) == 0:
        noteCandidates = self.col.db.list(
            "select id from notes where id in %s and id in %s" % (ids2str(
                nidList['new']), ids2str(
                map(lambda n: n['nId'], nextNotes))))
    nextNote = random.choice(noteCandidates)
    return nextNote


scheduler.v2.Scheduler.getUrgentNote = getUrgentNote


def getCardData(self, dueAnswers, cards, ntMt):
    nextNotes = []
    for crd in cards:
        crd['children'] = []
        for qId in ntMt['answers'][crd['ord']]['children']:
            nId = getNotesFromQIds(qIds=[qId], col=self.col)[0]
            dueCards = getDueAnswersToNote(nId=nId, dueAnswers=dueAnswers,
                                           col=self.col)
            if len(dueCards) > 0:
                nextNotes.append(dict(dueCards=dueCards, nId=nId))
            crd['children'].append(dict(qId=qId, nId=nId, dueCards=dueCards))
    return nextNotes


scheduler.v2.Scheduler.getCardData = getCardData


def getNextAnswer(self, nid, aId):
    dueAnswers = [t[1] for t in self._lrnQueue] + self._revQueue + self._newQueue
    dueAw2Note = list(self.col.db.execute(
        """select id, ord from cards where nid = ? and id in """ + ids2str(
            dueAnswers), nid))
    awOrds = list(map(lambda t: t[1], dueAw2Note))
    nextOrd = min(filter(lambda o: o >= aId, awOrds))
    answerId = dueAw2Note[awOrds.index(nextOrd)][0]

    return self.col.get_card(answerId)


scheduler.v2.Scheduler.getNextAnswer = getNextAnswer


def getAnswerFurtherDown(self, notes, dueAnswers, nidList):
    urgntNxtLvlNotes = []
    allNxtLvlNids = []
    for nxtNote in notes:
        nxtNote['note'] = self.col.getNote(nxtNote['nId'])
        nxtNote['meta'] = json.loads(
            nxtNote['note'].fields[list(X_FLDS.keys()).index('mt')])
        nxtNote['cards'] = list(map(lambda o: dict(ord=o), self.col.db.list(
            "select ord from cards where nid = ?", nxtNote['nId'])))
        urgntNxtLvlNotes.extend(
            self.getCardData(dueAnswers=dueAnswers, cards=nxtNote['cards'],
                             ntMt=nxtNote['meta']))
        for card in nxtNote['cards']:
            for child in card['children']:
                allNxtLvlNids.append(dict(nId=child['nId']))
    if len(urgntNxtLvlNotes) > 0:
        nextNote = self.getUrgentNote(urgntNxtLvlNotes, nidList)
        return self.getNextAnswer(nextNote, 0)
    if len(allNxtLvlNids) > 0:
        return self.getAnswerFurtherDown(notes=allNxtLvlNids,
                                         dueAnswers=dueAnswers, nidList=nidList)
    return None


scheduler.v2.Scheduler.getAnswerFurtherDown = getAnswerFurtherDown
