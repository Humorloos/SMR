import dataclasses as dc
from typing import Optional

from smr.dto.entitydto import EntityDto


@dc.dataclass
class XmindNodeDto(EntityDto):
    """
    Data transfer object representing a node (or edge) from the xmind_sheets relation in the smr world
    """
    node_id: str = ""
    sheet_id: str = ""
    title: str = ""
    image: str = ""
    link: str = ""
    ontology_storid: Optional[int] = None
    last_modified: Optional[int] = None
    order_number: Optional[int] = None
