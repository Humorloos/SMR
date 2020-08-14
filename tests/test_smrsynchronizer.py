import pytest
from assertpy import assert_that

from anki import Collection
from smr.smrsynchronizer import SmrSynchronizer
from smr.smrworld import SmrWorld
from smr.xnotemanager import XNoteManager


def test_smr_synchronizer(patch_aqt_mw_smr_world_and_col_with_example_map):
    # when
    cut = SmrSynchronizer()
    # then
    assert type(cut.smr_world) == SmrWorld
    assert type(cut.note_manager) == XNoteManager
    assert type(cut.col) == Collection
