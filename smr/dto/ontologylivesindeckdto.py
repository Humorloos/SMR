import dataclasses as dc
from typing import Optional

from smr.dto.entitydto import EntityDto


@dc.dataclass
class OntologyLivesInDeckDto(EntityDto):
    """
    Data transfer object representing an entry for an ontology belonging to a deck from the ontology_lives_in_deck
    relation in the smr world
    """
    deck_id: Optional[int] = None
    ontology: Optional[int] = None
