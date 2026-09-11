"""Run directly on the Windows desktop; uses an isolated temporary database."""
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import App
from add_word_dialog import AddWordDialog


def pump(app, seconds=0.3):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.update()
        time.sleep(0.01)


with tempfile.TemporaryDirectory() as folder:
    app = App(Path(folder) / 'test.db')
    dialog = AddWordDialog(app)
    dialog.source.set('Free dictionary')
    fixture = [{'meaning': 'Able to recover quickly.', 'kind': 'adjective',
                'example': 'She recovered quickly.'},
               {'meaning': 'Able to spring back into shape.', 'kind': 'adjective',
                'example': 'The material is resilient.'}]
    with patch('add_word_dialog.lookup', return_value=fixture):
        dialog.word.set('resilient')
        dialog.start_lookup()
        pump(app)
        assert dialog.get_value('meaning') == fixture[0]['meaning']
        assert dialog.get_value('example') == fixture[0]['example']
        dialog.word.set('another')
        assert dialog.get_value('meaning') == ''
        # Older replies must not populate a different word.
        dialog.messages.put((dialog.generation - 1, fixture, None))
        pump(app, 0.2)
        assert dialog.get_value('meaning') == ''
        dialog.word.set('resilient')
        dialog.start_lookup()
        dialog.put_value('meaning', 'My edited definition.')
        pump(app)
        assert dialog.get_value('meaning') == 'My edited definition.'
        dialog.choose()
        dialog.save()
        saved = app.store.words('resilient')[0]
        assert saved['meaning'] == fixture[0]['meaning']
        assert saved['example'] == fixture[0]['example']
        # Closing while a reply is pending must not call destroyed widgets.
        pending = AddWordDialog(app)
        pending.source.set('Free dictionary')
        pending.word.set('close')
        pending.start_lookup()
        pending.destroy()
        pump(app)
    app.close()
print('Dictionary lookup, stale replies, manual edits, save, and close passed.')
