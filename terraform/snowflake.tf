# Create Database
resource "snowflake_database" "urbanflow_db" {
  name    = "URBANFLOW_DB"
  comment = "Database for UrbanFlow taxi data pipeline"
}

# FinOps: Resource Monitor
resource "snowflake_resource_monitor" "urbanflow_monitor" {
  name         = "URBANFLOW_COST_MONITOR"
  credit_quota = 10

  frequency       = "MONTHLY"
  start_timestamp = "2026-02-05 18:00"

  notify_triggers = [75]

  # FIX: singular attribute names
  suspend_trigger           = 90
  suspend_immediate_trigger = 100

  notify_users = [var.snowflake_user]
}

# Warehouse (with cost controls)
resource "snowflake_warehouse" "urbanflow_wh" {
  name           = var.snowflake_warehouse
  warehouse_size = "XSMALL"

  auto_suspend = 60
  auto_resume  = true

  resource_monitor = snowflake_resource_monitor.urbanflow_monitor.name

  comment = "Warehouse for UrbanFlow data processing (with cost controls)"
}

# Schemas
resource "snowflake_schema" "raw" {
  database = snowflake_database.urbanflow_db.name
  name     = "RAW"
  comment  = "Raw zone tables"
}

resource "snowflake_schema" "analytics" {
  database = snowflake_database.urbanflow_db.name
  name     = "ANALYTICS"
  comment  = "Analytics tables (dbt output)"
}

resource "snowflake_schema" "silver" {
  database = snowflake_database.urbanflow_db.name
  name     = "SILVER"
  comment  = "Silver zone tables (s3 output)"
}

resource "snowflake_schema" "gold" {
  database = snowflake_database.urbanflow_db.name
  name     = "GOLD"
  comment  = "Gold zone tables (dbt output)"
}

resource "snowflake_storage_integration" "s3_int" {
  name    = "S3_INTEGRATION"
  type    = "EXTERNAL_STAGE"
  enabled = true

  storage_provider         = "S3"
  storage_aws_role_arn     = aws_iam_role.snowflake_role.arn
  storage_allowed_locations = ["s3://urbanflow-silver-dev/"]
}