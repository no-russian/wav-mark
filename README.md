![wavMark Logo](github-logo-light.png#gh-light-mode-only)
![wavMark Logo](github-logo-dark.png#gh-dark-mode-only)
# wavMark

**wavMark** is a versatile, lightweight digital audio utility designed as a "Swiss-Army knife" for inspecting, editing, and manipulating Wave (`.wav`) audio files. Built with a clean desktop interface, it enables real-time waveform visualization, audio processing, dynamic speed and pitch manipulation, and metadata management.

---

## Key Features

* **Interactive Waveform Visualization:** Displays real-time audio amplitude plots and syncs a moving playback cursor during playback.
* **Cue Marker Management:** Add, view, and delete non-destructive cue markers specified by seconds or exact sample position.
* **Sample Rate & Pitch Adjustment:** Shift playback speed and pitch dynamically by modifying sample rates on the fly.
* **Linear Resampling:** Resample audio to different sample rates without altering pitch or tempo.
* **Bit Depth Conversion:** Downsample audio to 8-bit resolution.
* **Channel Reversal:** Quickly reverse audio tracks.
* **RIFF Cue Metadata Export:** Export updated audio files along with embedded RIFF `cue ` chunks directly back into standard `.wav` containers.
* **Drag-and-Drop Support:** Drag audio files directly into the window for immediate inspection and editing.
---

## Usage
1. **Open File:** Drag and drop a `.wav` file into the window or click **Select File...**.
2. **Playback:** Click **Play** to start audio playback and view the tracking cursor in real time. Toggle **Loop** to repeat playback continuously.
3. **Edit Sample Rate:** Click **Set Sample Rate...** to alter speed and pitch.
4. **Process Audio:** Use the **Process** menu to reverse audio, convert to 8-bit depth, or perform linear resampling.
5. **Manage Markers:** Use the **Cues** menu to add or delete cue markers by second or sample index.
6. **Save Work:** Click **File > Save** (`Ctrl+S`) or **Save As...** to export the updated audio and RIFF metadata.