# Wordcraft

A Windows desktop app for building English vocabulary for speaking and writing, with local storage and online dictionary lookup.

## Launch

Download or clone the repository, then double-click **Launch Wordcraft.vbs** or run `python app.py` in the project folder.
Requires Python 3.10+ with Tkinter.
No extra Python packages are required. AI generation uses the installed Codex CLI and your ChatGPT sign-in. The dictionary and manual entry options do not require a ChatGPT account. This version runs from Python; it is not a packaged executable.

## Generate with your ChatGPT account

1. Click **Add word**. Leave **ChatGPT via Codex** selected.
2. If needed, click **Connect ChatGPT**. An existing Codex ChatGPT sign-in is reused; otherwise complete the official login in your browser.
3. Enter a word or phrase and click **Generate with ChatGPT**, or press Enter.
4. Review the generated meaning and two examples, edit them if needed, then click **Save word**.

Generation uses your available Codex allowance and needs internet access. Typing does not start generation. Repeated clicks are blocked while a request is running; **Cancel request** stops the request, although usage already incurred can still count. Completed generations are cached in `%LOCALAPPDATA%\Wordcraft\generated-cache` and can be reused offline. AI content can be imperfect, so all fields remain editable.

ChatGPT generates one developed meaning of about 25 to 45 words and two contextual examples of about 12 to 25 words each. Regenerating a word after this update creates a new result instead of reusing an older short cached entry.

This integration uses the official [Codex App Server](https://learn.chatgpt.com/docs/app-server) over local stdio, tested with Codex CLI 0.153.4. It uses ephemeral conversations and an isolated generation working folder with a read-only sandbox. Tool-related features are disabled for that process. Wordcraft does not read or copy authentication tokens, change your Codex configuration, or fall back to paid API-key authentication. Sign-in credentials remain managed by Codex. The client uses the configured Codex model with low reasoning effort.

If Codex cannot be found, install/open Codex and restart Wordcraft. If your sign-in expires, use **Connect ChatGPT**. If your allowance is exhausted, wait for it to reset or choose **Free dictionary**. These do not automatically buy additional usage. Your saved vocabulary and notebook are not included in generation requests; the app submits the requested word and tutoring instructions.

## Practice

Browse the 12 starter words and phrases, then choose **I can use it** or **I understand it**. Recall your answer before revealing the example. Write an answer or speak aloud, compare your phrasing, and rate your recall. Speaking is self-directed: there is no recording, speech recognition, or automatic pronunciation assessment.

Each skill has an independent schedule. Again returns in 10 minutes, Hard in 1 day, Good in 3 days, and Easy in 7 days. Two consecutive Easy ratings schedule the word in 30 days; any other rating breaks that Easy streak. The Practice page lets you choose 1 to 100 words per session and starts at 10. These are simple scheduling heuristics, not a validated personal memory model. Progress counts are self-reported practice indicators, not proof of mastery.

The vocabulary list can be filtered by the latest practice rating. Easy and Good show those exact ratings, while Hard includes both Hard and Again. Words that have not been reviewed yet remain visible under All.

For dictionary lookup, select **Free dictionary**, type an English word, and press Enter or **Find meaning**. The first available meaning and example are filled in and remain editable. Only the word and meaning are required.

Lookup uses [Free Dictionary API](https://dictionaryapi.dev/) over HTTPS and sends only the entered word. It requires internet access and may not cover every word or multiword expression. On a failed lookup, you can retry or enter a definition manually. Saved definitions remain available offline. Dictionary responses do not always include example sentences; the app does not invent them.

Use the notebook for longer writing. After saving an entry, the suggested words refresh and prefer words outside the previous combination. With more than three vocabulary items, the next combination always changes. Model examples support self-assessment; automatic grammar or usage correction is not included.

## Local data

The SQLite database is saved at `%LOCALAPPDATA%\Wordcraft\vocabulary.db`. The folder is created automatically for each user, so the app does not depend on a particular drive or project location. Advanced users can set `WORDCRAFT_DATA_DIR` to store the database in another folder. Data persists across app restarts. The library's export button saves all vocabulary, schedules, reviews, and notebook entries as JSON. To restore a full database backup, close the app and replace `vocabulary.db` with your saved database copy. JSON import is not included.

## Check

Run `python -m unittest discover -s tests -v` for persistence and scheduling checks.

Desktop checks: `python tests/ui_lookup_smoke.py` and `python tests/ui_codex_smoke.py`. To test real AI generation using your ChatGPT allowance and a temporary vocabulary database, run `python tests/ui_codex_smoke.py --live`.
