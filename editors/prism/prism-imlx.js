// Prism.js language definition for IMLX: Invariant Markup Language (eXtended)
// https://github.com/passert-ai/imlx
// Usage: load after prism.js, then <pre><code class="language-imlx">
(function (Prism) {
  Prism.languages.imlx = {
    'header': {
      pattern: /^(?:IMLX|DECLARATIONS|DECL_VERSION):.*$/m,
      inside: {
        'keyword': /^(?:IMLX|DECLARATIONS|DECL_VERSION)/,
        'constant': /\bINLINE\b/,
        'string': /[A-Za-z0-9._-]+\.imlx/,
        'number': /\b[\d.]+\b/,
        'punctuation': /[:;]/
      }
    },
    'pagebreak': { pattern: /^%%PAGEBREAK%%$/m, alias: 'important' },
    'envelope': {
      pattern: /^::: \{custom-style="[A-Za-z0-9_]+"\}$|^:::$/m,
      inside: {
        'class-name': /(?<=")[A-Za-z0-9_]+(?=")/,
        'attr-name': /custom-style/,
        'punctuation': /[:{}="]+/
      }
    },
    'declare-heading': {
      pattern: /^# (?:DECLARE (?:TYPE|PROCEDURE|CONVERTER|REGISTER|SYMBOL|POLICY)|TRACE .+)$/m,
      inside: { 'keyword': /DECLARE|TRACE/, 'class-name': /TYPE|PROCEDURE|CONVERTER|REGISTER|SYMBOL|POLICY/, 'punctuation': /^#/ }
    },
    'heading': { pattern: /^#{1,3} .+$/m, alias: 'title', inside: { 'punctuation': /^#{1,3}/ } },
    'table-row': {
      pattern: /^\|.*\|$/m,
      inside: {
        'opcode': {
          pattern: /\b(?:LOAD|SEARCH|QUERY|SELECT|PARSE|LABEL|EXTRACT|CONCAT|INSERT|APPEND|POPULATE|FOR_EACH|IF\/THEN\/ELSE|EXECUTE|DECLARE|SLOT|VERIFY|CONVERT|COMPUTE|OUTPUT_PRINT|GATE)\b/,
          alias: 'keyword'
        },
        'trace-event': {
          pattern: /\b(?:GATE_L1|GATE_L2|STEP|BIND|SLOT_OPEN|SLOT_FILL|GATE_VERDICT|HALT)\b/,
          alias: 'builtin'
        },
        'outcome-fail': { pattern: /\bFAIL\b/, alias: 'deleted' },
        'outcome': { pattern: /\b(?:PASS|BOUND|FILLED|SKELETON|DONE)\b/, alias: 'inserted' },
        'register': { pattern: /\breg_[A-Za-z0-9_]+\b/, alias: 'variable' },
        'reference': { pattern: /@[A-Za-z][A-Za-z0-9_]*/, alias: 'symbol' },
        'contract-key': { pattern: /\b(?:ground|type|blocklist|THEN|ELSE)(?==)/, alias: 'attr-name' },
        'digest': { pattern: /\b[0-9a-f]{64}\b/, alias: 'number' },
        'string': /"[^"]*"/,
        'number': /\b\d+(?:\.\d+)*\b/,
        'punctuation': /[|;=]|:---/
      }
    },
    'bullet': { pattern: /^\* (?:\* )?/m, alias: 'punctuation' },
    'math': { pattern: /\$[^$\n]*\$/, alias: 'string' },
    'reference': { pattern: /@[A-Za-z][A-Za-z0-9_]*/, alias: 'symbol' }
  };
}(Prism));
