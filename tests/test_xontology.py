from unittest import TestCase

from XmindImport.xontology import *


class TestClassify(TestCase):
    def test_only_text(self):
        content = {"content": "biological psychology",
                   "media": {"image": None, "media": None}}
        act = classify(content)
        self.fail()

    def test_only_image(self):
        content = {"content": "", "media": {
            "image": "attachments/09r2e442o8lppjfeblf7il2rmd.png",
            "media": None}}
        act = classify(content)
        self.fail()

    def test_only_media(self):
        content = {"content": "", "media": {
            "image": None,
            "media": "attachments/3lv2k1fhghfb9ghfb8depnqvdt.mp3"}}
        act = classify(content)
        self.fail()
