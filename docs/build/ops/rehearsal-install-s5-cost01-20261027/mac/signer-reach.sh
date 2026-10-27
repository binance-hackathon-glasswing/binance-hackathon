#!/bin/bash
# Read-only (Mac, Yao): why SSM cannot deliver to the signer. SSM registration and ping of both hosts, the IDEA-080
# endpoints (state, private DNS), the signer's EC2 state/status checks and its role's policies. Prints IDs and states only.
#   bash mac/signer-reach.sh        (also saved to results/signer-reach.txt)
set -uo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"; AWS=(aws --profile larp --region ap-southeast-2)
{
echo "== now $(date -u +%FT%TZ)"
echo "== SSM registration (signer i-0f8fe5d5fe5ccba36, primary i-040fc5fea8b700e9a)"
"${AWS[@]}" ssm describe-instance-information --filters Key=InstanceIds,Values=i-0f8fe5d5fe5ccba36,i-040fc5fea8b700e9a \
  --query 'InstanceInformationList[].[InstanceId,PingStatus,LastPingDateTime,AgentVersion]' --output text
echo "== SSM interface endpoints"
"${AWS[@]}" ec2 describe-vpc-endpoints --filters Name=service-name,Values=com.amazonaws.ap-southeast-2.ssm,com.amazonaws.ap-southeast-2.ssmmessages,com.amazonaws.ap-southeast-2.ec2messages \
  --query 'VpcEndpoints[].[ServiceName,State,PrivateDnsEnabled,length(SubnetIds),CreationTimestamp]' --output text
echo "== signer EC2 state and status checks"
"${AWS[@]}" ec2 describe-instance-status --include-all-instances --instance-ids i-0f8fe5d5fe5ccba36 \
  --query 'InstanceStatuses[].[InstanceState.Name,SystemStatus.Status,InstanceStatus.Status]' --output text
"${AWS[@]}" ec2 describe-instances --instance-ids i-0f8fe5d5fe5ccba36 --query 'Reservations[].Instances[].LaunchTime' --output text \
  | sed 's/^/last start: /'
echo "== signer role policies"
ROLE=$("${AWS[@]}" ec2 describe-instances --instance-ids i-0f8fe5d5fe5ccba36 \
  --query 'Reservations[].Instances[].IamInstanceProfile.Arn' --output text | awk -F/ '{print $NF}')
"${AWS[@]}" iam get-instance-profile --instance-profile-name "$ROLE" --query 'InstanceProfile.Roles[].RoleName' --output text \
  | while read -r r; do echo "role $r"; "${AWS[@]}" iam list-attached-role-policies --role-name "$r" \
      --query 'AttachedPolicies[].PolicyName' --output text; done
} 2>&1 | tee "$HERE/results/signer-reach.txt"
