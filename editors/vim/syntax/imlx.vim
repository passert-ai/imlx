" Vim syntax file for IMLX: Invariant Markup Language (eXtended)
" Language and reference gate: https://github.com/passert-ai/imlx
if exists("b:current_syntax")
  finish
endif

syn match imlxHeader        /^\(IMLX\|DECLARATIONS\|DECL_VERSION\):.*$/
syn match imlxPagebreak     /^%%PAGEBREAK%%$/
syn match imlxEnvelope      /^::: {custom-style="[A-Za-z0-9_]\+"}$/
syn match imlxEnvelope      /^:::$/
syn match imlxDeclare       /^# \(DECLARE\|TRACE\)\>.*$/
syn match imlxHeading       /^#\{1,3} .*$/ contains=imlxDeclare
syn match imlxBullet        /^\* \(\* \)\?/
syn match imlxTableSep      /^|\( :--- |\)\+$/
syn match imlxTablePipe     / | \||$\|^| / contained
syn keyword imlxOpcode      LOAD SEARCH QUERY SELECT PARSE LABEL EXTRACT CONCAT INSERT APPEND POPULATE FOR_EACH EXECUTE DECLARE SLOT VERIFY CONVERT COMPUTE OUTPUT_PRINT GATE contained
syn match imlxOpcode        /\<IF\/THEN\/ELSE\>/ contained
syn keyword imlxTraceEvent  GATE_L1 GATE_L2 STEP BIND SLOT_OPEN SLOT_FILL GATE_VERDICT HALT contained
syn keyword imlxOutcomeOk   PASS BOUND FILLED SKELETON DONE contained
syn keyword imlxOutcomeFail FAIL contained
syn match imlxRegister      /\<reg_[A-Za-z0-9_]\+\>/ contained
syn match imlxReference     /@[A-Za-z][A-Za-z0-9_]*/ contained
syn match imlxContractKey   /\<\(ground\|type\|blocklist\|THEN\|ELSE\)=/ contained
syn match imlxDigest        /\<[0-9a-f]\{64}\>/ contained
syn region imlxString       start=/"/ end=/"/ contained
syn region imlxTableRow     start=/^| / end=/$/ contains=imlxTablePipe,imlxOpcode,imlxTraceEvent,imlxOutcomeOk,imlxOutcomeFail,imlxRegister,imlxReference,imlxContractKey,imlxDigest,imlxString oneline
syn region imlxMath         start=/\$/ end=/\$/ oneline

hi def link imlxHeader      PreProc
hi def link imlxPagebreak   Special
hi def link imlxEnvelope    Structure
hi def link imlxDeclare     Keyword
hi def link imlxHeading     Title
hi def link imlxBullet      Special
hi def link imlxTableSep    Delimiter
hi def link imlxTablePipe   Delimiter
hi def link imlxOpcode      Statement
hi def link imlxTraceEvent  Type
hi def link imlxOutcomeOk   Constant
hi def link imlxOutcomeFail Error
hi def link imlxRegister    Identifier
hi def link imlxReference   Identifier
hi def link imlxContractKey Label
hi def link imlxDigest      Number
hi def link imlxString      String
hi def link imlxMath        Special

let b:current_syntax = "imlx"
