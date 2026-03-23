"""
Configuration constants for the OS2200 test package automation workflow.
"""

# Polling settings
POLLING_INTERVAL_SECONDS = 15
POLLING_TIMEOUT_SECONDS = 300  # 5-minute default timeout

# Retry settings
RETRY_COUNT = 3
RETRY_BACKOFF_BASE = 2  # Exponential backoff base (seconds)

# File management
FILE_RETENTION_DAYS = 10
TEMP_FOLDER_NAME = "testrepo_temp"
RESULTS_FOLDER_NAME = "testrepo_results"

# FTP defaults
FTP_PORT = 21
FTP_TIMEOUT_SECONDS = 30

# TELNET defaults
TELNET_PORT = 23
TELNET_TIMEOUT_SECONDS = 30
TELNET_READ_TIMEOUT = 5

# Logging
LOG_FILE_NAME = "testrepo.log"

# SSG script template
SSG_SCRIPT_TEMPLATE = """\
@SSG
SGS.
@EOF
SKEL
*MESSAGE SCRIPT IS STARTED. TEST PASS
"""
