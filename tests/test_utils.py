from smr.utils import replace_embedded_media


def test_replace_embedded_media():
    # when
    replaced_content = replace_embedded_media('some media edge title [sound:somemedia.mp3]')
    # then
    assert replaced_content == 'some media edge title (media)'
