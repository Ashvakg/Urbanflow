# Dead Letter Queue Strategy

## Purpose
Store records that fail schema validation for investigation and recovery.

## Storage Location
s3://urbanflow-dlq/
├── year=2024/
│   └── month=01/
│       └── day=15/
│           └── failed_records_20240115_083045.parquet

## Schema
Original record columns + metadata:
- _error_type: string (schema_mismatch, type_error, null_violation, etc.)
- _error_message: string (details about what failed)
- _failed_at: timestamp (when validation failed)
- _source_file: string (which input file)
- _original_record: string (raw CSV line, for debugging)

## Retention Policy
- Keep for 30 days
- Alert if DLQ > 1% of total records
- Weekly review of patterns

## Recovery Process
1. Identify error pattern in DLQ
2. Fix source system OR update schema
3. Reprocess DLQ records if needed