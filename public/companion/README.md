# Character Sheet desktop companion

The companion currently gives a desktop AI four narrow local tools for **one selected companion JSON file**: open a page, read the file, save an approved change, and undo. It listens only on `127.0.0.1` and does not send data to a cloud service by itself. **The page is not yet wired to that file.** An edit made in the browser does not reach the companion file, and an AI edit to that file does not appear in the browser. Do not use this route as a live two-way sheet yet. In particular, revision `0` with `{}` means the selected companion file has not been initialised; it does not mean your existing browser or Drive sheet is empty.

The MCPB opens a blank standalone browser copy and carries only its explicitly referenced public paintings. The loopback host checks the current Host, browser Origin and Fetch Metadata before issuing redirects or reading state, blocks frames, and serves only the selected HTML and hash-verified packaged artwork. Its CSP retains inline scripts and handlers for compatibility with the current UI; network destinations remain explicit, and responses use no-referrer and framing restrictions.

Accepted companion-file writes now keep the exact previous revision in a private-permission sibling backup directory, and independent MCP processes take a file lock before a read/modify/write. These backups are plaintext if the companion file is plaintext. They protect against an accidental edit, not loss or compromise of the whole folder, device, or Drive account. Keep a separately located backup and test recovery before relying on this file.

## Fictional encrypted Drive proof

The companion also contains an isolated proof of the future private-storage path. It encrypts the complete Character Sheet document with AES-256-GCM before a synthetic Drive adapter sees it, derives the key from a recovery passphrase with scrypt, and keeps namespace schema, version, and ETag checks. The adapter writes only an authenticated ciphertext envelope and non-secret conflict metadata. It creates no plaintext cache.

This is deliberately not connected to a live Character Sheet, Google Drive account, browser cache, or scheduled jobs. It uses the built-in fictional Avery Example record only.

Create a test object and optionally retain the passphrase in the macOS Login Keychain:

```sh
python3 companion/character-sheet-mcp.py encrypted-proof-init \
  --store "$PWD/fictional-encrypted-drive-object.json" \
  --remember-in-keychain
```

Start the narrow local JSON-lines interface after Mac login:

```sh
python3 companion/character-sheet-mcp.py encrypted-proof-ai \
  --store "$PWD/fictional-encrypted-drive-object.json" \
  --keychain-service org.character-sheet.encrypted-proof
```

The interface accepts only `read` and small JSON-pointer `patch` requests. A patch must carry the version and ETag returned by its preceding read. Ordinary chat-approved edits need no repeated confirmation field. Deletes and more than five operations require `I CONFIRM DELETE OR BULK CHANGE`.

Omit `--keychain-service` to unlock manually with the recovery passphrase. The Keychain entry is convenience, not recovery: the retained passphrase can still unlock the file if the Mac or Keychain entry is lost. Losing both makes the AES-GCM data unrecoverable. Remove the test-only Keychain item with:

```sh
python3 companion/character-sheet-mcp.py encrypted-proof-forget-keychain
```

Before any live migration, four separate pieces still need implementation and review:

1. Adapt the private Drive module, localhost bridge, and every scheduled reader/writer so plaintext exists only in process memory and the current whole-document conflict checks remain intact.
2. Add the matching browser encryption/decryption path for the canonical Drive document. The current browser unlock keeps passwords and non-extractable keys in memory; that browser protection does not encrypt the canonical Drive document.
3. Inventory and handle historical plaintext Drive revisions, local caches, exports, backups, and logs. Encrypting the current object does not erase old plaintext copies.
4. Create and rehearse a named rollback that preserves the pre-migration Drive object, proves decryptability and complete read-back before cutover, and never silently falls back to plaintext.

## Claude Desktop: companion-file route

1. Download `character-sheet-companion.mcpb`.
2. In Claude Desktop, open **Settings → Extensions → Advanced settings → Install Extension** and choose the MCPB.
3. Choose a private `character-sheet-companion.json` file when prompted. Keep it outside public Git and inside a folder you back up.
4. Start a new chat and ask the AI to **read the companion file**. Do not infer that it has read your existing browser or Drive sheet. The bundled page is presently a separate browser copy.

Claude Desktop chat is available on Free and paid plans. A Team or Enterprise administrator can block custom desktop extensions. The companion needs no API key and adds no separate API bill, but Claude usage still follows the limits of your plan. See Anthropic's current [desktop availability](https://support.claude.com/en/articles/10065433-install-claude-desktop) and [MCPB installation guide](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop).

## Codex desktop: companion-file route

Download this repository, open Terminal in its folder, then paste this one command:

```sh
codex mcp add character-sheet -- python3 "$PWD/companion/character-sheet-mcp.py" mcp --sheet "$PWD/character-sheet.html" --state "$PWD/character-sheet-companion.json"
```

Restart Codex, open a local task, and ask it to **read the companion file**. It will report whether the file exists. The app page and companion file are not yet connected, so this command is only for testing the isolated file route.

Codex is included with ChatGPT Plus, Pro, Business, and Enterprise/Edu plans. Free and Go access is currently available for a limited time, with lower usage limits. The local app can use this stdio MCP configuration; ordinary ChatGPT web or mobile chats cannot. No API key is required when you sign in with your ChatGPT plan. See the current [Codex plan guide](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan) and [MCP setup reference](https://developers.openai.com/learn/docs-mcp).

## The approval rule

Ask your AI to read the current sheet, discuss one change, and explain it in plain language. Nothing saves until you approve it in that chat. Deletion or more than five operations requires the stronger confirmation phrase the tool returns. Every accepted save checks the revision, keeps recovery history, and can be undone.

The companion state is **not** currently the browser sheet's data. Data → Export exports the browser copy, not the companion file. Do not put either, their backups, a chat transcript, or MCP settings containing private paths in a public repository.

## If local MCP is unavailable

Use the browser and chat-only route for actual edits today. Download `instructions.md`, share only the relevant parts of a fresh private Data export, ask for one small `_partial` JSON update, review it, then paste it into Data → Import. The standalone HTML does not watch files an AI edits.

This public companion is separate from any private Drive-backed development sheet. It never reads or replaces that private state.
