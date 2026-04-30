from .bienici import BienIciSource
# from .seloger_playwright import SeLogerPlaywrightSource
from .bienicifrance import BienIciFranceSource

SOURCES_ACTIVES = [
    BienIciSource(),
    BienIciFranceSource()
]
