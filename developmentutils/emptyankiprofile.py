# import required modules
import os
import shutil

import smr.consts as cts
from smr import smrworld


def main():
    try:
        os.unlink(smrworld.SMR_WORLD_PATH)
    except FileNotFoundError:
        pass
    user_directory = os.path.join(os.path.dirname(os.path.dirname(cts.ADDON_PATH)), 'User 1')
    for name in os.listdir(user_directory):
        path = os.path.join(user_directory, name)
        if os.path.isfile(path):
            os.unlink(path)
        else:
            shutil.rmtree(path)


# Call the main function
if __name__ == "__main__":
    main()
