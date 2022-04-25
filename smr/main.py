from anki.hooks import addHook
from anki.lang import _
import anki.importing as importing
from aqt import deckbrowser

from smr.config import *
from smr.xminder import XmindImporter
# noinspection PyUnresolvedReferences
import smr.monkeypatches
# noinspection PyUnresolvedReferences
import smr.exportsync


# import aqt.deckbrowser as deckbrowser


# creates smr model when loading profile if necessary
def on_profile_loaded():
    get_or_create_model()
    # Add SMR Sync Button to Deckbrowser
    deckbrowser.DeckBrowser.drawLinks.append(["", "sync", "SMR Sync"])
    mw.reset(guiOnly=True)

# Add-on setup at profile-load time
addHook("profileLoaded", on_profile_loaded)

# Add xmind importer to importers
importing.Importers = importing.Importers + ((_("Xmind map (*.xmind)"), XmindImporter),)
