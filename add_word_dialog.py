"""Nonblocking dictionary lookup with editable definitions and sense selection."""
import queue
import sqlite3
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from dictionary_lookup import LookupError, lookup
from codex_provider import CodexProvider


class AddWordDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title('Add to your vocabulary')
        width = min(760, self.winfo_screenwidth() - 80)
        height = min(610, self.winfo_screenheight() - 100)
        left = max(20, min(app.winfo_rootx() + (app.winfo_width() - width) // 2, self.winfo_screenwidth() - width - 20))
        top = max(20, min(app.winfo_rooty() + 20, self.winfo_screenheight() - height - 40))
        self.geometry(f'{width}x{height}+{left}+{top}')
        self.minsize(640, 600)
        self.configure(bg='#F5F3EE', padx=25, pady=20)
        self.transient(app)
        self.grab_set()
        self.results = []
        self.messages = queue.Queue()
        self.generation = 0
        self.debounce = None
        self.poll_id = None
        self.auto_values = {}
        self.provider = CodexProvider(app.store.path.parent)
        self.cancel_event = None
        self.running_generation = None
        self.busy = False
        footer = tk.Frame(self, bg='#F5F3EE')
        footer.pack(side='bottom', fill='x', pady=(12, 0))
        app.button(footer, 'Save word', self.save).pack(side='right')
        canvas = tk.Canvas(self, bg='#F5F3EE', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=canvas.yview)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        body = tk.Frame(canvas, bg='#F5F3EE')
        window = canvas.create_window((0, 0), window=body, anchor='nw')
        body.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda event: canvas.itemconfigure(window, width=event.width))
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        app.label(body, 'Discover a new word.', 23, bold=True).pack(anchor='w')
        app.label(body, 'Generate one developed meaning and two contextual examples with your ChatGPT account.', 10, '#747D74', wraplength=600).pack(anchor='w', pady=(4, 12))
        source_row = tk.Frame(body, bg=self.cget('bg'))
        source_row.pack(fill='x', pady=(0, 10))
        self.source = tk.StringVar(value='ChatGPT via Codex')
        self.source_picker = ttk.Combobox(source_row, textvariable=self.source,
            values=('ChatGPT via Codex', 'Free dictionary'), state='readonly', width=24)
        self.source_picker.pack(side='left', padx=(0, 10))
        self.source_picker.bind('<<ComboboxSelected>>', self.changed)
        self.connect_button = app.button(source_row, 'Connect ChatGPT', self.connect, True)
        self.connect_button.pack(side='left')
        row = tk.Frame(body, bg=self.cget('bg'))
        row.pack(fill='x')
        self.word = tk.StringVar()
        word_entry = tk.Entry(row, textvariable=self.word, relief='flat', font=('Segoe UI', 13))
        word_entry.pack(side='left', fill='x', expand=True, ipady=9, padx=(0, 10))
        self.generate_button = app.button(row, 'Generate with ChatGPT', self.start_lookup)
        self.generate_button.pack(side='right')
        word_entry.bind('<Return>', lambda event: self.start_lookup())
        self.status = app.label(body, 'Uses your Codex allowance when you click Generate. Saved results can be reused offline.', 9, '#747D74', wraplength=600)
        self.status.pack(anchor='w', pady=(8, 8))
        self.cancel_button = app.button(body, 'Cancel request', self.cancel_request, True)
        self.cancel_button.pack(anchor='w', pady=(0, 8))
        self.cancel_button.configure(state='disabled')
        app.label(body, 'Meaning — editable', 10, '#747D74').pack(anchor='w')
        self.meaning = tk.Text(body, height=3, wrap='word', relief='flat', padx=10, pady=8, font=('Segoe UI', 11))
        self.meaning.pack(fill='x', pady=(4, 4))
        app.label(body, 'Two example sentences — editable', 10, '#747D74').pack(anchor='w', pady=(12, 3))
        self.examples = tk.Text(body, height=5, wrap='word', relief='flat', padx=8, pady=8, font=('Segoe UI', 11))
        self.examples.pack(fill='x')
        self.word.trace_add('write', self.changed)
        self.poll_id = self.after(100, self.poll)
        word_entry.focus_set()

    def get_value(self, key):
        return (self.meaning if key == 'meaning' else self.examples).get('1.0', 'end-1c')

    def put_value(self, key, value):
        widget = self.meaning if key == 'meaning' else self.examples
        widget.delete('1.0', 'end')
        widget.insert('1.0', value)

    def changed(self, *args):
        self.generation += 1
        if self.cancel_event:
            self.cancel_event.set()
        if self.debounce:
            self.after_cancel(self.debounce)
        # Clear only dictionary-filled values, preserving any manual edits.
        for key, value in self.auto_values.items():
            if self.get_value(key) == value:
                self.put_value(key, '')
        self.auto_values = {}
        self.results = []
        is_ai = self.source.get() == 'ChatGPT via Codex'
        self.generate_button.configure(text='Generate with ChatGPT' if is_ai else 'Find meaning')
        self.status.configure(text='Click Generate or press Enter when your word is ready.' if is_ai else 'Click Find meaning or press Enter for dictionary lookup.')
        self.debounce = None

    def set_busy(self, busy):
        self.busy = busy
        self.generate_button.configure(state='disabled' if busy else 'normal')
        self.connect_button.configure(state='disabled' if busy else 'normal')
        self.source_picker.configure(state='disabled' if busy else 'readonly')
        self.cancel_button.configure(state='normal' if busy else 'disabled')

    def cancel_request(self):
        if self.cancel_event:
            self.cancel_event.set()
        self.generation += 1
        self.status.configure(text='Request cancelled. Any usage already incurred may still count.')

    def run_worker(self, work):
        if self.busy:
            return
        self.generation += 1
        generation = self.generation
        self.running_generation = generation
        self.cancel_event = threading.Event()
        cancel = self.cancel_event
        self.set_busy(True)

        def worker():
            try:
                result, error = work(cancel), None
            except LookupError as exc:
                result, error = [], str(exc)
            except Exception:
                result, error = [], 'Could not finish the request. Reconnect ChatGPT or try the dictionary.'
            self.messages.put((generation, result, error))
        threading.Thread(target=worker, daemon=True).start()

    def connect(self):
        if self.busy:
            return
        self.status.configure(text='Connecting to ChatGPT. If a browser opens, complete the official sign-in there.')
        self.run_worker(lambda cancel: {'connection': self.provider.connect(cancel)})

    def start_lookup(self):
        if self.busy:
            return
        word = self.word.get().strip()
        if not word:
            self.status.configure(text='Enter an English word first.')
            return
        if self.source.get() == 'ChatGPT via Codex':
            self.status.configure(text=f'Generating a developed meaning and two contextual examples for “{word}”…')
            self.run_worker(lambda cancel: self.provider.generate(word, cancel))
        else:
            self.status.configure(text=f'Finding dictionary meanings for “{word}”…')
            self.run_worker(lambda cancel: lookup(word))

    def poll(self):
        try:
            while True:
                generation, result, error = self.messages.get_nowait()
                if generation == self.running_generation:
                    self.set_busy(False)
                if generation != self.generation:
                    continue
                if error:
                    self.status.configure(text=error)
                    continue
                if isinstance(result, dict) and 'connection' in result:
                    self.status.configure(text=result['connection'])
                    continue
                self.results = result
                self.choose(preserve_manual=True)
        except queue.Empty:
            pass
        self.poll_id = self.after(100, self.poll)

    def choose(self, event=None, preserve_manual=False):
        if not self.results:
            return
        result = self.results[0]
        for key in ('meaning', 'example'):
            if key not in result:
                continue
            current = self.get_value(key)
            if preserve_manual and current and current != self.auto_values.get(key):
                continue
            self.put_value(key, result[key])
            self.auto_values[key] = result[key]
        source = result.get('source', 'Free Dictionary API')
        example_count = len([line for line in result.get('example', '').splitlines() if line.strip()])
        self.status.configure(text=f"One meaning and {example_count} example{'s' if example_count != 1 else ''} · {source}. Review and edit before saving.")

    def save(self):
        try:
            self.app.store.add_word(self.word.get(), self.get_value('meaning'), '',
                                    self.get_value('example'), '', 'word')
        except (ValueError, sqlite3.IntegrityError) as exc:
            messagebox.showerror('Could not add word', 'That word is already in your collection.' if isinstance(exc, sqlite3.IntegrityError) else str(exc), parent=self)
            return
        self.destroy()
        self.app.library()

    def destroy(self):
        if self.cancel_event:
            self.cancel_event.set()
        if self.debounce:
            self.after_cancel(self.debounce)
        if self.poll_id:
            self.after_cancel(self.poll_id)
        super().destroy()
