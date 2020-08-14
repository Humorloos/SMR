from smr.dto.xmindfiledto import XmindFileDto


def test_xmind_file_dto():
    entity = ('directory', 'name', 123, 123.4, 567)
    # when
    cut = XmindFileDto(*entity)
    # then
    assert cut == XmindFileDto(
        directory='directory', file_name='name', map_last_modified=123, file_last_modified=123.4, deck_id=567)


def test_iter():
    # given
    cut = XmindFileDto(directory='directory', file_name='name', map_last_modified=123, file_last_modified=123.4,
                       deck_id=567)
    # when
    entity = tuple(cut)
    # then
    assert entity == ('directory', 'name', 123, 123.4, 567)
