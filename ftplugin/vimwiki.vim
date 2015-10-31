" Check VIM version
if version < 704
  echoerr "Knowledge requires at least Vim 7.4. Please upgrade your environment."
  finish
endif

" Check presence of the python support
if ! has("python")
  echoerr "Knowledge requires Vim compiled with the Python support."
  finish
endif

" Disable taskwiki if taskwiki_disable variable set
if exists("g:knowledge_disable")
  finish
endif

" Determine the plugin path
let s:plugin_path = escape(expand('<sfile>:p:h:h'), '\')

" Execute the main body of taskwiki source
execute 'pyfile ' . s:plugin_path . '/knowledge/knowledge.py'
