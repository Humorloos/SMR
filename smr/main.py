from anki.hooks import addHook
from anki.lang import _
from aqt import deckbrowser
from anki import hooks

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
    mw.reset()

# Add-on setup at profile-load time
addHook("profileLoaded", on_profile_loaded)


def importer_hook(importers):
    importers.append(("Xmind map (*.xmind)", XmindImporter))


# Add xmind importer to importers
hooks.importing_importers.append(importer_hook)
