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
            with open(self.status_file) as status_file:
                self.status = json.load(status_file)
        except FileNotFoundError:
            self.status = []

    def add_new(self, status):
        status_index = [self.status.index(s) for s in self.status if
                        s['file'] == status['file']]
        if not status_index:
            self.status.append(status)
        else:
            self.status[status_index[0]] = status

    def save(self):
        with open(self.status_file, 'w') as status_file:
            json.dump(self.status, status_file)