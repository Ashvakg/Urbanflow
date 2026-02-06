# ==========================================
# 1. STORAGE LAYER (S3 Buckets)
# ==========================================

# Bronze Layer
resource "aws_s3_bucket" "bronze" {
  bucket = "${var.project_name}-bronze-${var.environment}"
  tags = {
    Layer       = "Bronze"
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "bronze_versioning" {
  bucket = aws_s3_bucket.bronze.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "bronze_lifecycle" {
  bucket = aws_s3_bucket.bronze.id
  rule {
    id     = "transition_to_glacier"
    status = "Enabled"
    filter { prefix = "" }
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

# Silver Layer
resource "aws_s3_bucket" "silver" {
  bucket = "${var.project_name}-silver-${var.environment}" 
  tags = {
    Layer       = "Silver"
    Project     = var.project_name
    Environment = var.environment
  }
}

# Gold Layer
resource "aws_s3_bucket" "gold" {
  bucket = "${var.project_name}-gold-${var.environment}"
  tags = {
    Layer       = "Gold"
    Project     = var.project_name
    Environment = var.environment
  }
}

# DLQ Layer
resource "aws_s3_bucket" "dlq" {
  bucket = "${var.project_name}-dlq-${var.environment}"
  tags = {
    Layer       = "DLQ"
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "dlq_lifecycle" {
  bucket = aws_s3_bucket.dlq.id
  rule {
    id     = "transition_to_glacier"
    status = "Enabled"
    filter { prefix = "" }
    transition {
      days          = 30
      storage_class = "GLACIER"
    }
  }
}

# ==========================================
# 2. AWS IAM LAYER (Security)
# ==========================================

resource "aws_iam_role" "snowflake_role" {
  name = "${var.project_name}-snowflake-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          # PASTE YOUR 'STORAGE_AWS_IAM_USER_ARN' HERE
          AWS = "arn:aws:iam::115005006440:user/j2nf1000-s" 
        }
        Condition = {
          StringEquals = {
            # PASTE YOUR 'STORAGE_AWS_EXTERNAL_ID' HERE
            "sts:ExternalId" = "UV33480_SFCRole=6_d77QzUbVWzfTGLeJtSstfS6H2cU="
          }
        }
      }
    ]
  })
}

# The Permission: What the role is allowed to touch
resource "aws_iam_policy" "snowflake_s3_access" {
  name        = "SnowflakeS3AccessPolicy-${var.environment}"
  description = "Allows Snowflake to read files from Silver bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          "${aws_s3_bucket.silver.arn}",
          "${aws_s3_bucket.silver.arn}/*"
        ]
      }
    ]
  })
}

# The Glue: Attaching the policy to the role
resource "aws_iam_role_policy_attachment" "snowflake_attach" {
  role       = aws_iam_role.snowflake_role.name
  policy_arn = aws_iam_policy.snowflake_s3_access.arn
}
