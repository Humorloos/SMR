from aqt import deckbrowser, gui_hooks
from anki import hooks

from .config import *
from .xminder import XmindImporter
# noinspection PyUnresolvedReferences
from . import monkeypatches


# import aqt.deckbrowser as deckbrowser


# creates smr model when loading profile if necessary
def on_profile_loaded():
    get_or_create_model()
    # Add SMR Sync Button to Deckbrowser
    deckbrowser.DeckBrowser.drawLinks.append(["", "sync", "SMR Sync"])
    mw.reset()


# Add-on setup at profile-load time
gui_hooks.profile_did_open.append(on_profile_loaded)


def importer_hook(importers):
    importers.append(("Xmind map (*.xmind)", XmindImporter))


# Add xmind importer to importers
hooks.importing_importers.append(importer_hook)
