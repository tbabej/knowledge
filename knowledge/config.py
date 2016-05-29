"""
This module collects all the config variables sourced from vim.
"""

import vim

MEASURE_COVERAGE = vim.vars.get('knowledge_measure_coverage')
SRS_PROVIDER = vim.vars.get('knowledge_srs_provider')
DATA_DIR = vim.vars.get('knowledge_data_dir')

QUESTION_OMITTED_PREFIXES = vim.vars.get(
    'knowledge_omitted_prefixes',
    ('Q:',)
)

QUESTION_PREFIXES = vim.vars.get(
    'knowledge_question_prefixes',
    ('Q:', 'How:', 'Explain:', 'Define:', 'List:', 'Prove:')
)

GLUED_LATEX_COMMANDS = vim.vars.get('knowledge_glued_latex_commands', [])
