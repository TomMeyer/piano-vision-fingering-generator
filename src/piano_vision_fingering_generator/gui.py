import signal
import sys
import tkinter as tk
from tkinter import ttk, filedialog
from ttkthemes import ThemedTk
from pathlib import Path
from typing import Optional
from piano_vision_fingering_generator.io import build_and_save_piano_vision_json
from piano_vision_fingering_generator.constants import HandSize


class PianoVisionFingeringGeneratorApp:

    def __init__(self):
        self.root: tk.Tk = ThemedTk(theme="arc")
        self.root.minsize(400, 200)
        self.selected_file: Optional[Path] = None

        self.root.title("Piano Vision Fingering Generator")
        self.select_button = ttk.Button(
            self.root, text="Select File", command=self.select_file
        )
        self.select_button.pack(pady=10)
        self.file_label = ttk.Label(self.root, text="No file selected")
        self.file_label.pack(pady=10)

        #
        self.selected_choice = (
            tk.StringVar()
        )  # Variable to store the dropdown selection

        self.choices = [v.value for v in iter(HandSize)]  # List of options
        self.dropdown = ttk.Combobox(
            self.root, textvariable=self.selected_choice, values=self.choices
        )
        self.dropdown.set("Select hand size")  # Set a default value
        self.dropdown.pack(pady=10)

        self.process_button = ttk.Button(
            self.root, text="Process File", command=self.process_file, state=tk.DISABLED
        )
        self.root.after(100, self._check_interrupt)
        self.process_button.pack(pady=10)

    def _on_interrupt(self, sig, frame):
        print("\nCtrl+C caught. Exiting the application...")
        self.root.quit()  # Gracefully stop the Tkinter mainloop
        sys.exit(0)

    def _check_interrupt(self):
        try:
            signal.signal(signal.SIGINT, self._on_interrupt)
        except Exception:
            pass
        self.root.after(
            100, self._check_interrupt
        )  # Reschedule the check every 100 milliseconds

    def mainloop(self, n: int = 0):
        self.root.mainloop(n)

    def process_file(self):
        if self.selected_file and self.selected_file.exists():
            hand_size = HandSize(self.selected_choice.get())
            build_and_save_piano_vision_json(self.selected_file, hand_size)

    def select_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            file_path = Path(file_path)
            self.selected_file = file_path
            self.file_label.config(text=file_path.name)
            self.process_button.config(state=tk.NORMAL)


def run_app():
    app = PianoVisionFingeringGeneratorApp()
    app.mainloop()
