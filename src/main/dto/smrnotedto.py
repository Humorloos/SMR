import dataclasses as dc
from typing import Optional

from main.dto.entitydto import EntityDto


@dc.dataclass
class SmrNoteDto(EntityDto):
    """
    Data transfer object representing an entity from the smr_notes relation in the smr world
    """
    note_id: Optional[int] = None
    edge_id: str = ""
    last_modified: Optional[int] = None
