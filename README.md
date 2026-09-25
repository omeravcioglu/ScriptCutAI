# ScriptCutAI

AI-powered video editing assistant that automatically removes mistakes, retakes, and off-script talking from script-based recordings.

## What It Does

- Transcribes your video using AI (Whisper)
- Compares what was said to your script
- Finds the best take for each sentence
- Removes mistakes, pauses, and off-script talking
- Applies cuts directly in Premiere Pro

## How It Works

```
Premiere Pro panel (CEP: HTML/JS + ExtendScript)
      │  1. picks the clip on the active timeline, sends its path + your script
      ▼
Local FastAPI server (Python, http://127.0.0.1:8000)
      │  2. Whisper transcribes the audio with word-level timestamps
      │  3. Alignment finds every attempt at every script sentence
      │  4. Cut engine picks the best take per sentence, in script order,
      │     and trims long silences inside kept takes
      ▼
Edit list (KEEP / REMOVE segments with timings)
      │  5. ExtendScript razor-cuts the sequence at segment boundaries and
      │     ripple-deletes the REMOVE parts (or just adds markers, as a fallback)
      ▼
Clean, script-ordered edit on the timeline
```

- **Transcription** (`backend/app/services/transcription.py`): OpenAI **Whisper** runs locally on the CPU (default model `base`; `tiny` through `large` are selectable). It returns word-level timestamps. The model stays loaded between runs and can be unloaded on demand.
- **Alignment** (`backend/app/services/alignment.py`):
  - The script is split into sentences, and the text is normalized.
  - The transcript is scanned for attempts at each sentence using **Levenshtein** similarity on key words.
  - Filler words and off-script talking are recognized, so retakes, false starts and chatter can be told apart.
- **Cut decisions** (`backend/app/services/cut_detector.py`):
  - Selects the best take for every sentence while enforcing the script's order.
  - Generates KEEP/REMOVE segments with tight boundaries, merges neighbours and removes long internal silences.
  - Reports how much time is kept and how much removed.
- **Premiere integration** (`premiere-extension/jsx/premiere.jsx`):
  - Reads the active clip.
  - Converts seconds to Premiere ticks.
  - Applies cuts with razor + extract through the QE DOM, with a marker-only fallback plus marker clearing and seeking helpers.

## Tech Stack

| Part | Technology |
|---|---|
| Backend | Python 3.12, **FastAPI** + Uvicorn, Pydantic |
| Speech-to-text | **OpenAI Whisper** (local, PyTorch CPU build), FFmpeg |
| Text matching | python-Levenshtein, RapidFuzz |
| Editor panel | Adobe **CEP** extension (HTML/CSS/JS, CSInterface) + **ExtendScript** for Premiere Pro (host `PPRO` 13.0+) |
| Setup | One-click `INSTALL.bat` → `setup-new-computer.ps1` (installs Python if needed, creates the venv, installs dependencies, installs and enables the extension) |

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Server status (the panel shows "Server offline" when this fails) |
| `POST` | `/api/transcribe` | Transcribe a video file with word-level timestamps |
| `POST` | `/api/analyze` | Full pipeline: transcribe, align to the script, return the edit segments and statistics |
| `GET` | `/api/edits/premiere-format` | Describes the edit-list format the panel consumes |
| `POST` | `/api/unload-model` | Free the Whisper model from memory |

Interactive API docs are served by FastAPI at `http://127.0.0.1:8000/docs` while the server runs.

## Requirements

- Windows 10/11
- Python 3.12
- Adobe Premiere Pro (CC 2019 or later)
- ~2GB disk space for AI models

## Installation (One-Time Setup)

### Step 1: Install Python 3.12

Download from: https://www.python.org/downloads/
- Check "Add Python to PATH" during installation

### Step 2: Install FFmpeg

Open PowerShell and run:
```powershell
winget install Gyan.FFmpeg
```

### Step 3: Set Up the Backend

Open PowerShell in the ScriptCutAI folder and run:
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 4: Install the Premiere Extension

Run as Administrator:
```powershell
.\install-extension.ps1
```

Or manually:
1. Copy the `premiere-extension` folder to:
   `C:\Users\YOUR_USERNAME\AppData\Roaming\Adobe\CEP\extensions\com.scriptcutai.panel`

2. Enable unsigned extensions (run in PowerShell):
```powershell
reg add "HKCU\Software\Adobe\CSXS.11" /v PlayerDebugMode /t REG_SZ /d 1 /f
```

## Usage

### Step 1: Start the Server

Double-click `start-server.bat` or run:
```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Step 2: Open Premiere Pro

1. Open your project with the video
2. Go to **Window → Extensions → ScriptCutAI**

### Step 3: Analyze and Cut

1. Click "Get from Timeline" to select your video
2. Paste your script text
3. Click "Analyze Video" (wait for transcription)
4. Click "Preview Cuts" to review
5. Click "Apply Cuts to Timeline" to execute

## Folder Structure

```
ScriptCutAI/
├── backend/              # Python AI server
│   ├── app/              # Application code
│   ├── venv/             # Python environment (created by setup, not in the repo)
│   └── requirements.txt  # Dependencies (pinned; uses PyTorch's CPU wheel index)
├── premiere-extension/   # Premiere Pro panel
├── start-server.bat      # Quick start script
├── install-extension.ps1 # Extension installer
└── README.md             # This file
```

## Troubleshooting

### "Server offline" in the panel
- Make sure you started the server first
- Check if port 8000 is available

### Extension not showing in Premiere
- Run the install script as Administrator
- Restart Premiere Pro completely

### Analysis takes too long
- Use "tiny" or "base" Whisper model for faster results
- "medium" is more accurate but slower

### Cuts not applying
- Make sure a sequence is active
- Try the "Add Markers" fallback option

## Tips

- Keep the server running while editing
- Use "base" model for good balance of speed/accuracy
- Review cuts with "Preview" before applying
- Save your project before applying cuts!


## Repository Notes

Changes made when preparing this repository (the working copy on my PC is unchanged):

- `backend/requirements.txt` was converted from UTF-16 to UTF-8 so GitHub and every tool can read it. It now starts with `--extra-index-url https://download.pytorch.org/whl/cpu`, because the pinned `torch==2.9.1+cpu` builds are only published on PyTorch's own index. Without that line, `pip install -r requirements.txt` fails on a fresh machine.
- `setup-new-computer.ps1` no longer hides pip errors (`2>$null`). If installing dependencies fails, it now stops and says so, instead of reporting success.
- `install-extension.ps1` prints the backend path relative to where the script lives, instead of a hardcoded personal folder.
- The Python virtual environment (`backend/venv`, about 1 GB) is not stored in git; setup recreates it.

Copyright © Omer Avcioglu (McHunter Studio). **All rights reserved.** Viewing only; see [LICENSE](LICENSE).
