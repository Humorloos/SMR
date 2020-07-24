import dataclasses as dc
from typing import Optional


@dc.dataclass
class NodeContentDTO:
    """
    Data transfer object for storing xmind nodes' content which consists of the title, optional image, and media
    """
    image: Optional[str] = None
    media: Optional[str] = None
    title: str = ""
