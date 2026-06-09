# db-operations Specification

## Purpose

Operational requirements for two procedures: full database reset (drop + recreate all tables in FK-safe order) and guided step-by-step reimportation of data via existing `/api/import/` endpoints. These are maintenance utilities, not system capabilities.

## Requirements

### Requirement: Safe Full Database Reset

The reset script MUST drop all tables in reverse foreign-key dependency order, MUST recreate them (SQLAlchemy metadata + `procedimientos` via psycopg2 DDL), MUST execute post-create migrations, and MUST run the user seed.

The script SHALL prompt for confirmation before executing any DROP. Each phase MUST be logged to stdout with timestamps.

#### Scenario: Successful reset cycle

- GIVEN the PostgreSQL database `asis_hos` is accessible via `DB_CONFIG`
- WHEN the user runs `python scripts/reset_db.py` and confirms
- THEN all tables are dropped in reverse FK order
- AND SQLAlchemy tables are recreated via `Base.metadata.create_all()`
- AND the `procedimientos` table is created via psycopg2 DDL
- AND post-create SQL migrations execute
- AND admin + odonto + urgencias users seed successfully

#### Scenario: User cancels at confirmation

- GIVEN the reset script is running
- WHEN the user answers "no" at the confirmation prompt
- THEN zero DROP statements execute
- AND the script exits with code 0

#### Scenario: DROP fails mid-execution

- GIVEN a table cannot be dropped (e.g., active connection)
- WHEN the DROP statement fails
- THEN the script MUST log the error and abort with non-zero exit
- AND the database remains in the state at time of failure

### Requirement: Guided Reimportation Flow

The reimport guide SHALL present steps in FK-safe order, SHALL accept CSV file paths (with optional Excel-to-CSV conversion), SHALL reuse existing `/api/import/` endpoints, and SHALL allow skipping any step.

The import order SHALL be: (1) users — seed, no file; (2) eps_contratado; (3) procedimiento; (4) nota_hoja; (5) procedimientos; (6) notas_tecnicas; (7) eps_nota.

#### Scenario: Full reimport cycle

- GIVEN the database is reset and the Flask server is running
- WHEN the user provides CSV files for all six data steps
- THEN each file is uploaded to its corresponding `/api/import/` endpoint
- AND every endpoint returns HTTP 200
- AND all tables contain the expected records

#### Scenario: Step skipped

- GIVEN the user does NOT have an `eps_contratado` file
- WHEN the guide reaches that step
- THEN the user types "skip" and the guide proceeds to the next step
- AND `eps_contratado` table remains empty

#### Scenario: Excel file provided

- GIVEN the user provides an `.xlsx` file for `nota_hoja`
- WHEN the guide receives it
- THEN it SHALL convert to CSV before calling the endpoint
- AND the import proceeds identically to a native CSV upload

#### Scenario: Endpoint returns error

- GIVEN the uploaded CSV has invalid data
- WHEN the endpoint returns HTTP 4xx/5xx
- THEN the guide MUST display the error to the user
- AND MUST pause until the user decides to retry or skip

### Requirement: Logging and Audit Trail

Every operation in reset and reimport SHALL be timestamped and written to stdout for failure diagnosis.

#### Scenario: Reset produces structured log

- GIVEN the reset script runs to completion
- WHEN it drops tables
- THEN each DROP is logged as `[DROP] table_name`
- AND each CREATE as `[CREATE] table_name`
- AND seeding as `[SEED] users — N created`
- AND a final `[DONE]` message confirms success
