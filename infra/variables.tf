variable "aws_region" {
  description = "AWS region for PipelineWatch resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefix used for queue names"
  type        = string
  default     = "pipelinewatch"
}

variable "max_receive_count" {
  description = "Number of SQS receives before a message is moved to the DLQ"
  type        = number
  default     = 3
}

variable "visibility_timeout_seconds" {
  description = "How long an in-flight message stays hidden from other consumers"
  type        = number
  default     = 30
}
