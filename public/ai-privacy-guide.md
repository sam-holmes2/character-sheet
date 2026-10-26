# Character Sheet: AI privacy and setup guide

This guide covers the public standalone app and its reusable setup routes; installation-specific connections may differ.

Provider facts checked 8 October 2026 using the official links below. Availability, limits, pricing and policy can change. Character Sheet is free; an existing Support action offers optional donations. No paid CS backend is needed. Human setup trials remain pending.

## Ordinary external chat

Use the ordinary chat you already have. Free text chat can work within its limits. You do not need an upload, Project, API key, writable attachment, companion or new chat for each update. A subscription is optional; it does not pay for embedded API calls.

1. In your private sheet, open Settings → Setup and external AI guide. Choose **Copy chat starter** for casual conversation or **Copy guided start** for a short optional assessment. Open a new chat in your AI, paste and send. The starter explains Character Sheet and asks about your pace and familiarity with game terms. You can skip questions, change approach or leave the sheet partly empty.
2. Talk about something you want help with. A blank sheet needs no export. If you already have records, open Data → Export, choose only the relevant item/section and **Copy for AI**. Read the text before pasting it into the chat. The AI sees what you share; it does not automatically read other chats or your live sheet.
3. When the AI suggests a specific change, correct it or agree in your own words. Ask for the JSON update, use Copy on its code block, or select everything from the first `{` to the final `}`. Leave out the surrounding explanation and code marks, then paste into Data → Import. JSON is the text format the app reads. Choose Apply, inspect the changed entry and use Undo if wrong. Agreement in chat is not a save. A valid update is not proof that its interpretation is right. Wait for “Sheet updated”. If an error or save warning appears, keep this window and the JSON open, and follow its retry or Undo instruction before reloading, closing or importing another proposal. For rejected JSON, copy the error back to the same AI and ask for a corrected small update. Do not paste secrets or the full recovery file. Undo is in the change notice at the bottom left; check which Import it identifies. Do not apply an already accepted proposal again.
4. Confirm it stays saved after reopening. In an already connected installation, wait for confirmed Sync save before reloading. Tell the AI you accepted the update and continue in the same chat. Refresh relevant context after edits elsewhere or when the chat loses track. Keep dated private recovery backups with Data → Export → Download recovery file; data.json is context, not full recovery.

The starter covers a first conversation and simple quest. For classes, enemies and other updates, copy the full AI guide when asked, plus fresh relevant app detail. Share only sources and definitions the proposed change needs. Some settings and histories still require their native controls; the full guide names that boundary. Do not paste a context export or recovery file as though it were a small update.

## Free-plan limits and continuing later

Message limits vary by provider, account and demand. Large attachments, long histories and repeated full-sheet exports can use more of your allowance. Prefer short replies and a few relevant records. Do not resend the full guide or sheet after every message, and never delete stored history to fit a chat. If you hit a limit, return later or keep using manual controls. For a manual entry, open Quests → Side → + Side Quest, give it a name and Save. The Help walkthrough shows the main controls.

For a new chat, copy the starter, fresh relevant sheet context and an optional short recap from the old chat: your preferences, accepted changes and open questions. Keep proposals you have not imported separate from saved changes. AI memory, Projects, custom instructions and attachments are optional conveniences, not requirements or proof of complete recall. If a pasted message is too long, use a smaller relevant item; ask for a shorter response if the returned update is cut off. Do not apply incomplete JSON.

