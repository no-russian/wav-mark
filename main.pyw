import os
import sys
import struct
import time
import webbrowser

# UI
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD

# General wave handling
from pydub import AudioSegment
from pygame import mixer
import wave

# Waveform rendering
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

TITLE = "wavMark"
UINT_32_SIZE = (1 << 32) - 1
GITHUB_LINK = "https://github.com/no-russian/wav-mark"

sound_path = "sample-sounds/Windows Background.wav"

playing = False
player = None
audio: AudioSegment = AudioSegment.from_file(sound_path)

window = TkinterDnD.Tk()
window.title(TITLE)
window.geometry("640x300")
window.minsize(450, 350)

cursor_line = None
fig_canvas = None
fig_ax = None
playback_start_time = 0
bg_cache = None  # Cache for background blitting

cues = []

if sys.platform == "win32": window.iconbitmap(default="icon.ico")

loop = tk.IntVar()

def check_wav_validity(path):
    try:
        with wave.open(path, "rb") as f:
            f.getparams()
            return True
    except:
        messagebox.showerror("Error Opening WAV", "Invalid WAV file: " + path + "\nMust be a valid WAV file with PCM data")
        return False

def update_status_label():
    sample_rate_label.config(text=
        f"File: {sound_path}\n"
        f"Sample Rate: {str(audio.frame_rate)}, Bit Depth: {str(audio.sample_width * 8)}, Channels: {str(audio.channels)}\n"
        f"Duration: {audio.duration_seconds:.3f} seconds ({int(audio.frame_count())} samples)"
    )

def get_wav_cues(path):
    file_cues = []

    with open(path, "rb") as file:
        file.seek(12)

        friendly_name = os.path.basename(path)
        while True:
            header = file.read(8)

            if len(header) < 8:
                break

            chunk_id, size = struct.unpack("<4sI", header)

            if chunk_id == b"cue ":
                for _ in range (struct.unpack("<I", file.read(4))[0]):
                    cue_data = struct.unpack("<II4sIII", file.read(24))
                    file_cues.append(cue_data[5])
                break
            else:
                padding = size % 2
                file.seek(size + padding, 1)

    file_cues.sort()
    return file_cues

def write_wav_cues(filepath):
    """Appends a RIFF 'cue ' chunk to the WAV file if cues exist."""
    if not cues:
        return

    with open(filepath, "r+b") as f:
        f.seek(0, 2)  # Go to end of file
        
        chunk_id = b"cue "
        num_cues = len(cues)
        chunk_size = 4 + (num_cues * 24)

        f.write(chunk_id)
        f.write(struct.pack("<I", chunk_size))
        f.write(struct.pack("<I", num_cues))

        for i, sample_offset in enumerate(cues):
            # cue_id, position, data_chunk_id, chunk_start, block_start, sample_offset
            f.write(struct.pack("<II4sIII", i + 1, sample_offset, b"data", 0, 0, sample_offset))

        # Update RIFF size header
        total_size = f.tell() - 8
        f.seek(4)
        f.write(struct.pack("<I", total_size))

def plot_waveform():
    global fig_canvas, fig_ax, cursor_id

    data = np.frombuffer(audio.set_channels(1).raw_data, np.int16 if audio.sample_width == 2 else np.int8)
    data = data / (32768 if audio.sample_width == 2 else 128)
    time_axis = np.linspace(0, audio.duration_seconds, num=len(data))

    fig = Figure(figsize=(8, 3), dpi=72, facecolor="none")
    ax = fig.add_subplot(111)

    ax.set_facecolor("none")
    ax.plot(time_axis, data, color="blue")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Amplitude")
    ax.set_ylim(-1.0, 1.0)
    ax.grid(True)

    for sample in cues:
        time_sec = sample / audio.frame_rate
        ax.axvline(x=time_sec, color="orange", linestyle="--", alpha=0.8)

    for widget in waveform_frame.winfo_children():
        widget.destroy()

    canvas = FigureCanvasTkAgg(fig, master=waveform_frame)
    canvas.draw()
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(fill=tk.BOTH, expand=True)

    fig_canvas = canvas
    fig_ax = ax

    x_pixel, y_min, y_max = get_cursor_canvas_coords(0)
    cursor_id = canvas_widget.create_line(
        x_pixel, y_min, x_pixel, y_max, fill="red", width=2
    )

    canvas_widget.tag_raise(cursor_id)

