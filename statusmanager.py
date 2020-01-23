import json
import os

from .consts import ADDON_PATH


class StatusManager:
    def __init__(self, status_file=None):
        if status_file:
            self.status_file = status_file
        else:
            self.status_file = os.path.join(
                ADDON_PATH, 'user_files', 'status.json')
        try:
            self.status = json.loads(self.status_file)
        except json.decoder.JSONDecodeError:
            self.status = []

    def add_new(self, status):
        self.status.append(status)

    def save(self):
        with open(self.status_file, 'w') as status_file:
            json.dump(self.status, status_file)