# Delta for folder-scanner

## ADDED Requirements

### R6: Watchdog Incremental Detection

The system MUST monitor root directories via watchdog observer for filesystem events after observer is started. On each event, the system MUST re-scan the affected subtree and update the in-memory `ScanResult` with thread-safe access.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| File created | new file appears in a known facturador folder | watchdog fires `on_created` | affected subtree re-scanned; `ScanResult` updated atomically |
| File modified | existing file content changes | watchdog fires `on_modified` | affected subtree re-scanned; `ScanResult` updated |
| File deleted | existing file removed from subfolder | watchdog fires `on_deleted` | affected subtree re-scanned; facturador removed from `ScanResult` if empty |
| File moved | file moved from one subdir to another | watchdog fires `on_moved` | source and destination subtrees both re-scanned; `ScanResult` updated |

### R7: Watchdog Health Check

On subsequent `POST /scan` calls (after the first), the system MUST verify the watchdog observer is alive. An alive observer SHALL return a monitoring status response with no scan data. A dead observer SHALL trigger a fallback full scan.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Watchdog alive | observer thread running and healthy | `POST /scan` (2nd+) | response `status=monitoring`, code 200, no scan data |
| Watchdog dead | observer thread stopped unexpectedly | `POST /scan` (2nd+) | fallback full scan triggered; result returned as full scan |

## MODIFIED Requirements

### R1: Scan Configured Roots

The system MUST switch behavior based on call sequence: the first `POST /scan` performs a full scan of all configured roots and MUST start the watchdog observer as a daemon thread. Subsequent `POST /scan` calls SHALL perform a health check of the watchdog observer and MUST NOT re-scan unless the observer is dead.

(Previously: every scan call did a full O(n) scan of all configured roots regardless of prior calls)

| Scenario | Given | When | Then |
|----------|-------|------|------|
| First call — full scan | watchdog not yet started | `POST /scan` | full scan runs; all subdirs enumerated; observer started in daemon thread |
| Single root (unchanged) | one root dir with 3 facturadores | scan runs | all 3 subdirs returned |
| Multiple roots (unchanged) | 2 root dirs configured | scan runs | subdirs from both roots returned |
| Empty root (unchanged) | root dir contains no subfolders | scan runs | empty list returned |
| Subsequent call — health check | watchdog observer alive | `POST /scan` (2nd+) | no re-scan; response `status=monitoring`, code 200 |

## MODIFIED Non-Functional Requirements

- The in-memory `ScanResult` MUST be protected by a synchronization primitive (e.g. `threading.Lock`) for thread-safe concurrent access from watchdog and Flask request threads.