def get_cursor_canvas_coords(time_sec):
    pixel_x, pixel_y_bottom = fig_ax.transData.transform((time_sec, fig_ax.get_ylim()[0]))
    _, pixel_y_top = fig_ax.transData.transform((time_sec, fig_ax.get_ylim()[1]))

    canvas_height = fig_canvas.get_tk_widget().winfo_height()
    tk_y_min = canvas_height - pixel_y_top
    tk_y_max = canvas_height - pixel_y_bottom

    return pixel_x, tk_y_min, tk_y_max

def update_cursor():
    global playing, cursor_id, fig_canvas, fig_ax, playback_start_time

    if playing and mixer.get_busy():
        elapsed = time.time() - playback_start_time

        if loop.get():
            elapsed = elapsed % audio.duration_seconds

        x_pixel, y_min, y_max = get_cursor_canvas_coords(elapsed)
        canvas_widget = fig_canvas.get_tk_widget()
        canvas_widget.coords(cursor_id, x_pixel, y_min, x_pixel, y_max)

        canvas_widget.tag_raise(cursor_id)

        window.after(17, update_cursor)
    else:
        x_pixel, y_min, y_max = get_cursor_canvas_coords(0)
        fig_canvas.get_tk_widget().coords(cursor_id, x_pixel, y_min, x_pixel, y_max)

        if playing:
            button_play()

def select_audio(path):
    if os.path.isfile(path) and check_wav_validity(path):
        global audio, sound_path, cues

        audio = AudioSegment.from_file(path)
        cues = get_wav_cues(path)

        sound_path = path
        update_status_label()
        plot_waveform()

        if playing:
            button_play()

def button_play():
    if sound_path == "": return

    global snd, playing, playback_start_time

    playing = not playing

    if playing:
        snd = mixer.Sound(buffer=audio.set_channels(2).set_frame_rate(44100).set_sample_width(2).raw_data)
        snd.play(-1 if loop.get() else 0)
        play_button.config(text="Stop", style="TButton")

        playback_start_time = time.time()
        update_cursor()
    else:
        snd.stop()
        snd = None
        play_button.config(text="Play", style="Accent.TButton")

def button_sample_rate():
    input = 0

    while input == 0:
        input = simpledialog.askinteger(
            "Change Sample Rate",
            "Note: If you want to resample instead, use Process > Resample.\nThis will re-encode your audio without affecting pitch and speed.\n\nEnter desired sample rate:",
            minvalue=1, maxvalue=UINT_32_SIZE, initialvalue=audio.frame_rate
        )

    if input != None:
        audio.frame_rate = input
        update_status_label()
        plot_waveform()

def button_select_file(event=None):
    select_audio(filedialog.askopenfilename(title="Choose WAV File", filetypes=[("PCM, ADPCM, μ-law", "*.wav")]))

def button_save(event=None):
    audio.export(sound_path, "wav")
    write_wav_cues(sound_path)

def button_save_as():
    global sound_path

    file = filedialog.asksaveasfilename(title="Export as WAV", defaultextension=".wav", filetypes=[("WAV PCM", "*.wav")])
    if file != "":
        audio.export(file, "wav")
        sound_path = file
        write_wav_cues(sound_path)
        update_status_label()

def button_resample():
    global audio
    
    input = simpledialog.askinteger("Linear Resample", "Enter desired sample rate:", minvalue=1, maxvalue=UINT_32_SIZE)
    if input != None:
        audio = audio.set_frame_rate(input)
        update_status_label()
        plot_waveform()

def button_8bit():
    global audio
    audio = audio.set_sample_width(1)
    update_status_label()
    plot_waveform()

def button_reverse():
    global audio
    audio = audio.reverse()
    plot_waveform()

def button_add_cue():
    if sound_path == "": return

    global cues
    
    mode = simpledialog.askstring("Add Cue Marker", "Enter position unit ('sec' or 'sample'):", initialvalue="sec")
    if not mode or mode.strip().lower() not in ["sec", "sample"]:
        return

    mode = mode.strip().lower()
    
    if mode == "sec":
        val = simpledialog.askfloat("Add Cue Marker", f"Enter time in seconds (0 - {audio.duration_seconds:.3f}):", maxvalue=audio.duration_seconds)
        if val is not None:
            sample_pos = int(val * audio.frame_rate)
            cues.append(sample_pos)
            cues.sort()
            plot_waveform()
    else:
        val = simpledialog.askinteger("Add Cue Marker", f"Enter sample index (0 - {int(audio.frame_count())}):", maxvalue=audio.duration_seconds * audio.frame_rate)
        if val is not None:
            cues.append(val)
            cues.sort()
            plot_waveform()