Research checked 24 October 2026. Official guidance recommends sharing only relevant context; providers do not offer one permanent free-message allowance. See [prompting guidance](https://learn.chatgpt.com/docs/prompting) and [usage best practices](https://support.claude.com/en/articles/9797557-usage-limit-best-practices). These links explain usage, not a required account upgrade.

## Chosen historical sources

Backfilling is optional and only relevant if you want AI help with past records. Start with one selected note, a date range or a short conversation excerpt. Exclude third-party secrets and anything you do not want the provider to retain. Ask for dated facts and exact quotations separately from proposed interpretations; keep gaps explicit. Review a small patch first, and keep a backup before a bulk import. CS does not automatically search archives when you select this plan. Manual users can start with a name and one quest without sharing any archive.

## Cloud services

Check the exact product/account before sending sensitive context: training opt-outs, retention/deletion, human review, connected apps, shared Projects/workspaces and account export controls. Provider encryption at rest does not stop the provider processing your prompts. Chat and API policies differ; no blanket promise covers all services. A work/organisation account may expose content to administrators or violate its data rules, so use an appropriate private account.

- OpenAI: [privacy policy](https://openai.com/policies/privacy-policy), [API data controls](https://developers.openai.com/api/docs/guides/your-data), and [separate ChatGPT/API billing](https://help.openai.com/en/articles/9039756-managing-billing-for-chatgpt-and-the-api-platform). API data is not used for training by default unless opted in; endpoint retention/application state and abuse monitoring still matter. This does not assert the same rule for every consumer chat account.
- Anthropic: [privacy policy](https://www.anthropic.com/privacy) and [API access](https://support.claude.com/en/articles/8114521-how-can-i-access-the-claude-api). Console/API access is a distinct setup from ordinary chat. Check the current commercial or consumer terms for the product you use; do not infer retention from the model name.
- Google: [privacy policy](https://policies.google.com/privacy), [Gemini API billing](https://ai.google.dev/gemini-api/docs/billing) and [API terms](https://ai.google.dev/gemini-api/terms). API free/paid tiers have their own limits and data terms. This app does not currently provide a Gemini in-app connector; an external text chat can still use the reviewed Import route.

These are policy references, not endorsements or required purchases. Deletion and training controls are separate questions. Inspect current official pricing before buying credits; the app's cost estimates are not a billing authority.

## In-app setup

Open Chat → gear. Keep Data sync on Manual, or enable Review changes before saving. These are actual in-app controls, unlike the planner's preferences. Current automatic sync is broad; per-source/per-field enforcement is not provided.

For a local model, install Ollama from its [official download](https://ollama.com/download), choose a downloaded local model that fits your device, then pull it (for example `ollama pull qwen2.5:7b`). Run the service on loopback and choose the same model in Chat settings. Follow the app's connection check, set the context window to fit your sheet, Save, and try a synthetic conversation before personal data. Installation/model downloads require disk space and internet; memory needs grow with model/context. No universal setup time or quality guarantee applies. See [Ollama quickstart](https://docs.ollama.com/quickstart) and [FAQ](https://docs.ollama.com/faq) for current platform requirements, GPU support and environment-variable setup.

If the browser blocks the connection, configure OLLAMA_ORIGINS for only the app's origin and restart the service. The exact loopback URL must match the browser URL. A downloaded file has origin `null`, which also admits other opaque/local-file origins; a dedicated loopback origin is preferable for tighter access. Do not bind to the public network or use wildcard origins just to suppress an error. Check that a local endpoint is not using a cloud-hosted model. Ollama supports disabling cloud features with OLLAMA_NO_CLOUD=1; restart it after changing configuration.

For a cloud model, choose one of the providers actually offered by Chat settings, create a provider API account/key, check billing and spend controls, and set a CS browser password before storing the key. Paste the key only into its API Key control, Save, and send a small test message. Errors about quota, billing, unavailable models or browser-origin access require checking that provider/account; a chat subscription cannot fix them by itself. Never paste keys into a conversation, guide or recovery JSON. Cloud requests send sheet context in plaintext to that provider over its connection.

After a proposed update, use the review card's Apply or discard it. Check the sheet and Undo notice, then verify persistence. Closing the tab/process stops in-app work; this is not an unattended service.

## Direct agents and integrations

The desktop MCP companion is Experimental and edits a separate selected file. Read the [companion guide](companion/README.md) for its client-specific installation, tools, revision checks, backups and undo. Use synthetic records only until browser-file synchronisation is implemented. External agent/client permissions govern folder access. A UI setting in CS cannot revoke them, and natural-language approval is not a secure file-permission boundary.

Factual integrations, high-autonomy inference and user-owned canonical Drive can be present in separately configured installations, but no universal plug-and-play setup is included in the standalone download. Generic source/field allowlists, client-side encrypted canonical storage and a persistent background bridge are Planned. They need a tested writer, attributable changes, pause, recovery and conflict handling. Keep the manual/reviewed path working while experimenting.

Developer mode means manually managing code/configuration in an isolated private copy, with backups and synthetic testing; there is no implemented Developer permission toggle. Code changes can break your installation or expose data. Contribute only generic code and fictional fixtures under the project licence, through a separately reviewed contribution. No route choice gives permission to publish your data or personalised build.

See the [threat model](threat-model.md) for browser storage, encryption limitations, permission boundaries, switching source and recovery.
