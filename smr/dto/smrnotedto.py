import dataclasses as dc
from typing import Optional

from smr.dto.entitydto import EntityDto
from smr.dto.xmindnodedto import XmindNodeDto


@dc.dataclass
class SmrNoteDto(EntityDto):
    """
    Data transfer object representing an entity from the smr_notes relation in the smr world
    """
    note_id: Optional[int] = None
    edge_id: str = ""
    last_modified: Optional[int] = None
    edge: XmindNodeDto = None
