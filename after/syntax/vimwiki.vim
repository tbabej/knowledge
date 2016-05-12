" Disable knowledge if knowledge_disable variable set
if exists("g:knowledge_disable")
  finish
endif

" Detect if conceal feature is available
let s:conceal = exists("+conceallevel") ? ' conceal': ''

" Conceal header definitions
for s:i in range(1,6)
  execute 'syn match WikiNoteHeaderDef containedin=VimwikiHeader'.s:i.' contained /@[^=]*/'.s:conceal
endfor

" Conceal the fact identifiers
execute 'syn match FactIdentifier /\v\@[0-9a-zA-Z]{13,22}$/'.s:conceal
highlight link FactIdentifier Comment

execute 'syn match Close /\(\* \)\@<!\[\([^[\]@]\|\n\)\+\(\]\| \ze\(@[0-9a-zA-Z]\)\)/'
execute 'syn match CloseRest /\([^\n]\n\)\@<=\([^[\]\@]\|\n\)\+\]/'

execute 'syn match CloseBorder containedin=Close,CloseRest contained /\[\|\]/'.s:conceal
execute 'syn match CloseMeta containedin=Close,CloseRest contained /:[^:]\+\ze\]/'.s:conceal
highlight link Close Keyword
highlight link CloseRest Keyword

" Define SRSQuestion region that allows folding of the explicit questions
execute 'syntax region SRSQuestion start=/^\(Q\|How\|Explain\|Define\|List\|Prove\): / end=/\n\ze\n/ transparent fold'

" Set concealed parts as really concealed in normal mode, and with cursor over
setlocal conceallevel=3
setlocal concealcursor=nc

" Configure custom FoldText function
" Altered version of the VimwikiFoldText
setlocal foldmethod=syntax
setlocal viewoptions=folds

function! KnowledgeFoldText()
  let line = getline(v:foldstart)
  let main_text = substitute(line, '^\s*', repeat(' ',indent(v:foldstart)), '')
  let short_text = substitute(main_text, '|[^=]* =', '=', '')
  let short_text = substitute(short_text, '@[^=]* =', '=', '')
  let short_text = substitute(short_text, ' @[A-Za-z0-9]\+', '', '')
  let fold_len = v:foldend - v:foldstart + 1
  let len_text = ' ['.fold_len.'] '
  return short_text.len_text.repeat(' ', 500)
endfunction

setlocal foldtext=KnowledgeFoldText()
