import dataclasses as dc
from typing import Optional


@dc.dataclass
class TopicContentDto:
    """
    Data transfer object for storing xmind nodes' content which consists of the title, optional image, and media
    """
    image: Optional[str] = None
    media: Optional[str] = None
    title: str = ""

    def is_empty(self):
        return not (self.image or self.media or self.title)

    def to_string(self) -> str:
        content_string = self.title
        if self.image:
            if content_string != '':
                content_string += ' '
            content_string += '(image)'
        if self.media:
            if content_string != '':
                content_string += ''
            content_string += '(media)'
        return content_string
