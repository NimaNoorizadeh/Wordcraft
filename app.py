"""Wordcraft — an offline desktop vocabulary practice space."""
import os
import sqlite3
# tkinter is Python's built-in library for creating desktop graphical interfaces.
import tkinter as tk
from datetime import datetime
# Path provides a cleaner, modern way to work with file and directory paths.
from pathlib import Path
# filedialog opens operating-system file dialogs.
# messagebox displays popup messages.
from tkinter import filedialog, messagebox

from storage import Store
from notebook_suggestions import choose_suggestions

BG = '#F5F3EE'
PAPER = '#FFFFFF'
INK = '#253D35'
MUTED = '#747D74'
GREEN = '#30694F'
LINE = '#E0E3DA'


def default_database_path():
    """Return a writable database location for the current Windows user."""
    custom_directory = os.environ.get('WORDCRAFT_DATA_DIR')
    if custom_directory:
        data_directory = Path(custom_directory).expanduser()
    else:
        local_app_data = os.environ.get('LOCALAPPDATA')
        data_directory = (Path(local_app_data) if local_app_data else Path.home()) / 'Wordcraft'
    return data_directory / 'vocabulary.db'


# tk.Tk is Tkinter's main application window.

class App(tk.Tk):
    def __init__(self, data_path=None):
        super().__init__()
        self.title('Wordcraft')
        self.geometry('1180x820')
        self.minsize(960, 730)

        # Background color
        self.configure(bg=BG)
        default = default_database_path()
        #create database
        self.store = Store(data_path or default)
        self.protocol('WM_DELETE_WINDOW', self.close) #close button
        self.option_add('*Font', '{Segoe UI} 11')
        self.queue = []
        self.review_index = 0 #Keeps track of which word the user is currently reviewing.
        self.session_size = 10
        self.draft = ''
        self.draft_widget = None
        self.sidebar = tk.Frame(self, bg=INK, width=220)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)

        # Create the Wordcraft logo/title
        logo = self.label(self.sidebar, 'wordcraft', 23, '#FFFFFF', INK, bold=True)
        logo.configure(anchor='center')
        logo.pack(fill='x', padx=12, pady=(35, 55))

        self.nav = {} #This creates an empty dictionary.You're going to store the sidebar buttons in it.

        for name, action in [('Overview', self.home), ('My vocabulary', self.library), ('Practice', self.practice), ('Writing notebook', self.notebook)]:
            b = tk.Button(self.sidebar, text=name, command=action, anchor='w', bg=INK, fg='#DCE5DB', activebackground=GREEN, activeforeground='white', relief='flat', bd=0, padx=25, pady=14, cursor='hand2')
            b.pack(fill='x', padx=10, pady=3)
            self.nav[name] = b

        self.label(self.sidebar, 'A little practice.\nMore words that feel like you.', 10, '#B5C4B4', INK).pack(side='bottom', anchor='w', padx=25, pady=30)
        self.content = tk.Frame(self, bg=BG)
        self.content.pack(side='left', fill='both', expand=True, padx=40, pady=30)
        self.home()

    def label(self, parent, text, size=11, fg=INK, bg=None, bold=False, **kw):
        return tk.Label(parent, text=text, font=('Segoe UI', size, 'bold' if bold else 'normal'), fg=fg, bg=bg or parent.cget('bg'), justify='left', anchor='w', **kw)

    def button(self, parent, text, command, secondary=False):
        return tk.Button(parent, text=text, command=command, bg=LINE if secondary else GREEN, fg=INK if secondary else 'white', activebackground='#CFD9CD' if secondary else INK, activeforeground=INK if secondary else 'white', relief='flat', bd=0, padx=20, pady=11, cursor='hand2', font=('Segoe UI', 10, 'bold'))

    def page(self, name, title, subtitle, show_name=True):
        if self.draft_widget is not None and self.draft_widget.winfo_exists():
            self.draft = self.draft_widget.get('1.0', 'end-1c')
        self.draft_widget = None
        for child in self.content.winfo_children():
            child.destroy()
        for key, b in self.nav.items():
            b.configure(bg=GREEN if key == name else INK)
        if show_name:
            self.label(self.content, name.upper(), 9, MUTED, bold=True).pack(anchor='w', pady=(0, 12))
        title_label = self.label(self.content, title, 28, bold=True)
        title_label.pack(anchor='w', pady=(0, 25) if not subtitle else 0)
        if subtitle:
            self.label(self.content, subtitle, 11, MUTED, wraplength=700).pack(anchor='w', pady=(7, 25))

    def card(self, parent=None):
        f = tk.Frame(parent or self.content, bg=PAPER, padx=24, pady=22, highlightbackground=LINE, highlightthickness=1)
        f.pack(fill='x', pady=(0, 16))
        return f

    def home(self):
        self.page('Overview', 'Make the words yours', 'Build the English you can reach for in a conversation or on a blank page.')
        stats = self.store.stats()
        row = tk.Frame(self.content, bg=BG)
        row.pack(fill='x', pady=(0, 22))
        for i, (value, text) in enumerate([(stats['words'], 'words & phrases'), (stats['due'], 'reviews ready'), (stats['today'], 'reviews today'), (stats['growing'], 'expression progress*')]):
            f = tk.Frame(row, bg=PAPER, padx=18, pady=14)
            f.grid(row=0, column=i, sticky='nsew', padx=(0, 10 if i < 3 else 0))
            row.columnconfigure(i, weight=1)
            self.label(f, str(value), 27, bold=True).pack(anchor='w')
            self.label(f, text, 10, MUTED).pack(anchor='w')
        card = self.card()
        self.label(card, 'YOUR DAILY PRACTICE', 9, GREEN, bold=True).pack(anchor='w')
        self.label(card, 'A small session. A useful step forward.', 20, bold=True).pack(anchor='w', pady=(10, 6))
        self.label(card, 'Recall a phrase, check the example, then make a sentence of your own.\nYour next review adapts to how easily you remembered it.', 11, MUTED, wraplength=650).pack(anchor='w', pady=(0, 18))
        self.button(card, 'Start practicing  →', self.practice).pack(anchor='w')
        bottom = self.card()
        self.label(bottom, 'Learn for the moments that matter.', 17, bold=True).pack(anchor='w')
        self.label(bottom, 'Save expressions from your life: a book, a meeting, a conversation.\nLearn the phrase around a word so it is easier to use naturally.', 11, MUTED, wraplength=650).pack(anchor='w', pady=10)
        self.button(bottom, '+ Add a word or phrase', self.add_word, True).pack(anchor='w')
        self.label(self.content, '* Words with at least 3 consecutive successful expression self-ratings.\nAll vocabulary, reviews, and writing are saved on this computer.', 9, MUTED).pack(anchor='w', pady=5)

    def library(self):
        self.page('My vocabulary', 'Your growing collection', '', show_name=False)
        toolbar = tk.Frame(self.content, bg=BG)
        toolbar.pack(fill='x', pady=(0, 16))
        search = tk.StringVar()
        entry = tk.Entry(toolbar, textvariable=search, relief='flat', bg=PAPER, font=('Segoe UI', 12))
        entry.pack(side='left', fill='x', expand=True, ipady=11, padx=(0, 12))
        self.button(toolbar, '+ Add word', self.add_word).pack(side='left')
        filter_row = tk.Frame(self.content, bg=BG)
        filter_row.pack(fill='x', pady=(0, 12))
        self.label(filter_row, 'Show', 10, MUTED).pack(side='left', padx=(0, 9))
        difficulty = tk.StringVar(value='all')
        filter_buttons = {}

        def set_filter(value):
            difficulty.set(value)
            for key, button in filter_buttons.items():
                selected = key == value
                button.configure(
                    bg=GREEN if selected else LINE,
                    fg='white' if selected else INK,
                    activebackground=INK if selected else '#CFD9CD',
                    activeforeground='white' if selected else INK,
                )
            refresh()

        for key, text in [('all', 'All'), ('easy', 'Easy'), ('good', 'Good'), ('hard', 'Hard')]:
            button = self.button(filter_row, text, lambda value=key: set_filter(value), key != 'all')
            button.configure(padx=14, pady=6)
            button.pack(side='left', padx=(0, 6))
            filter_buttons[key] = button
        area = tk.Frame(self.content, bg=BG)
        area.pack(fill='both', expand=True)
        words_list = tk.Listbox(area, width=23, bg=PAPER, fg=INK, selectbackground=GREEN, selectforeground='white', relief='flat', bd=0, highlightthickness=0, font=('Segoe UI', 12), activestyle='none', exportselection=False)
        words_list.pack(side='left', fill='both', padx=(0, 5))
        scrollbar = tk.Scrollbar(area, command=words_list.yview)
        scrollbar.pack(side='left', fill='y', padx=(0, 18))
        words_list.configure(yscrollcommand=scrollbar.set)
        detail = tk.Frame(area, bg=PAPER, padx=24, pady=22)
        detail.pack(side='left', fill='both', expand=True)
        matches = []

        def available_wrap_width():
            width = detail.winfo_width()
            return max(260, width - 50) if width > 100 else 390

        def resize_detail(event):
            wrap_width = max(260, event.width - 50)
            for child in detail.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(wraplength=wrap_width)

        detail.bind('<Configure>', resize_detail)

        def select(event=None):
            for child in detail.winfo_children():
                child.destroy()
            if not words_list.curselection():
                self.label(detail, 'No matching words.', 14).pack(anchor='w')
                return
            w = matches[words_list.curselection()[0]]
            wrap_width = available_wrap_width()
            self.label(detail, w['word'], 23, bold=True, wraplength=wrap_width).pack(anchor='w', pady=(0, 15))
            self.label(detail, 'MEANING', 9, MUTED, bold=True).pack(anchor='w', pady=(12, 4))
            self.label(detail, w['meaning'], 12, wraplength=wrap_width).pack(anchor='w')
            self.label(detail, 'EXAMPLES', 9, MUTED, bold=True).pack(anchor='w', pady=(22, 8))
            examples = [line.strip() for line in w['example'].splitlines() if line.strip()][:2]
            for number, example in enumerate(examples, 1):
                self.label(detail, f'{number}.  {example}', 12, wraplength=wrap_width).pack(anchor='w', pady=(0, 16))
            if not examples:
                self.label(detail, 'No examples saved for this word yet.', 11, MUTED, wraplength=wrap_width).pack(anchor='w')

        def refresh(*args):
            matches[:] = self.store.words(search.get(), difficulty.get())
            words_list.delete(0, 'end')
            for w in matches:
                words_list.insert('end', '  ' + w['word'])
            if matches:
                words_list.selection_set(0)
            select()
        words_list.bind('<<ListboxSelect>>', select)
        search.trace_add('write', refresh)
        refresh()
        self.button(self.content, 'Export vocabulary', self.export, True).pack(anchor='w', pady=(15, 0))

    def add_word(self):
        from add_word_dialog import AddWordDialog
        AddWordDialog(self)

    def practice(self):
        self.page('Practice', 'Turn knowing into using.', '', show_name=False)
        controls = tk.Frame(self.content, bg=BG)
        controls.pack(fill='x', pady=(0, 18))
        self.label(controls, 'Words per session', 10, MUTED).pack(side='left', padx=(0, 10))
        size_var = tk.StringVar(value=str(self.session_size))
        review_buttons = {}
        due_counts = {}

        def selected_size():
            try:
                return max(1, min(100, int(size_var.get())))
            except ValueError:
                return self.session_size

        def refresh_buttons(*args):
            limit = selected_size()
            for review_mode, button in review_buttons.items():
                count = due_counts[review_mode]
                button.configure(text=f'Practice {min(count, limit)} of {count} ready  →' if count else 'All caught up')

        def save_size(event=None):
            self.session_size = selected_size()
            size_var.set(str(self.session_size))
            refresh_buttons()

        size = tk.Spinbox(
            controls,
            from_=1,
            to=100,
            width=5,
            textvariable=size_var,
            command=save_size,
            justify='center',
            relief='flat',
            bg=PAPER,
            fg=INK,
            buttonbackground=LINE,
            font=('Segoe UI', 11),
        )
        size.pack(side='left', ipady=6)
        size.bind('<Return>', save_size)
        size.bind('<FocusOut>', save_size)

        for mode, title, description in [('express', 'I can use it', 'See a meaning, recall the word.'), ('understand', 'I understand it', 'See the word and explain its meaning before revealing the answer.')]:
            card = self.card()
            count = len(self.store.due(mode))
            due_counts[mode] = count
            self.label(card, title, 22, bold=True).pack(anchor='w')
            if description:
                self.label(card, description, 11, MUTED, wraplength=650).pack(anchor='w', pady=10)
            button = self.button(card, '', lambda m=mode: self.start_review(m, selected_size()))
            button.pack(anchor='w')
            review_buttons[mode] = button
        size_var.trace_add('write', refresh_buttons)
        refresh_buttons()
        self.label(self.content, 'New here? Browse your vocabulary first to learn the starter phrases.\nReviews use honest self-assessment, with examples to help you compare.', 10, MUTED).pack(anchor='w')

    def start_review(self, mode, session_size=None):
        if session_size is not None:
            self.session_size = max(1, min(100, int(session_size)))
        self.mode = mode
        self.queue = list(self.store.due(mode))[:self.session_size]
        self.review_index = 0
        self.review_card()

    def review_card(self):
        if self.review_index >= len(self.queue):
            self.page('Practice', 'A little more fluent.', f'{len(self.queue)} reviews completed in this session.' if self.queue else 'There are no reviews due for this skill right now.', show_name=False)
            card = self.card()
            self.label(card, 'Let those words settle.', 22, bold=True).pack(anchor='w')
            self.label(card, 'Your answers are saved. Try using a phrase in your notebook,\nor come back when your next reviews are ready.', 11, MUTED).pack(anchor='w', pady=14)
            self.button(card, 'Open writing notebook  →', self.notebook).pack(anchor='w')
            self.button(card, 'Back to practice', self.practice, True).pack(anchor='w', pady=(12, 0))
            return
        w = self.queue[self.review_index]
        self.page('Practice', 'Find the words.', f"{'Expression' if self.mode == 'express' else 'Understanding'}  ·  {self.review_index + 1} / {len(self.queue)}", show_name=False)
        card = self.card()
        self.label(card, 'RECALL BEFORE YOU REVEAL', 9, GREEN, bold=True).pack(anchor='w')
        self.label(card, w['meaning'] if self.mode == 'express' else w['word'], 22, bold=True, wraplength=680).pack(anchor='w', pady=(12, 10))
        self.label(card, w['prompt'] if self.mode == 'express' else 'What does this mean? Explain it in your own words.', 11, MUTED, wraplength=680).pack(anchor='w', pady=(0, 12))
        self.label(card, 'Write your answer, or say it aloud before checking.', 10, MUTED).pack(anchor='w')
        answer = tk.Text(card, height=3, wrap='word', bg=BG, fg=INK, relief='flat', padx=12, pady=10, font=('Segoe UI', 12))
        answer.pack(fill='x', pady=10)
        answer.focus_set()
        reveal_button = self.button(card, 'Reveal & compare', lambda: reveal())
        reveal_button.pack(anchor='w')

        def reveal():
            reveal_button.destroy()
            self.label(card, w['word'] + '  ·  ' + w['phrase'], 16, GREEN, bold=True, wraplength=680).pack(anchor='w', pady=(8, 4))
            self.label(card, w['meaning'] + '\n' + w['example'], 11, wraplength=680).pack(anchor='w', pady=(0, 9))
            row = tk.Frame(card, bg=PAPER)
            row.pack(fill='x', pady=(14, 0))
            for rating, name in [('again', 'Again'), ('hard', 'Hard'), ('good', 'Good'), ('easy', 'Easy')]:
                self.button(row, name, lambda r=rating: finish(r), rating != 'good').pack(side='left', padx=(0, 7))

        def finish(rating):
            self.store.review(w['id'], self.mode, rating, answer.get('1.0', 'end-1c'))
            self.review_index += 1
            self.review_card()

    def notebook(self):
        self.page('Writing notebook', 'Give your words a life.', 'Write a short paragraph. Read it aloud, then check whether your phrases sound natural.')
        suggestions = choose_suggestions(self.store.words())
        suggestion_label = self.label(self.content, 'TRY USING:  ' + '  ·  '.join(w['word'] for w in suggestions), 11, GREEN, wraplength=700, bold=True)
        suggestion_label.pack(anchor='w', pady=(0, 12))
        editor = tk.Text(self.content, height=7, wrap='word', bg=PAPER, fg=INK, relief='flat', padx=18, pady=16, undo=True, font=('Segoe UI', 12))
        editor.pack(fill='x')
        editor.insert('1.0', self.draft)
        self.draft_widget = editor
        row = tk.Frame(self.content, bg=BG)
        row.pack(fill='x', pady=12)
        status = self.label(row, '', 10, GREEN)

        def save():
            try:
                self.store.save_note(editor.get('1.0', 'end-1c'))
            except ValueError as exc:
                status.configure(text=str(exc))
                return
            editor.delete('1.0', 'end')
            self.draft = ''
            status.configure(text='Saved to your notebook.')
            suggestions[:] = choose_suggestions(self.store.words(), [w['id'] for w in suggestions])
            suggestion_label.configure(text='TRY USING:  ' + '  ·  '.join(w['word'] for w in suggestions))
            refresh()
            editor.focus_set()
        self.button(row, 'Save entry', save).pack(side='left', padx=(0, 15))
        status.pack(side='left')
        self.label(self.content, 'YOUR PREVIOUS ENTRIES', 9, MUTED, bold=True).pack(anchor='w', pady=(12, 10))
        history = tk.Text(self.content, height=8, wrap='word', bg=BG, fg=INK, relief='flat', font=('Segoe UI', 11))
        history.pack(fill='both', expand=True)

        def refresh():
            history.configure(state='normal')
            history.delete('1.0', 'end')
            entries = self.store.notes()
            if not entries:
                history.insert('end', 'Your writing will collect here. Start with a few sentences about your day.')
            for note in entries:
                date = datetime.fromisoformat(note['created']).astimezone().strftime('%d %b %Y · %H:%M')
                history.insert('end', date + '\n' + note['body'] + '\n\n')
            history.configure(state='disabled')
        refresh()

    def export(self):
        target = filedialog.asksaveasfilename(title='Export vocabulary and progress', defaultextension='.json', initialfile='wordcraft-export.json', filetypes=[('JSON files', '*.json')])
        if target:
            try:
                self.store.export(target)
                messagebox.showinfo('Export complete', 'Your vocabulary, schedules, reviews, and notebook were exported.')
            except OSError as exc:
                messagebox.showerror('Export failed', str(exc))

    def close(self):
        if self.draft_widget is not None and self.draft_widget.winfo_exists():
            self.draft = self.draft_widget.get('1.0', 'end-1c')
        if self.draft.strip():
            choice = messagebox.askyesnocancel('Unsaved writing', 'Save your notebook draft before closing?')
            if choice is None:
                return
            if choice:
                self.store.save_note(self.draft)
        self.store.close()
        self.destroy()


if __name__ == '__main__':
    App().mainloop()
