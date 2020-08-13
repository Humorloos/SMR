from smr.dto.xmindfiledto import XmindFileDto


def test_xmind_file_dto():
    entity = ('path', 123, 123.4, 567)
    # when
    cut = XmindFileDto(*entity)
    # then
    assert cut == XmindFileDto('path', 123, 123.4, 567)


def test_iter():
    # given
    cut = XmindFileDto('path', 123, 123.4, 567)
    # when
    entity = tuple(cut)
    # then
    assert entity == ('path', 123, 123.4, 567)
