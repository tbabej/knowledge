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
let s:plugin_path = escape(expand('<sfile>:p:h:h'), '\')

" Run the measure parts first, if desired
if exists("g:knowledge_measure_coverage")
  execute 'py3file ' . s:plugin_path . '/knowledge/coverage.py'
endif

" Execute the main body of taskwiki source
execute 'py3file ' . s:plugin_path . '/knowledge/main.py'

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
command! KnowledgeBufferSave :py3 create_notes(update=True)
command! KnowledgeCloseQuestions :py3 close_questions()
