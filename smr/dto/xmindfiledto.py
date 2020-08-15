import dataclasses as dc
from typing import Optional

from smr.dto.entitydto import EntityDto


@dc.dataclass
class XmindFileDto(EntityDto):
    """
    Data transfer object representing an entity from the xmind_files relation in the smr world
    """
    directory: str = ""
    file_name: str = ""
    map_last_modified: Optional[int] = None
    file_last_modified: Optional[float] = None
    deck_id: Optional[int] = None