def button_delete_cue():
    if not cues:
        messagebox.showinfo("Delete Cue", "No cue markers found.")
        return

    cue_list_str = "\n".join([f"{i+1}. {s / audio.frame_rate:.3f}s ({s} samples)" for i, s in enumerate(cues)])
    idx = simpledialog.askinteger("Delete Cue Marker", f"Current Cues:\n{cue_list_str}\n\nEnter cue index to delete (1 - {len(cues)}):")

    if idx and 1 <= idx <= len(cues):
        cues.pop(idx - 1)
        plot_waveform()

def button_about_dialog():
    about = tk.Toplevel(window)
    about.title("About")
    about.geometry("250x320")
    about.resizable(False, False)
    
    about.transient(window)
    about.grab_set()
    
    title_label = tk.Label(about, text="wavMark", font=("Arial", 16, "bold"))
    title_label.pack(pady=6)

    version_label = tk.Label(about, text="Version 1.0\nMade by Maxim Naumov\n\nLibraries used:\nnumpy\npydub\nmatplotlib\npygame-ce\ntkinterdnd2\nsv-ttk\ndarkdetect\npywinstyles")
    version_label.pack()
    
    link_label = tk.Label(about, text=GITHUB_LINK, fg="blue", cursor="hand2")
    link_label.pack(pady=6)
    link_label.bind("<Button-1>", lambda _: webbrowser.open_new(GITHUB_LINK))
    
    close_button = ttk.Button(about, text="Close", command=about.destroy)
    close_button.pack(pady=6)
    pywinstyles.apply_style(about, style="mica" if darkdetect.isDark() else "normal")

def on_drop_file(event):
    select_audio(event.data.strip("{}"))

menu = tk.Menu(window, bg="black", fg="white")

file_menu = tk.Menu(menu, tearoff=False)
file_menu.add_command(label="Open...", command=button_select_file, accelerator="Ctrl+O")
file_menu.add_separator()
file_menu.add_command(label="Save", command=button_save, accelerator="Ctrl+S")
file_menu.add_command(label="Save As...", command=button_save_as)
file_menu.add_separator()
file_menu.add_command(label="About", command=button_about_dialog)
file_menu.add_command(label="Exit", command=window.quit, accelerator="Alt+F4")

edit_menu = tk.Menu(menu, tearoff=False)
edit_menu.add_command(label="Set Sample Rate...", command=button_sample_rate)

process_menu = tk.Menu(menu, tearoff=False)
process_menu.add_command(label="Reverse",command=button_reverse)
process_menu.add_command(label="Linear Resample...",command=button_resample)
process_menu.add_command(label="Convert to 8-bit...", command=button_8bit)

cue_menu = tk.Menu(menu, tearoff=False)
cue_menu.add_command(label="Add Cue...", command=button_add_cue)
cue_menu.add_command(label="Delete Cue...", command=button_delete_cue)

menu.add_cascade(label="File", menu=file_menu)
menu.add_cascade(label="Edit", menu=edit_menu)
menu.add_cascade(label="Process", menu=process_menu)
menu.add_cascade(label="Cues", menu=cue_menu)

waveform_frame = tk.Frame(window)
waveform_frame.pack(fill=tk.BOTH, expand=True)

control_frame = tk.Frame(window)
control_frame.pack()

play_button = ttk.Button(control_frame, text="Play", command=button_play,style="Accent.TButton")
sample_rate_button = ttk.Button(control_frame, text="Set Sample Rate...", command=button_sample_rate)
resample_button = ttk.Menubutton(control_frame, text="Process...", menu=process_menu)
select_file_button = ttk.Button(control_frame, text="Select File...", command=button_select_file)
sample_rate_label = tk.Label(window, text="Please select a file")
looping_toggle = ttk.Checkbutton(window, text="Loop", variable=loop)

play_button.grid(row=0, column=0,padx=8)
sample_rate_button.grid(row=0, column=1,padx=8)
resample_button.grid(row=0, column=2,padx=8)
select_file_button.grid(row=0, column=3,padx=8)
sample_rate_label.pack()
looping_toggle.pack()

update_status_label()
plot_waveform()

mixer.init()

window.config(menu=menu)
window.bind("<Control-s>", button_save)
window.bind("<Control-o>", button_select_file)

window.drop_target_register(DND_FILES)
window.dnd_bind("<<Drop>>", on_drop_file)

if sys.platform == "win32":
    import sv_ttk
    import darkdetect
    import pywinstyles

    sv_ttk.set_theme(darkdetect.theme())
    pywinstyles.apply_style(window, style="mica" if darkdetect.isDark() else "normal")

window.mainloop()
