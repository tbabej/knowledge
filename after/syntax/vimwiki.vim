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
execute 'syn match FactIdentifier /\v\[[0-9a-zA-Z]{22}\]$/'.s:conceal
highlight link FactIdentifier Comment