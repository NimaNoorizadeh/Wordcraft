"""End-to-end AI dialog test. Pass --live to use the signed-in Codex allowance."""
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import App
from add_word_dialog import AddWordDialog
from codex_provider import parse_generated
from test_codex_provider import ENTRY
import json


def wait(app, dialog):
    deadline = time.monotonic() + 190
    while dialog.busy and time.monotonic() < deadline:
        app.update()
        time.sleep(0.02)
    assert not dialog.busy, 'UI request timed out'
    app.update()


with tempfile.TemporaryDirectory() as folder:
    app = App(Path(folder) / 'vocabulary.db')
    dialog = AddWordDialog(app)
    dialog.word.set('resilient')
    app.update()
    assert not dialog.busy, 'Typing must not trigger generation'
    if '--live' in sys.argv:
        print('Generating through ChatGPT in the desktop dialog...', flush=True)
        dialog.start_lookup()
        wait(app, dialog)
    else:
        with patch.object(dialog.provider, 'generate', return_value=parse_generated(json.dumps(ENTRY))) as generate:
            dialog.start_lookup()
            dialog.start_lookup()
            wait(app, dialog)
            assert generate.call_count == 1, 'Duplicate click must not spend allowance twice'
    assert dialog.results, dialog.status.cget('text')
    assert len(dialog.get_value('example').splitlines()) == 2
    assert not hasattr(dialog, 'senses')
    assert not hasattr(dialog, 'fields')
    original = dialog.get_value('meaning')
    dialog.save()
    assert app.store.words('resilient')[0]['meaning'] == original
    app.start_review('express')
    app.update()
    app.close()
    # Reopen the database: the generated entry and schedules must survive.
    app = App(Path(folder) / 'vocabulary.db')
    assert app.store.words('resilient')[0]['meaning'] == original
    assert len(app.store.due('express')) == 13
    app.close()
print('ChatGPT dialog, one meaning, two examples, save, and persistence passed.', flush=True)
