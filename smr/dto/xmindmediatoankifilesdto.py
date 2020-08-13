import dataclasses as dc

from smr.dto.entitydto import EntityDto


@dc.dataclass
class XmindMediaToAnkiFilesDto(EntityDto):
    """
    Data transfer object representing an entity from the xmind_media_to_anki_files relation in the smr world
    """
    xmind_uri: str = ""
    anki_file_name: str = ""
