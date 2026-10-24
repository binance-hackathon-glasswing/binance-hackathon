# IDEA-091 example (copy to a git-ignored file). The login hash goes in the KeyValueStore after apply, never here:
#   printf '%s' "$(printf 'user:password' | base64)" | sha256sum   ->  aws cloudfront-keyvaluestore put-key ...
account_id          = "000000000000"
region              = "ap-southeast-2"
environment         = "rehearsal"
name                = "larp-rehearsal"
bucket_name         = "larp-rehearsal-dashboard"
primary_instance_id = "i-0000000000000000"
wallet              = "0x0000000000000000000000000000000000000000"
start_nonce         = 0
start_usdt          = 100
package_path        = "../../../deploy/activation/dashboard-lambda.zip" # git-ignored
log_retention_days  = 30
