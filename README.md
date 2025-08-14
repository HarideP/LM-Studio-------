## LM Studio Directory Migration & Junction Tool

English | [中文](README_zh.md)

> **Please consider giving this project a Star before use. Thank you for your support! 🌟**

This project provides a Windows GUI/CLI tool to move LM Studio’s models and data directory from its default location to another drive, and create a directory junction at the original path. After migration, LM Studio can still access the content via the original path, saving space on the system drive without affecting user experience.

### What you can do with it
- Move `%USERPROFILE%\.lmstudio` to another drive (default suggestion: `D:\LMstudio_AIModels`).
- After copying, automatically remove the source directory and create a junction at the original path pointing to the target.
- If the target directory already exists, choose to delete and overwrite, or skip copying and only create the junction.
- Offer both a GUI and a CLI mode.
- Prefer `robocopy` for fast copying; when unavailable, fall back to Python copying.
- Pre-execution reminders and checks: whether running as Administrator, and whether LM Studio is fully closed.

### Requirements
- Windows only (Windows 10/11).
- Python 3.10+ (Tkinter is typically included on Windows).

### Files
- `move_lmstudio.py`: Main tool (supports both GUI and CLI).
- `movefile.bat`: Legacy batch script (no longer necessary).

### Important notes before use
1) Run as Administrator (creating a directory junction requires elevated privileges or Developer Mode).
2) Make sure LM Studio is fully closed (including tray and background processes).
3) Consider backing up important data.

### Quick start (GUI recommended)
1. Open PowerShell or CMD as Administrator.
2. Navigate to the project directory.
3. Run:
```bash
python move_lmstudio.py --gui
```
4. In the GUI:
   - Set Source (default: `%USERPROFILE%\.lmstudio`).
   - Set Target (default: `D:\LMstudio_AIModels`).
   - Optional:
     - "Delete and overwrite if target exists".
     - "Skip copy, only create junction at source path".
   - Click "View Info" to inspect directory stats.
   - Click "Start" and confirm prompts.

### CLI mode
1. Open PowerShell or CMD as Administrator.
2. Run:
```bash
python move_lmstudio.py --cli
```
3. Follow the prompts:
   - Enter/confirm source and target paths.
   - If the target exists, choose from re-enter, delete & overwrite copy, link-only, or exit.
   - Confirm that you’re running as Administrator and LM Studio has been fully closed.

### Defaults
- Source: `%USERPROFILE%\.lmstudio`
- Target: `D:\LMstudio_AIModels`
(Both can be customized in GUI or CLI.)

### Operations
- Copy: Fully copy the source directory to the target (`robocopy` preferred; if unavailable, Python fallback).
- Remove source: After a successful copy, remove the source directory (free up system drive).
- Create junction: Create a junction at the original source path pointing to the target, so LM Studio keeps using the original path.

### FAQ / Troubleshooting
- Cannot create junction / permission errors:
  - Run the terminal as Administrator, or enable "Developer Mode".
  - Ensure the target path is accessible, and the source path is available for junction creation after deletion.
- Target directory already exists:
  - Choose "Delete & overwrite copy" in CLI, or check the corresponding option in GUI.
  - Or choose "Link-only" to use the existing target without copying.
- Copy is slow:
  - Ensure `robocopy` is available (bundled with Windows).
  - Python fallback copying is expected to be slower.
- LM Studio still holds files:
  - Fully close LM Studio including tray and background processes, then retry.

### Safety
- When using "Delete & overwrite", the specified target directory will be removed first. Double-check paths.
- Back up important data beforehand.

### Revert / Undo
- To revert, remove the junction at the source path and copy data back; or set the target back to the original path in the tool and run again.

### License
This tool is provided as-is, without warranties or liabilities.


