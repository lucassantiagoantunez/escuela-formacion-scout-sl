import re
from urllib.parse import parse_qs, urlsplit

import nh3


def limpiar_html(value):
    return nh3.clean(value or '',
        tags={'p', 'br', 'h2', 'h3', 'h4', 'strong', 'em', 'u', 's', 'sub', 'sup', 'span',
              'ul', 'ol', 'li', 'blockquote', 'a', 'hr', 'table', 'thead', 'tbody', 'tfoot',
              'tr', 'td', 'th', 'figure', 'figcaption'},
        attributes={'a': {'href', 'title'}, 'td': {'colspan', 'rowspan', 'style'},
                    'th': {'colspan', 'rowspan', 'style'}, '*': {'style'}, 'ol': {'start'}},
        url_schemes={'https', 'http', 'mailto'},
        allowed_classes={'figure': {'table'}},
        filter_style_properties={'color', 'background-color', 'text-align', 'font-size',
                                 'font-weight', 'font-style', 'text-decoration', 'border',
                                 'border-width', 'border-color', 'border-style', 'padding', 'width'})


def youtube_embed(value):
    try:
        url = urlsplit(value)
        if url.scheme != 'https' or url.username or url.password or url.port not in (None, 443):
            return ''
        parts = url.path.strip('/').split('/')
        video_id = ''
        if url.hostname == 'youtu.be' and len(parts) == 1:
            video_id = parts[0]
        elif url.hostname in {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'www.youtube-nocookie.com'}:
            if url.path == '/watch':
                video_id = parse_qs(url.query).get('v', [''])[0]
            elif len(parts) == 2 and parts[0] in {'embed', 'shorts', 'live'}:
                video_id = parts[1]
        if re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
            return f'https://www.youtube-nocookie.com/embed/{video_id}?rel=0'
    except ValueError:
        pass
    return ''
