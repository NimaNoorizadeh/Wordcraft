"""Desktop regression check for fresh notebook prompts after saving."""
import sys
import tempfile
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import App


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


with tempfile.TemporaryDirectory() as folder:
    app = App(Path(folder) / 'vocabulary.db')
    try:
        app.notebook()
        app.update()
        prompt = next(widget for widget in descendants(app.content)
                      if isinstance(widget, tk.Label) and widget.cget('text').startswith('TRY USING:'))
        save = next(widget for widget in descendants(app.content)
                    if isinstance(widget, tk.Button) and widget.cget('text') == 'Save entry')

        original_prompt = prompt.cget('text')
        save.invoke()
        app.update()
        assert prompt.cget('text') == original_prompt, 'A failed save must preserve the prompt'
        assert not app.store.notes()

        previous = set(original_prompt.removeprefix('TRY USING:  ').split('  ·  '))
        for number in range(2):
            body = f'Notebook entry {number + 1}.'
            app.draft_widget.insert('1.0', body)
            save.invoke()
            app.update()
            current = set(prompt.cget('text').removeprefix('TRY USING:  ').split('  ·  '))
            assert len(current) == 3
            assert current.isdisjoint(previous), 'Saved prompts must rotate to available alternatives'
            assert app.store.notes()[0]['body'] == body
            assert app.draft_widget.get('1.0', 'end-1c') == ''
            previous = current
    finally:
        app.draft = ''
        if app.draft_widget is not None and app.draft_widget.winfo_exists():
            app.draft_widget.delete('1.0', 'end')
        app.close()

print('Notebook saves rotate suggestions and preserve entries.')
