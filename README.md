# Character Sheet

Release sources for [Character Sheet](https://character-sheet.quiethawk512.chatgpt.site/character-sheet).

This snapshot contains the fictional example, blank app, optimised artwork and user guides. Personal sheets, private development history, original artwork masters, credentials and recovery files are excluded.

## Run locally

Use Python 3 to rebuild the two exact downloads, then start a local static server:

    python3 tools/build_downloads.py
    python3 -m http.server 8080 --bind 127.0.0.1 --directory public

Open http://127.0.0.1:8080/character-sheet.html for the example or http://127.0.0.1:8080/blank.html for a blank sheet. Keep personal data and exports private. A static source checkout does not include a personal Drive connection or private local bridge.

## Release contents

release-pins.json records the published file hashes. tools/build_downloads.py --check-only reconstructs and checks the downloads in memory. Generated ZIP and companion bundles are deliberately excluded from Git; they are rebuilt from the same optimised assets instead of storing duplicate archives.

App updates and user data remain separate. Replacing app files does not merge, reassess or migrate a personal sheet automatically. Use the app's documented export/recovery flow before moving browsers, profiles or storage locations.
