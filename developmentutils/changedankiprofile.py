# import required modules
import os
import shutil

import tests.constants as cts
from conftest import generate_new_file, generate_new_tree
from smr import smrworld


def main():
    try:
        os.unlink(smrworld.SMR_WORLD_PATH)
    except FileNotFoundError:
        pass
    generate_new_file(src=cts.ORIGINAL_SMR_WORLD_WITH_EXAMPLE_MAP_PATH, dst=smrworld.SMR_WORLD_PATH)
    user_directory = os.path.join(os.path.dirname(os.path.dirname(cts.ADDON_PATH)), 'User 1')
    for name in os.listdir(user_directory):
        path = os.path.join(user_directory, name)
        if os.path.isfile(path):
            os.unlink(path)
        else:
            shutil.rmtree(path)
    generate_new_file(src=cts.DEFAULT_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_PATH, dst=os.path.join(
        user_directory, 'collection.anki2'))
    generate_new_tree(src=cts.DEFAULT_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_MEDIA, dst=os.path.join(
        user_directory, 'collection.media'))


# Call the main function
if __name__ == "__main__":
    main()
