import pytest

from anki import Collection
from smr.smrsynchronizer import SmrSynchronizer
from smr.smrworld import SmrWorld
from smr.xnotemanager import XNoteManager


@pytest.fixture
def smr_synchronizer_no_changes(patch_aqt_mw_smr_world_and_col_with_example_map):
    return SmrSynchronizer()


def test_smr_synchronizer(smr_synchronizer_no_changes):
    # when
    cut = smr_synchronizer_no_changes
    # then
    assert type(cut.smr_world) == SmrWorld
    assert type(cut.note_manager) == XNoteManager
    assert type(cut.col) == Collection


def test_synchronize(smr_synchronizer_no_changes):
    # given
    cut = smr_synchronizer_no_changes
    # when
    cut.synchronize()
    # then
    assert False
