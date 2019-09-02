from anki.hooks import addHook

from config import *


# creates smr model when loading profile if necessary
def on_profile_loaded():
    get_or_create_model()


# Add-on setup at profile-load time
addHook("profileLoaded", on_profile_loaded)
