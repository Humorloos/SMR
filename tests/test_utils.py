from smr.utils import replace_embedded_media


def test_replace_embedded_media():
    # when
    replaced_content = replace_embedded_media('some media edge title [sound:somemedia.mp3]')
    # then
    assert replaced_content == 'some media edge title (media)'


def test_replace_embedded_media_with_multiple_media_files():
    # when
    replaced_content = replace_embedded_media(
        'biological psychology<li>investigates: perception</li><li>Pain</li><li>triggered by<br>[sound:环境很好。.mp3]: '
        'nociceptors<br>[sound:环境很好。.mp3]</li><li>can be: chemical</li>')
    # then
    assert replaced_content == 'biological psychology<li>investigates: perception</li><li>Pain</li><li>triggered by (' \
                               'media): nociceptors (media)</li><li>can be: chemical</li>'
