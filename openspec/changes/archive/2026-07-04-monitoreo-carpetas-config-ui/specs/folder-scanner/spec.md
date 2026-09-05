# Delta for folder-scanner

## MODIFIED Requirements

### R1: Scan Configured Roots

The system MUST read root directories from the **folder-scanner-config store** (instead of directly from env var) and enumerate first-level subdirectories as facturador folders.
(Previously: read directly from env var `MONITOREO_CARPETAS_ROOTS`)

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Single root | store returns one root dir with 3 facturadores | scan runs | all 3 subdirs returned |
| Multiple roots | store returns 2 root dirs | scan runs | subdirs from both roots returned |
| Empty root | store returns empty list | scan runs | empty result returned (no error) |
| Store corrupt | store falls back to env var with 1 root | scan runs | that 1 root is scanned |
