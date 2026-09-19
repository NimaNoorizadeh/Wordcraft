"""Desktop check for expression review reveal content."""
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
        meaning = 'Belief in or acceptance of something as true.'
        examples = 'The evidence lent credence to the theory.\nThey gave little credence to the claim.'
        app.store.add_word('credence', meaning, '', examples, '', 'word')
        app.mode = 'express'
        app.queue = [app.store.words('credence')[0]]
        app.review_index = 0
        app.review_card()
        app.update()

        before = [widget.cget('text') for widget in descendants(app.content) if isinstance(widget, tk.Label)]
        assert before.count(meaning) == 1
        meaning_label = next(widget for widget in descendants(app.content)
                             if isinstance(widget, tk.Label) and widget.cget('text') == meaning)
        normal_wrap = int(meaning_label.cget('wraplength'))
        assert normal_wrap > 680, normal_wrap

        app.geometry('1600x900')
        app.update()
        wide_wrap = int(meaning_label.cget('wraplength'))
        assert wide_wrap > normal_wrap, (normal_wrap, wide_wrap)

        app.geometry('960x730')
        app.update()
        narrow_wrap = int(meaning_label.cget('wraplength'))
        assert 360 <= narrow_wrap < wide_wrap, (narrow_wrap, wide_wrap)

        reveal = next(widget for widget in descendants(app.content)
                      if isinstance(widget, tk.Button) and widget.cget('text') == 'Reveal & compare')
        reveal.invoke()
        app.update()

        after = [widget.cget('text') for widget in descendants(app.content) if isinstance(widget, tk.Label)]
        assert after.count(meaning) == 1, 'The comparison area must not repeat the meaning'
        assert after.count('credence') == 1
        assert not any('credence  ·  credence' in text for text in after)
        assert examples in after
    finally:
        app.close()

print('Expression reveal shows one word and examples without repeating the meaning.')
