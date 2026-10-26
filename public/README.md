# Welcome to Character Sheet

A free personal dashboard for what matters to you: quests, skills, check-ins and a Journal. Start with one useful entry. Everything else can stay empty.

The hosted example and its records are fictional. It does not save your edits or setup answers. Open **Help** to use **Choose your playstyle**: choose a starting point, AI location, editing route, storage, protection and review policy, then follow the instructions for your choices. Answers prepare a plan; they never connect accounts or move data.

## Ways to start

| Choice | Effort and power | Cost | Available today |
| --- | --- | --- | --- |
| Manual | Simplest; edit a name, one quest or a check-in | Free | Browser editing and full recovery exports |
| External chat | Small copy/paste steps; your AI proposes, you review | Ordinary free chat within its limits; existing subscriptions optional | instructions.md + compact context + small Import patch + feedback/Undo |
| In-app Chat | One-time local-model or API setup; conversation stays in CS | Local hardware/time or separate API charges | Local endpoint and offered cloud APIs; reviewed changes recommended |
| Direct agent/MCP | Advanced tools and permissions | Depends on your client/model | Experimental separate companion file; no browser synchronisation |

Start manually even if you plan to add AI later. From the hosted example, download your personal copy. If it downloads as character-sheet.zip, extract the whole folder and keep character-sheet.html with its assets and public-assets.json. Open character-sheet.html in your usual personal browser profile, outside private/incognito mode. Enter one test quest, reload, then close and reopen the same file to check it remains. App files are not a backup of your sheet.

For ordinary external chat, open Settings → Setup and external AI guide. Copy the short chat starter or guided start, paste it into your usual AI and send it. No upload, Project, API key or paid tools are required. A new sheet can start with one topic; an existing sheet can share selected Copy for AI detail from Data → Export. Review one proposed change, then paste the JSON into Data → Import and Apply. Check the result and Undo, then verify it remains after reopening. Continue the same conversation; refresh relevant app context after outside edits or in a new chat. The full [AI guide](instructions.md) covers other updates, and the [AI privacy and setup guide](ai-privacy-guide.md) explains the steps. Free services have usage limits; pause or keep editing manually when needed.

## Storage, permissions and recovery

Browser storage is the general standalone source. The Experimental [companion](companion/README.md) uses a separate local file. User-owned Drive setup and client-side encrypted canonical storage are Planned for general downloads; separately configured installations may have their own working Drive/integration paths. Never switch an existing source just by changing a plan answer. Reviewed proposals, factual updates and autonomous inference are different permission policies; generic source/field enforcement and a persistent just-chat service are Planned.

A browser password is a limited implemented encryption feature, not protection for every sidecar, an unlocked device, cloud requests or a canonical Drive file. Device/provider encryption differs from CS client-side encryption. Read the [threat model](threat-model.md) before sensitive use.

Data → Export → data.json is compact AI context. **Download recovery file → migration.json** is full recovery including supported history/configuration and excluding credentials/caches. Save dated private backups in a separate location. Restore through Data → Import after backing up the current sheet, then verify reload and records. Undo is short-term correction, not disaster recovery.

Updating the app is currently manual. First export a dated full recovery migration.json and keep the working old app. Download and extract the newer app separately. If your records are not visible, restore migration.json through Data → Import. Verify your records, history and settings after reopening before relying on the new copy. data.json is AI context and cannot replace this recovery backup. Moving or renaming files, changing browser/profile or clearing browser storage can change access to saved data; do not assume automatic transfer.

CS remains free. Optional donations use the existing Support action. Developer mode is an Experimental self-managed code workflow, not a casual data-update toggle. No setup choice permits publication. Keep exports, transcripts, keys, personalised pages and real fixtures out of public repositories. Public releases require separate human review.

Technical checks and human usability trials are different: the guidance is ready to try, while systematic end-user setup trials are still pending. Check the repository licence before redistribution.
