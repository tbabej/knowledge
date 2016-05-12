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

execute 'syn match Close /\(\* \)\@<!\[\([^\]@]\|\n\)\+\(\]\| \ze\(@[0-9a-zA-Z]\)\)/'
execute 'syn match CloseRest /\([^\n]\n\)\@<=\([^\]\@]\|\n\)\+\]/'

execute 'syn match CloseBorder containedin=Close,CloseRest contained /\[\|\]/'.s:conceal
execute 'syn match CloseMeta containedin=Close,CloseRest contained /:[^:]\+\ze\]/'.s:conceal
highlight link Close Keyword
highlight link CloseRest Keyword

" Define SRSQuestion region that allows folding of the explicit questions
execute 'syntax region SRSQuestion start=/^\(Q\|How\|Explain\|Define\|List\|Prove\): / end=/\n\ze\n/ transparent fold'
