# Character Sheet: privacy and threat model

This guide covers the public standalone app and its reusable setup routes; installation-specific connections may differ.

This describes reusable Character Sheet routes, not a promise that every installation has the same integrations. Setup answers prepare instructions only. They do not connect accounts, move records, grant permissions or change approval settings. Human setup trials are still pending.

## What needs protecting

Your sheet, Journal, history, chat transcripts, exports, credentials and backups may describe you and other people. Protect their confidentiality, preserve accurate records, and keep a recoverable copy. A compact AI context is still personal data. The HTML is reusable code, but a saved rendered page may contain personal text. Never distribute a saved personal page as a blank template.

The main threats are a lost or unlocked device, someone using your browser profile, malicious extensions or page scripts, stolen account credentials, excessive agent permissions, accidental publication, stale/conflicting updates, invented AI claims, and deletion or storage failure. CS does not defend a device already controlled by an attacker. A trusted AI can still make mistakes.

## Browser storage

The downloaded standalone app normally stores its working sheet in this browser profile. The HTML file itself does not contain a durable backup of your entries. Clearing site data, private browsing, changing browser/profile or moving the HTML can lose access to the sheet. Keep the file in one place, use a normal private profile, make a small test entry and reload before relying on persistence. Export complete recovery data to a separate private location.

