import dataclasses as dc
from typing import Optional

from smr.dto.entitydto import EntityDto


@dc.dataclass
class XmindSheetDto(EntityDto):
    """
    Data transfer object representing an entity from the xmind_sheets relation in the smr world
    """
    sheet_id: str = ""
    path: str = ""
    last_modified: Optional[int] = None
