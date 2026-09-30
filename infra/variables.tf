variable "aws_region" {
  description = "AWS region for PipelineWatch resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefix used for PipelineWatch AWS resources"
  type        = string
  default     = "pipelinewatch"
}

variable "max_receive_count" {
  description = "Number of SQS receives before a failed message moves to the DLQ"
  type        = number
  default     = 3
}

variable "visibility_timeout_seconds" {
  description = "SQS visibility timeout; should be greater than Lambda processing time"
  type        = number
  default     = 60
}

variable "lambda_timeout_seconds" {
  description = "Worker Lambda timeout"
  type        = number
  default     = 30
}

variable "lambda_memory_mb" {
  description = "Worker Lambda memory allocation"
  type        = number
  default     = 256
}

variable "metric_namespace" {
  description = "CloudWatch namespace for PipelineWatch custom metrics"
  type        = string
  default     = "PipelineWatch"
}

variable "alarm_email" {
  description = "Optional email address for SNS alarm notifications"
  type        = string
  default     = ""
}
