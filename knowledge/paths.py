import pathlib

from knowledge import config


PLUGIN_ROOT_DIR = pathlib.Path(__file__).absolute().parent.parent

# Internal data structure
DATA_DIR = pathlib.Path(config.DATA_FOLDER)
CACHE_DIR = DATA_DIR / 'cache'
MEDIA_DIR = DATA_DIR / 'media'
OCCLUSIONS_DIR = DATA_DIR / 'occlusions'

BIBLIOGRAPHY_PATH = DATA_DIR / 'sources.bib'
