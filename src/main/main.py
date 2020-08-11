import anki.importing as importing
import aqt.deckbrowser as deckbrowser
import main.consts as cts
from anki.hooks import addHook
from anki.lang import _
from aqt import mw
from aqt.utils import showCritical, tooltip
from main.collection2smrworldmigrator import Collection2SmrWorldMigrator
from main.config import create_or_update_model, update_smr_version, get_or_create_smr_world
from main.smrworldmigrationdialog import SmrWorldMigrationDialog
from main.xmindimport import XmindImporter
from ximports.xversion import LooseVersion


def on_profile_loaded():
    """
    # If necessary creates smr model and smr world and updates the Addon version after loading the profile
    """
    mw.smr_world = get_or_create_smr_world()
    if mw.col:
        current_version = LooseVersion('0.0.0')
        if mw.col.get_config('smr'):
            current_version = LooseVersion(mw.col.get_config('smr')['version'])
        # if the version is below 0.1.0, show smr world migration dialog and migrate existing notes if the dialog is
        # accepted. Only update the version after the migration
        if current_version < cts.SMR_WORLD_VERSION:
            migration_dialog = SmrWorldMigrationDialog(mw)
            dialog_status = migration_dialog.exec()
            if dialog_status == int(migration_dialog.AcceptRole):
                migrator = Collection2SmrWorldMigrator()
                try:
                    migrator.migrate_collection_2_smr_world()
                    update_smr_version()
                    current_version = LooseVersion(cts.SMR_CONFIG['version'])
                    create_or_update_model()
                    tooltip('Successfully updated to stepwise map retrieval version 0.1.0.')
                except FileNotFoundError as error_message:
                    showCritical(str(error_message) +
                                 "You need to either move the missing file to the mentioned path and update all notes "
                                 "by importing it again or remove all notes belonging to the missing file. To try "
                                 "updating the addon again, please restart Anki.")
        elif current_version < LooseVersion(cts.SMR_CONFIG['version']):
            # Update version
            create_or_update_model()
            update_smr_version()
        # Add SMR Sync Button to Deckbrowser if the addon was already updated to version 0.1.0
        if current_version >= cts.SMR_WORLD_VERSION:
            deckbrowser.DeckBrowser.drawLinks.append(["", "sync", "SMR Sync"])
            mw.reset(guiOnly=True)


# Add-on setup at profile-load time
addHook("profileLoaded", on_profile_loaded)

# Add xmind importer to importers
importing.Importers = importing.Importers + \
                      ((_("Xmind map (*.xmind)"), XmindImporter),)
