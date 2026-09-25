output "pipeline_queue_url" {
  value = aws_sqs_queue.pipeline_jobs.url
}

output "pipeline_queue_arn" {
  value = aws_sqs_queue.pipeline_jobs.arn
}

output "pipeline_dlq_url" {
  value = aws_sqs_queue.pipeline_dlq.url
}

output "pipeline_dlq_arn" {
  value = aws_sqs_queue.pipeline_dlq.arn
}