Scripts in the same origin and extensions with sufficient access can read browser storage. Local-file storage behaviour is browser-dependent and not guaranteed; changing browser is not a security guarantee. A dedicated loopback origin can make the storage location more predictable, but other code served at that same origin shares its access boundary. See [MDN localStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage) and [OWASP browser storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html#local-storage).

## External chat

Ordinary free text chat needs no API key, folder access or companion. Give your AI the stable instructions once, and selected fresh context when needed. Only the files or text you send through that route are deliberately shared by CS; the AI service may also use its own account memory, connectors or earlier uploads. Check those separately.

An export attached to a chat or Project is a reference copy, not a live writable sheet. Proposed JSON becomes a sheet change only when you use Import. Review its meaning and fields before Apply; current Import validates the patch and shows change feedback and Undo after application, rather than guaranteeing a complete pre-apply diff. Small patches with stable IDs preserve unmentioned records; a valid patch can still contain a false claim. Refresh after outside changes, a new chat, or lost context. Keep personal evidence separate from AI inference.

The provider can process plaintext you send. Chats, attachments, Project files, downloads, clipboard managers and device backups can hold additional copies. Deleting one copy or disabling training does not necessarily delete the others. See the [AI privacy guide](ai-privacy-guide.md#cloud-services).

## In-app chat

Chat supports a local model endpoint and selected cloud APIs. It sends messages plus sheet context assembled by the app, which can include substantially more than your latest sentence. Inspect the context before sensitive use; a compact external export is not a guarantee that in-app requests have the same bounds. Chat sessions may also be kept in your sheet.

A genuinely local model avoids cloud inference; its downloads need network access and disk space, and larger models/context need more memory and time. A local endpoint can still proxy a cloud model. The app's local/cloud model classification is not a network audit. Check the model and endpoint, disable cloud features when desired, and avoid exposing the service beyond loopback. Restrict allowed web origins; a wildcard lets other sites reach a local service when browser rules permit. Allowing the file origin `null` is broader than a single HTML file. See [Ollama FAQ](https://docs.ollama.com/faq).

A cloud API receives plaintext context and may bill usage independently from your chat subscription. Keys stored for in-app use are available to the authorised app while unlocked; this browser-client design cannot conceal them from a compromised page or device. The app requires active password protection before storing a cloud key. Keep keys out of exports and shared code, restrict provider permissions/budget where available, and revoke exposed keys in the provider account. See the [AI privacy guide](ai-privacy-guide.md#in-app-setup).

## Encryption

Keep storage location and encryption separate. Device disk encryption and provider encryption in transit/at rest help protect their respective systems; they do not mean that CS encrypts your records before the provider receives them. Drive describes its own [encryption and privacy controls](https://support.google.com/drive/answer/10375054).

The current source uses AES-256-GCM and versioned PBKDF2-SHA-256 with 600,000 iterations for new encryption of its collected browser bundle, local protected recovery and encrypted backup. Unversioned older ciphertext remains readable with its original 200,000-iteration derivation and password. This describes the updated source and installations using it; older downloaded, exported or deployed copies keep their original protection and behaviour until updated. No password or live storage source is changed automatically.

Unlock passwords are held in memory and cleared on Lock or reload. Reload requires password re-entry; an installation using Drive can use Settings → Password Protection → Unlock for backups and recovery without replacing its current Drive profile. Saved provider keys and GitHub tokens are retained in the encrypted browser bundle and used from memory while unlocked. Ordinary persisted settings omit those secrets. An older plaintext credential cache is preserved until password re-entry verifies an encrypted copy before removing the plaintext credentials; loading the page alone is not proof that this migration has completed.

This browser protection is limited, not a claim that every record or copy is encrypted. The bundle collects sheet state, selected history/configuration keys and dynamic regular-quest keys. Unlock still restores some non-credential working data as readable browser keys; preferences and some sidecars remain outside the collected/cleared set. Local reset/restore checkpoints and record-deletion recovery use encryption when browser password protection is set, and need the appropriate password for recovery. Same-origin code or a compromised profile can defeat this boundary, including during an unlocked session. See [OWASP cryptographic storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html).

In an installation using canonical Drive, the save path bypasses browser encryption: setting a browser password does not encrypt that Drive document. Likewise, encrypting a GitHub backup does not encrypt your live browser source, exports, transcripts or older revisions. An authorised AI must see plaintext to reason about it. Encryption does not protect against that AI, an unlocked app, malicious code, false updates, metadata disclosure or copies made earlier.

Client-side encrypted canonical local-file/Drive storage is Planned. The companion contains only a fictional synthetic encrypted-object proof using AES-GCM, scrypt, version checks and optional macOS Keychain convenience. It is not connected to real Drive, live browser storage or background writers. There is no supported switch that turns an existing live store into this encrypted mode. A future migration needs complete coverage of readers/writers, key recovery, conflict checks, old plaintext copies and rehearsed rollback. Do not put real records into the proof. Losing all unlocking/recovery secrets can make ciphertext unrecoverable.

## One source of truth

Browser, local file and user-owned Drive are separate choices. The general standalone download uses browser storage. The companion reads one selected local JSON file; that file is not connected to the browser sheet. Revision 0 with an empty object means its test file is uninitialised, not that your browser sheet is empty.

A separately configured installation may have a working Drive source through Sync, with a complete-document read, conflict checks, confirmed saves and an offline browser cache. The general standalone build does not provide this connection; user-owned Drive setup remains Planned there. Keep an already configured installation's existing source. Questionnaire choices never switch it. Drive account access, sharing, synced folders and revision history are additional plaintext access/copy boundaries unless application encryption is actually implemented.

Before changing source: pause every writer; export full recovery; keep an independent copy; use only a tested migration mechanism; read back the entire destination; compare preserved records/history/configuration; explicitly choose one authority; test restart, another edit, a conflict and recovery. Do not import an old snapshot over newer work or call three unsynchronised stores one live sheet. No general automatic migration is provided here.

## Approval and scope

Reviewed changes are the recommended starting policy. External chat proposes; the person controls Import. In-app Chat settings offer Manual and Review changes before saving. Existing After every reply/Every N replies with review off can apply broad inferred updates while that conversation runs. They do not enforce a per-source/per-field allowlist. This is an advanced risk, not the proposed scoped automation service.

Allowed factual updates mean copying a named observation, such as a dated step count, only into explicitly allowed fields. Autonomous inference means allowing an AI to interpret selected evidence into specified fields. Both need attributable changes, conflict handling, Undo or recoverable backups, a pause mechanism and visible correction. Generic source/field enforcement and an unattended just-chat service are Planned. An existing privately configured integration may have its own rules; the planner neither audits nor changes them. Activity counts never prove feelings or justify invented Health/Mana readings.

CS UI preferences cannot grant or revoke an external agent's operating-system folder permissions, provider connectors or MCP tools, nor police a tool that ignores instructions. Limit access in the agent/client and OS, use test files first, and remove permissions there when pausing. Stop in-app requests/close the tab to stop its local process; it is not a persistent background service. An outside agent needs its own running service and can continue independently, so pause that service too. Turning off a planner option has no such effect.

The companion limits its tools to one selected file, checks revision, serialises writers, keeps previous revisions and offers undo. Chat approval is supplied by the AI client/tool caller, not an independent human-authentication boundary. An agent able to edit the file directly can bypass those tools. Sibling backups share the same folder/device risk. Test only until the browser round trip is implemented. See the [companion guide](companion/README.md).

## Backup and recovery

Data → Export contains two distinct documents. data.json is compact AI context, read-only and incomplete for recovery. Download recovery file produces migration.json with sheet records, history and supported configuration/extension state, excluding credentials and disposable caches. Older full-state data.json exports may remain importable; the filename alone does not prove a backup is complete. Store backups privately, with dates and separate copies. Exported JSON is plaintext even when the app has a password.

Undo from the change notice is a short-term correction mechanism, not durable version history or disaster recovery. Use it promptly after a bad import and check the result; retain a full backup for earlier recovery. To restore, back up the current sheet first, open Data → Import and choose/paste the complete recovery JSON, review and Apply, then reload and verify records/history and confirmed persistence. Test with synthetic data in a separate profile before depending on this process. There is no invented one-click restore or automatic encryption migration.

Optional encrypted GitHub backup uses the existing Sync controls and a repository you manage. New backups contain recovery data and exclude provider credentials and sync tokens. The current source verifies the exact private destination before upload or restore, reads back a completed upload, and stops on a stale remote version. Re-enter your browser password after reload before encrypted backup or recovery. A complete restore replaces records and history after review and a verified local recovery checkpoint; it does not merge two sheets. Protect the token and password, rehearse a pull/recovery with fictional data, and remember that metadata and older copies remain separate. Never rely solely on same-device exports or the companion's sibling backups. Browser clearing, loss of all keys and account deletion can defeat recovery.

## Hosted exploration and network policy

Hosted copies, including the separately authored hosted blank sheet, are for fictional exploration. Do not enter personal records or credentials there. The hosted blank keeps its own browser namespace for exploration; this is not permission to import personal data, store provider credentials, send AI requests or connect accounts. These personal actions require a downloaded file or an HTTP/HTTPS server on exactly localhost, 127.0.0.1 or ::1. Standalone metadata does not make another web host trusted.

The public package disables Drive sync and plaintext GitHub backup. The shared private-repository verification used by encrypted GitHub backup is retained when plaintext sync is removed. This corrects a source packaging dependency; it is not proof of a completed backup or restore on your device. Keep complete recovery exports and separate private copies, and rehearse with fictional data before relying on this route.

The supported model requests, prompt-cache warm-ups and local model listing reject redirects and suppress referrers. External links also suppress referrers. The app's content policy explicitly restricts objects, base URL changes and form destinations while retaining its existing identity, model and resource destinations. These allowances do not authorise automatic personal transfers.

Compatibility limit: this single-file app retains explicit unsafe-inline for its static and generated event handlers, scripts and dynamic styles. This is not a strict script policy and does not protect a compromised browser, malicious extension or hostile script already running in the page. Meta policy cannot supply a framing-denial response header. Visiting hosted pages still makes ordinary hosting and resource requests.

## Demo and publication

The hosted fictional demo does not load a private browser sheet or persist planner answers or sheet edits. It does not run AI/OAuth, connect accounts or initialise private storage through the planner. You may read every plan before downloading. Download the blank app shell through the demo's download action, open it privately, and verify that it starts blank. Merely visiting a hosted page still involves normal hosting/network requests.

Developer mode is an Experimental, self-managed code/configuration workflow, not a casual data-update switch or implemented permission gate. Keep private recovery and code copies, isolate tests with synthetic records, grant narrow file access, review diffs, test imports/persistence and reverse broken changes. Contributions must contain generic code and fictional fixtures only. No setup selection authorises publication. Public release is a separate human review; exports, transcripts, secrets and personalised HTML must never enter public Git, hosting or contribution attachments.
