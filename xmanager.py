# class for reading and writing xmind files

import zipfile

from bs4 import BeautifulSoup

class XManager:
    def __init__(self, file):
        xZip = zipfile.ZipFile(file, 'r')
        self.soup = BeautifulSoup(xZip.read('content.xml'),
                                  features='html.parser')
        self.tagList = self.soup('topic')
