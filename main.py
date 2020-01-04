from anki.hooks import addHook
from anki.lang import _
import anki.importing as importing

# import aqt.deckbrowser as deckbrowser

from .config import *
from .xmindimport import XmindImporter
# noinspection PyUnresolvedReferences
from . import monkeypatches
# noinspection PyUnresolvedReferences
from . import exportsync


# creates smr model when loading profile if necessary
def on_profile_loaded():
    get_or_create_model()

# Add-on setup at profile-load time
addHook("profileLoaded", on_profile_loaded)

# Add xmind importer to importers
importing.Importers = importing.Importers + \
                      ((_("Xmind map (*.xmind)"), XmindImporter),)

# Add SMR Sync Button to Deckbrowser
# deckbrowser.DeckBrowser.drawLinks.append(["", "sync", "SMR Sync"])
