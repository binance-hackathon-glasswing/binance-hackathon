mock_provider "aws" {}
variables {
  region            = "ap-southeast-1"
  account_id        = "123456789012"
  state_bucket_name = "larp-fixture-state-only"
}
run "private_versioned_state" {
  command = plan
  assert {
    condition     = aws_s3_bucket_versioning.state.versioning_configuration[0].status == "Enabled" && aws_s3_bucket_public_access_block.state.block_public_policy && !aws_s3_bucket.state.force_destroy
    error_message = "State must be versioned, private and protected from forced deletion."
  }
}
