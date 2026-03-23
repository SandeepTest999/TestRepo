# OS2200 Test Package Automation

A modular Python application that automates the execution of OS2200 test packages by coordinating FTP uploads, TELNET script execution, SSG script generation, result polling, and automated comparison.

---

## Project Structure

```
TestRepo/
├── README.md
├── requirements.txt
├── main.py                    # Entry point / workflow orchestrator
├── config.py                  # Configuration constants
├── credentials_manager.py     # Session-cached FTP/TELNET credentials
├── ftp_handler.py             # FTP upload/download operations
├── telnet_handler.py          # TELNET connection and script execution
├── ssg_generator.py           # SSG script generation and review
├── pollers.py                 # Local results folder polling
├── comparator.py              # Comparison script trigger and management
├── workflow_manager.py        # Workflow orchestration with step tracking
├── progress_indicator.py      # Visual progress/status display
├── file_manager.py            # Temp file storage, cleanup, retention
├── utils.py                   # Shared utility functions and exceptions
└── tests/
    ├── __init__.py
    ├── test_ftp_handler.py
    ├── test_telnet_handler.py
    ├── test_ssg_generator.py
    ├── test_pollers.py
    └── test_comparator.py
```

---

## Module Descriptions

| Module | Purpose |
|---|---|
| `config.py` | All configurable constants (polling interval, retry count, retention, etc.) |
| `utils.py` | Logging setup, shared exception classes |
| `credentials_manager.py` | Prompts once for FTP credentials and caches them in memory for the session |
| `file_manager.py` | Creates/manages temp and results folders; cleans up files older than 10 days |
| `ftp_handler.py` | FTP upload and download with exponential-backoff retry |
| `telnet_handler.py` | TELNET connection to OS2200 with retry on failure |
| `ssg_generator.py` | Generates the SSG test script, lets the user review/edit it, then saves to temp |
| `pollers.py` | Polls the results folder every 15 seconds; auto-triggers comparison when files appear |
| `comparator.py` | Runs comparison logic on result files; placeholder ready for real implementation |
| `progress_indicator.py` | Terminal progress display with emoji status icons for each step |
| `workflow_manager.py` | Coordinates all steps; supports pause, resume, retry, and graceful failure handling |
| `main.py` | CLI entry point; parses arguments and drives the workflow |

---

## Installation

```bash
# Clone the repository
git clone https://github.com/SandeepTest999/TestRepo.git
cd TestRepo

# (Recommended) Create a virtual environment
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate.bat     # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## How to Run

```bash
python main.py [OPTIONS]
```

### Options

| Option | Default | Description |
|---|---|---|
| `--telnet-host HOST` | `localhost` | Hostname / IP of the OS2200 TELNET target |
| `--telnet-port PORT` | `23` | TELNET port |
| `--ftp-upload-path PATH` | `/upload/ssg_script.txt` | Remote FTP path for SSG script upload |
| `--ftp-results-path PATH` | `/results/results_archive.tar` | Remote FTP path for results download |
| `--log-level LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

### Example

```bash
python main.py --telnet-host os2200.example.com --log-level DEBUG
```

---

## Workflow Steps

The application executes the following steps in sequence:

| # | Step | Description |
|---|---|---|
| 1 | **Collect FTP credentials** | Prompts the user once; cached for the session |
| 2 | **Generate SSG script (user review)** | Generates the script locally; user can accept, edit, or replace |
| 3 | **FTP upload** | Connects to FTP and uploads the reviewed SSG script |
| 4 | **TELNET execution** | Sends the approved script to OS2200 via TELNET |
| 5 | **Poll for results** | Polls the local results folder every 15 s until files appear |
| 6 | **FTP results retrieval** | Downloads results from the FTP server |
| 7 | **Run comparison** | Automatically compares results; displays "Test Package Completed" |

Each step displays one of the following statuses:

| Icon | Status |
|---|---|
| ⏳ | Pending |
| 🔄 | Running |
| ✅ | Completed |
| ❌ | Failed |
| ⏸️  | Paused |

If any step fails the workflow pauses with a descriptive error message and offers a retry option.

---

## Configuration Options (`config.py`)

| Constant | Default | Description |
|---|---|---|
| `POLLING_INTERVAL_SECONDS` | `15` | How often to check the results folder |
| `POLLING_TIMEOUT_SECONDS` | `300` | Maximum poll time before timeout error |
| `RETRY_COUNT` | `3` | Maximum retry attempts for FTP/TELNET failures |
| `RETRY_BACKOFF_BASE` | `2` | Exponential backoff base (seconds) |
| `FILE_RETENTION_DAYS` | `10` | Days before temp files are cleaned up |
| `TEMP_FOLDER_NAME` | `testrepo_temp` | Name of the temp folder (inside `~`) |
| `RESULTS_FOLDER_NAME` | `testrepo_results` | Name of the results folder (inside `~`) |

---

## Running Tests

```bash
pytest tests/
```

---

## Generated SSG Script Format

```
@SSG
SGS.
@EOF
SKEL
*MESSAGE SCRIPT IS STARTED. TEST PASS
```

The user is shown this script before it is uploaded and may accept it as-is, open it in an editor, or type a replacement inline.

---

## File Storage

- Temp files (SSG scripts, logs) are stored in `~/testrepo_temp/` — no admin rights required.
- Results are stored in `~/testRepo_results/` — no admin rights required.
- Files in the temp folder older than **10 days** are automatically deleted at application start.
