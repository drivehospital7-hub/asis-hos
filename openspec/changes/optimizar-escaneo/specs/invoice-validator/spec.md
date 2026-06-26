# Delta for Invoice Validator

## MODIFIED Requirements

### R1: FEV Pattern Validation

The system MUST match invoice folder names against the FEV regex pattern (case-insensitive). Valid SHALL mean the folder name consists only of the FEV pattern. Validation is applied to folder names, not PDF filenames. The regex patterns remain unchanged.
(Previously: Validated PDF filenames against FEV pattern.)

#### Scenario: Valid FEV folder

- GIVEN folder named FEV12345
- WHEN validation runs
- THEN type = FEV, valid = true

#### Scenario: FEV with INV_ prefix

- GIVEN folder named INV_FEV789
- WHEN validation runs
- THEN type = FEV, valid = true

#### Scenario: Invalid FEV folder

- GIVEN folder named FEV_ABC
- WHEN validation runs
- THEN type = FEV, valid = false

### R2: CAP Pattern Validation

The system MUST match invoice folder names against the CAP regex pattern (case-insensitive). Valid SHALL mean the folder name consists only of the CAP pattern. Validation is applied to folder names, not PDF filenames.
(Previously: Validated PDF filenames against CAP pattern.)

#### Scenario: Valid CAP folder

- GIVEN folder named CAP1234_ABC567
- WHEN validation runs
- THEN type = CAP, valid = true

#### Scenario: CAP with INV_ prefix

- GIVEN folder named INV_CAP567_DEF890
- WHEN validation runs
- THEN type = CAP, valid = true

#### Scenario: Invalid CAP folder

- GIVEN folder named CAP_ABC
- WHEN validation runs
- THEN type = CAP, valid = false

### R3: Unknown Pattern

The system MUST mark folder names matching neither FEV nor CAP as type Unknown.
(Previously: Applied to filenames; scenario for wrong-extension files removed since folders have no extensions.)

#### Scenario: No match

- GIVEN folder named factura_generica
- WHEN validation runs
- THEN type = Unknown, valid = false

#### Scenario: Non-invoice folder

- GIVEN folder named CRC_12345
- WHEN validation runs
- THEN type = Unknown, valid = false

### R4: Empty Folder Detection

The system MUST flag any invoice folder (name matches FEV*/CAP*) that is empty at scan time. Empty SHALL mean `os.listdir()` returns zero entries. The check operates at the invoice-folder level, not the facturador level. Any non-empty folder (regardless of file types) SHALL NOT be flagged.
(Previously: Checked facturador subfolders for presence of .pdf files only.)

#### Scenario: Truly empty folder

- GIVEN invoice folder FEV12345 with os.listdir() returning empty
- WHEN scan runs
- THEN folder in empty_folders list

#### Scenario: Non-empty with PDFs

- GIVEN invoice folder FEV67890 contains 3 .pdf files
- WHEN scan runs
- THEN not in empty_folders list

#### Scenario: Non-empty with only non-PDF files

- GIVEN invoice folder CAP1_AB123 contains only .txt and .log files
- WHEN scan runs
- THEN not in empty_folders list (folder is non-empty regardless of file type)
