" Check VIM version
if version < 704
  echoerr "Knowledge requires at least Vim 7.4. Please upgrade your environment."
  finish
endif

" Check presence of the python support
if ! has("python3")
  echoerr "Knowledge requires Vim compiled with the Python3 support."
  finish
endif

" Disable knowledge if knowledge_disable variable set
if exists("g:knowledge_disable")
  finish
endif

" Determine the plugin path
let s:knowledge_plugin_path = escape(expand('<sfile>:p:h:h'), '\')

" Determine if this is a knowledge file
let s:extension = expand('%:e')
if exists("g:knowledge_extension") && s:extension != g:knowledge_extension
    finish
endif

" Run the measure parts first, if desired
if exists("g:knowledge_measure_coverage")
  execute 'py3file ' . s:knowledge_plugin_path . '/knowledge/testcoverage.py'
endif

" Execute the main body of taskwiki source
execute 'py3file ' . s:knowledge_plugin_path . '/knowledge/main.py'

augroup knowledge
    autocmd!
    " Create new notes in Anki when saved
    execute "autocmd BufWrite *.".expand('%:e')." KnowledgeBufferSave"

    " Autoclose when opening
    if exists('g:knowledge_autoclose_questions')
        execute "autocmd BufWinEnter,SessionLoadPost *.".expand('%:e')." KnowledgeCloseQuestions"
    endif
augroup END

" Global update commands
command! KnowledgeBufferSave :py3 create_notes()
command! KnowledgeCloseQuestions :py3 close_questions()
command! KnowledgePasteImage :py3 paste_image()
command! KnowledgeNoteInfo :py3 note_info()
command! KnowledgeDiag :py3 diagnose()
command! KnowledgeExportPDF :py3 convert_to_pdf()
command! KnowledgeExportPDFPlain :py3 convert_to_pdf(interactive=False)
command! KnowledgeExportPDFInteractive :py3 convert_to_pdf(interactive=True)

" Leader-related mappings.
nmap <silent><buffer> <Leader>kp :KnowledgePasteImage<CR>
nmap <silent><buffer> <Leader>ki :KnowledgeNoteInfo<CR>
nmap <silent><buffer> <Leader>ke :KnowledgeExportPDF<CR>
