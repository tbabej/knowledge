"""
This module collects all the config variables sourced from vim.
"""

from knowledge import utils
import vim
import os

MEASURE_COVERAGE = utils.decode_bytes(vim.vars.get('knowledge_measure_coverage'))
SRS_PROVIDER = utils.decode_bytes(vim.vars.get('knowledge_srs_provider'))
DATA_DIR = utils.decode_bytes(vim.vars.get('knowledge_data_dir'))
DB_FILE = utils.decode_bytes(vim.vars.get(
    'knowledge_db_file',
    os.path.expanduser("~/.knowledge.db")
))

QUESTION_OMITTED_PREFIXES = utils.decode_bytes(vim.vars.get(
    'knowledge_omitted_prefixes',
    ('Q:',)
))

QUESTION_PREFIXES = utils.decode_bytes(vim.vars.get(
    'knowledge_question_prefixes',
    ('Q:', 'How:', 'Explain:', 'Define:', 'List:', 'Prove:', 'Derive:')
))

GLUED_LATEX_COMMANDS = utils.decode_bytes(vim.vars.get('knowledge_glued_latex_commands', []))
PDF_UNDERLINE_CLOZE = utils.decode_bytes(vim.vars.get('knowledge_pdf_underline_cloze', 1))
