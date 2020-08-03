# noinspection PyUnresolvedReferences
# noinspection PyUnresolvedReferences
# noinspection PyUnresolvedReferences
from main import sync, exportsync, monkeypatches
from main.config import get_or_create_model, update_smr_version, get_or_create_smr_world
from main.consts import SMR_CONFIG
from ximports.xversion import LooseVersion
from main.xmindimport import XmindImporter

import anki.importing as importing
import aqt.deckbrowser as deckbrowser
from anki.hooks import addHook
from anki.lang import _
from aqt import mw


def on_profile_loaded():
    """
    # If necessary creates smr model and smr world and updates the Addon version after loading the profile
    """
    get_or_create_model()
    mw.smr_world = get_or_create_smr_world()
    current_version = None
    if mw.col.get_config('smr'):
        current_version = LooseVersion(mw.col.get_config('smr')['version'])
    if not mw.col.get_config('smr') or current_version < LooseVersion(
            '0.1.0'):

        update_smr_version()
    elif current_version < LooseVersion(SMR_CONFIG['version']):
        update_smr_version()


# Add-on setup at profile-load time
addHook("profileLoaded", on_profile_loaded)

# Add xmind importer to importers
importing.Importers = importing.Importers + \
                      ((_("Xmind map (*.xmind)"), XmindImporter),)

# Add SMR Sync Button to Deckbrowser
deckbrowser.DeckBrowser.drawLinks.append(["", "sync", "SMR Sync"])
