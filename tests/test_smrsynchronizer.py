import pytest

from smr.smrsynchronizer import SmrSynchronizer


@pytest.mark.skip
def test_smr_synchronizer(patch_aqt_mw_empty_smr_world):
    cut = SmrSynchronizer()
