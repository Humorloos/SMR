import dataclasses as dc
from typing import Optional


@dc.dataclass
class DeckSelectionDialogUserInputsDTO:
    """
    Data transfer object for storing user inputs from the deck selection dialog
    """
    # Whether or not the import is supposed to repair already once imported notes after the xmind node ids have changed,
    #         e.g. due to opening the map in a different program like xmind zen
    repair: bool = False
    deck_id: Optional[int] = None
    deck_name: str = ''
    running: bool = True
