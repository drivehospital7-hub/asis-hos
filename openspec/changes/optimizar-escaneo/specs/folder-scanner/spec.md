# Delta for Folder Scanner

## MODIFIED Requirements

### R1: Scan Configured Roots

The system MUST scan all roots concurrently via `ThreadPoolExecutor` with `min(MAX_CONCURRENT_SCANS, len(roots))` workers. Each root SHALL timeout at `SCAN_TIMEOUT_PER_FACTURADOR` seconds.

Within a root, the scanner MUST walk to invoice-folder depth (~4 levels) and identify folders whose names start with "FEV" or "CAP" (case-insensitive). For each match, it MUST verify the folder is non-empty via `os.listdir() > 0`. Non-empty matches produce an `InvoiceRecord` with `invoice_code = folder_name`.

The scanner SHALL NOT enumerate individual PDF files within invoice folders.
(Previously: Sequential root scanning with os.walk() enumerating individual PDF files at any depth.)

#### Scenario: Single root with invoice folders

- GIVEN one root dir containing FEV12345 (non-empty), FEV67890 (non-empty), CAP1_AB123 (non-empty)
- WHEN scan runs
- THEN 3 InvoiceRecords returned with matching folder names as invoice_code

#### Scenario: Multiple roots in parallel

- GIVEN 2 configured root dirs
- WHEN scan runs
- THEN both roots scanned concurrently; invoice folders from both returned

#### Scenario: Empty invoice folder skipped

- GIVEN invoice folder FEV99999 exists but os.listdir() returns empty
- WHEN scan runs
- THEN folder flagged as empty; no InvoiceRecord created for it

#### Scenario: Non-matching folders ignored

- GIVEN root contains folders CRC_01, HAU_02, notas
- WHEN scan runs
- THEN none produce InvoiceRecords (startswith pre-filter excludes them)

### R3: Structural Tolerance

The system SHOULD tolerate individual root failures during parallel scan. Each root thread SHALL handle errors independently. Root timeouts SHALL be caught via `future.result(timeout=SCAN_TIMEOUT_PER_FACTURADOR)`. All errors SHALL be logged with root path and exception message.
(Previously: Sequential root scanning with same tolerance for inaccessible roots.)

#### Scenario: Root unreachable

- GIVEN root `\\server\billing` has network error
- WHEN scan_all runs in parallel
- THEN error logged for that root; other roots scanned normally

#### Scenario: Root timeout in parallel

- GIVEN one root hangs beyond timeout
- WHEN scan_all runs
- THEN timeout logged; remaining roots unaffected

#### Scenario: Permission denied

- GIVEN no read access to one root
- WHEN scan runs
- THEN permission error logged; remaining roots scanned

## ADDED Requirements

### R6: Parallel Root Scanning

The system MUST scan configured roots concurrently using `concurrent.futures.ThreadPoolExecutor`. Worker count SHALL be `min(MAX_CONCURRENT_SCANS, len(roots))`. Each future SHALL be collected with a 30-second timeout. Results SHALL be aggregated sequentially after all futures complete. No shared mutable state between threads.

#### Scenario: All roots healthy

- GIVEN 3 configured roots
- WHEN scan_all runs
- THEN 3 threads launched; results aggregated from all

#### Scenario: One root times out

- GIVEN 3 roots, one hangs
- WHEN scan_all runs
- THEN 2 roots return invoices; timeout root logged as error
