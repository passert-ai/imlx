# Editor support for IMLX

One TextMate grammar is the master asset (`vscode-imlx/syntaxes/
imlx.tmLanguage.json`); the other files derive from the same token
inventory: the 21 opcodes, trace events and outcomes, header lines,
envelopes, bullets, math fences, page breaks, registers, and
`@references`, all per SPEC v0.1.

## Visual Studio Code (and Cursor, VSCodium, Windsurf)

From `editors/vscode-imlx/`:

    npm install -g @vscode/vsce
    vsce package

This produces `imlx-0.1.0.vsix`. Install locally with
`code --install-extension imlx-0.1.0.vsix`, or publish:

- VS Code Marketplace: `vsce publish` (requires a publisher account
  matching the `publisher` field in package.json)
- Open VSX (used by most VS Code forks): `npx ovsx publish` (requires an
  Open VSX token)

## JetBrains IDEs

Settings > Editor > TextMate Bundles > add the `vscode-imlx` directory.
The bundled grammar applies to `.imlx` files immediately.

## Notepad++

Language > User Defined Language > Define your language... > Import... >
select `notepad-plus-plus/imlx-udl.xml`. Files with the `.imlx`
extension associate automatically.

## Vim / Neovim

Copy `vim/syntax/imlx.vim` and `vim/ftdetect/imlx.vim` into
`~/.vim/syntax/` and `~/.vim/ftdetect/` (Neovim:
`~/.config/nvim/syntax/` and `~/.config/nvim/ftdetect/`), or point your
plugin manager at this directory.

## Prism.js (websites and blogs)

Load `prism/prism-imlx.js` after `prism.js`, then:

    <pre><code class="language-imlx">IMLX: 0.1
    ...</code></pre>
