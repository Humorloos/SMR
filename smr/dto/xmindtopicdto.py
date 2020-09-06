import dataclasses as dc
from typing import Optional

from smr.dto.entitydto import EntityDto
from smr.dto.topiccontentdto import TopicContentDto


@dc.dataclass
class XmindTopicDto(EntityDto):
    """
    Data transfer object representing a topic (node or edge) from the xmind_nodes or xmind_edges relation in the smr
    world
    """
    node_id: str = ""
    sheet_id: str = ""
    title: str = ""
    image: Optional[str] = None
    link: Optional[str] = None
    order_number: Optional[int] = None

    @property
    def content(self) -> TopicContentDto:
        return TopicContentDto(image=self.image, media=self.link, title=self.title)

    @content.setter
    def content(self, value: TopicContentDto):
        self.image = value.image
        self.title = value.title
        self.link = value.media
