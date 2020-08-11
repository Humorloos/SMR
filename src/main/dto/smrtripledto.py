import dataclasses as dc
from typing import Optional

from main.dto.entitydto import EntityDto


@dc.dataclass
class SmrTripleDto(EntityDto):
    """
    Data transfer object representing an entity from the smr_triples relation in the smr world
    """
    parent_node_id: str = ""
    edge_id: str = ""
    child_node_id: str = ""
    card_id: Optional[int] = None
