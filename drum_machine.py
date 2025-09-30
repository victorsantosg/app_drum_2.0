import os
import json
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import pygame
from db_backend import init_db, save_groove, load_all_grooves, load_groove_by_id, delete_groove, DB_FILE
import sys

def resource_path(relative_path):
    """Ajusta caminho de arquivos quando empacotado com PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

SAMPLES_PATH = resource_path("samples")


# ---------------- CONFIG ---------------- #
SAMPLES_PATH = "samples"
INSTRUMENTS = {
    "kick": ["Attack Kick 15.wav", "Attack Kick 46.wav", "Downstream Kick 04.wav", "FL 808 Kick.wav", "FL 909 Kick Alt.wav", "FL 909 Kick.wav", "FL Basic Kick.wav"],
    "snare": ["FL 808 Snare.wav", "Attack Snare 03.wav", "Attack Snare 26.wav", "FL Grv Snareclap 30.wav", "FL 808 Snare.wav", "FL 909 Snare.wav", "FL 909 Rim.wav"],
    "hat": ["Attack Hat 06.wav", "Attack OHat 02.wav"],
    "tom": ["FL 808 Tom.wav", "FL 909 Tom.wav"],
}

DISPLAY_NAMES = {
    "kick": "Bumbo",
    "snare": "Caixa",
    "hat": "Hi-hat",
    "tom": "Tom"
}

NUM_STEPS = 16

PRESETS = {
    "Reggae": {
        "kick":  [1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0],
        "snare": [0,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0],
        "hat":   [1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0],
        "tom":   [0]*16
    },
    "Rock Basico": {
        "kick":  [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
        "snare": [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        "hat":   [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
        "tom":   [0]*16
    },
    "Rock Classico": {
        "kick":  [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
        "snare": [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        "hat":   [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
        "tom":   [0]*16
    },
    "Reggae Leve":{
        "kick":  [1,0,0,0, 0,0,0,0, 1,0,0,0, 0,0,0,0],
        "snare": [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        "hat":   [0,1,0,1, 0,1,0,1, 0,1,0,1, 0,1,0,1],
        "tom":   [0]*16
    },
    "Samba": {
        "kick":  [1,0,0,1, 0,1,0,0, 1,0,0,1, 0,1,0,0],
        "snare": [0,0,1,0, 0,0,1,0, 0,0,1,0, 0,0,1,0],
        "hat":   [1,1,1,1, 1,1,1,1, 1,1,1,1, 1,1,1,1],
        "tom":   [0]*16
    }
}

# ---------------- INIT PYGAME ---------------- #
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

samples = {}
for inst, files in INSTRUMENTS.items():
    samples[inst] = []
    for f in files:
        path = os.path.join(SAMPLES_PATH, inst, f)
        if os.path.exists(path):
            try:
                samples[inst].append(pygame.mixer.Sound(path))
            except pygame.error as e:
                print(f"Erro ao carregar {path}: {e}")
        else:
            print(f"Aviso: sample não encontrado: {path}")

# ---------------- DRUM MACHINE ---------------- #
class DrumMachine:
    def __init__(self, root):
        self.root = root
        self.root.title("Drum Machine Victor S.")
        self.root.columnconfigure(0, weight=1)
        self.sequence = {inst: [0]*NUM_STEPS for inst in INSTRUMENTS.keys()}
        self.bpm = tk.IntVar(value=100)
        self.is_playing = False
        self.stop_event = threading.Event()
        self.thread = None
        self._build_ui()
        init_db()

    def _build_ui(self):
        # ---------------- BPM ---------------- #
        bpm_frame = ttk.Frame(self.root, padding=5)
        bpm_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(bpm_frame, text="BPM:").pack(side="left")
        ttk.Scale(bpm_frame, from_=40, to=200, variable=self.bpm, orient="horizontal").pack(side="left", padx=5, fill="x", expand=True)

        # ---------------- Presets ---------------- #
        preset_frame = ttk.Frame(self.root, padding=5)
        preset_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(preset_frame, text="Presets:").pack(side="left")
        self.preset_var = tk.StringVar()
        preset_combo = ttk.Combobox(preset_frame, textvariable=self.preset_var, values=list(PRESETS.keys()))
        preset_combo.pack(side="left", padx=5)
        ttk.Button(preset_frame, text="Carregar", command=self.load_preset).pack(side="left", padx=5)

        # ---------------- Timbres ---------------- #
        self.timbre_vars = {}
        timbre_frame = ttk.Frame(self.root, padding=5)
        timbre_frame.pack(fill="x", padx=5, pady=5)
        for inst, t_list in INSTRUMENTS.items():
            ttk.Label(timbre_frame, text=DISPLAY_NAMES.get(inst, inst)).pack(side="left", padx=3)
            options = [f"{DISPLAY_NAMES.get(inst, inst)} {i+1}" for i in range(len(t_list))]
            var = tk.StringVar(value=options[0])
            combo = ttk.Combobox(timbre_frame, textvariable=var, values=options, width=12)
            combo.pack(side="left", padx=3)
            self.timbre_vars[inst] = var

        # ---------------- DB ---------------- #
        db_frame = ttk.Frame(self.root, padding=5)
        db_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(db_frame, text="Grooves Salvos:").pack(side="left")
        self.db_list = ttk.Combobox(db_frame, values=[], width=30)
        self.db_list.pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(db_frame, text="Salvar Preset", command=self.save_to_db).pack(side="left", padx=3)
        ttk.Button(db_frame, text="Tocar Preset", command=self.load_from_db).pack(side="left", padx=3)
        ttk.Button(db_frame, text="Excluir Preset", command=self.delete_from_db).pack(side="left", padx=3)
        ttk.Button(db_frame, text="Atualizar Lista", command=self.refresh_db_list).pack(side="left", padx=3)

        # ---------------- Sequencer ---------------- #
        self.grid_frame = ttk.Frame(self.root, padding=5)
        self.grid_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.step_buttons = {}
        for row, inst in enumerate(INSTRUMENTS.keys()):
            self.grid_frame.rowconfigure(row, weight=1)
            tk.Label(self.grid_frame, text=DISPLAY_NAMES.get(inst, inst), width=10, anchor="e").grid(row=row, column=0, padx=5, pady=2)
            self.step_buttons[inst] = []
            for col in range(NUM_STEPS):
                btn = tk.Button(self.grid_frame, width=2, height=1, relief="raised", bg="white",
                                command=lambda i=inst, c=col: self.toggle_step(i, c))
                btn.grid(row=row, column=col+1, padx=2, pady=2, sticky="nsew")
                self.step_buttons[inst].append(btn)
            for col in range(NUM_STEPS+1):
                self.grid_frame.columnconfigure(col, weight=1)

        # ---------------- Controles ---------------- #
        ctrl_frame = ttk.Frame(self.root, padding=5)
        ctrl_frame.pack(fill="x", padx=5, pady=5)
        ttk.Button(ctrl_frame, text="▶ Play", command=self.start).pack(side="left", padx=5)
        ttk.Button(ctrl_frame, text="⏹ Stop", command=self.stop).pack(side="left", padx=5)
        ttk.Button(ctrl_frame, text="💾 Extrair Preset", command=self.save_groove).pack(side="left", padx=5)
        ttk.Button(ctrl_frame, text="📂 Importar Preset", command=self.load_groove).pack(side="left", padx=5)

        self.refresh_db_list()

    # ---------------- FUNCIONALIDADES ---------------- #
    def toggle_step(self, inst, col):
        self.sequence[inst][col] = 1 - self.sequence[inst][col]
        self.update_button_color(inst, col)

    def update_button_color(self, inst, col, active_step=None):
        btn = self.step_buttons[inst][col]
        if col == active_step:
            btn.config(bg="red")
        else:
            btn.config(bg="green" if self.sequence[inst][col] else "white")

    def loop(self):
        while not self.stop_event.is_set():
            beat_duration = 60 / self.bpm.get() / 4
            for step in range(NUM_STEPS):
                if self.stop_event.is_set(): 
                    break
                for inst, pattern in self.sequence.items():
                    if pattern[step] == 1 and samples.get(inst):
                        try:
                            idx_str = self.timbre_vars[inst].get().split()[-1]
                            idx = int(idx_str) - 1
                            if 0 <= idx < len(samples[inst]):
                                samples[inst][idx].play()
                        except Exception as e:
                            print(f"Erro ao tocar {inst}: {e}")
                self.highlight_step(step)
                time.sleep(beat_duration)
            self.highlight_step(-1)

    def highlight_step(self, step):
        def update():
            for inst in INSTRUMENTS.keys():
                for col in range(NUM_STEPS):
                    self.update_button_color(inst, col, active_step=step if col==step else None)
        self.root.after(0, update)

    # ---------------- CONTROLES ---------------- #
    def start(self):
        if self.is_playing: return
        self.is_playing = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.is_playing = False
        self.highlight_step(-1)

    # ---------------- JSON ---------------- #
    def save_groove(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json")
        if not file_path: return
        data = {"sequence": self.sequence,
                "timbres": {inst: self.timbre_vars[inst].get() for inst in self.timbre_vars}}
        with open(file_path, "w") as f:
            json.dump(data, f)
        messagebox.showinfo("Sucesso", "Groove salvo em JSON!")

    def load_groove(self):
        file_path = filedialog.askopenfilename()
        if not file_path: return
        with open(file_path, "r") as f:
            data = json.load(f)
        self.sequence = data["sequence"]
        for inst, val in data["timbres"].items():
            self.timbre_vars[inst].set(val)
        for inst in INSTRUMENTS.keys():
            for col in range(NUM_STEPS):
                self.update_button_color(inst, col)

    # ---------------- DB ---------------- #
    def save_to_db(self):
        name = simpledialog.askstring("Nome do Groove", "Digite o nome do groove:")
        if not name:
            return
        new_id = save_groove(name, self.bpm.get(),
                    {inst: self.sequence[inst].copy() for inst in INSTRUMENTS.keys()},
                    {inst: self.timbre_vars[inst].get() for inst in self.timbre_vars})
        if new_id is None:
            messagebox.showerror("Erro", "Não foi possível salvar o groove. Veja o console para detalhes.")
        else:
            messagebox.showinfo("Sucesso", f"Groove '{name}' salvo com id {new_id}!")
            self.refresh_db_list()


    def refresh_db_list(self):
        grooves = load_all_grooves()
        self.db_list["values"] = [f"[{gid}] {name} - {bpm} BPM" for gid, name, bpm in grooves]

    def load_from_db(self):
        value = self.db_list.get()
        if not value: return
        groove_id = int(value.split("]")[0][1:])
        data, bpm = load_groove_by_id(groove_id)
        if not data: return
        self.sequence = {inst: data["sequence"][inst].copy() for inst in INSTRUMENTS.keys()}
        for inst, val in data["timbres"].items():
            self.timbre_vars[inst].set(val)
        for inst in INSTRUMENTS.keys():
            for col in range(NUM_STEPS):
                self.update_button_color(inst, col)
        self.bpm.set(bpm)

    def delete_from_db(self):
        value = self.db_list.get()
        if not value: return
        groove_id = int(value.split("]")[0][1:])
        delete_groove(groove_id)
        messagebox.showinfo("Sucesso", "Groove deletado!")
        self.refresh_db_list()

    # ---------------- PRESETS ---------------- #
    def load_preset(self):
        preset_name = self.preset_var.get()
        if preset_name not in PRESETS:
            return
        preset = PRESETS[preset_name]
        for inst in INSTRUMENTS.keys():
            self.sequence[inst] = preset.get(inst, [0]*NUM_STEPS).copy()
        for inst in INSTRUMENTS.keys():
            for col in range(NUM_STEPS):
                self.update_button_color(inst, col)



# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    init_db()
    print("DB file location:", os.path.abspath(DB_FILE))  # se importar db_backend como alias
    root = tk.Tk()
    app = DrumMachine(root)
    root.mainloop()
