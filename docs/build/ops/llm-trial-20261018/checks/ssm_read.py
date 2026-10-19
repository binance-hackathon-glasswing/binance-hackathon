import base64,json,pathlib,subprocess,sys,time
root=pathlib.Path(__file__).parent
script=pathlib.Path(sys.argv[1]); name=sys.argv[2]
args=['/opt/homebrew/bin/aws','--profile','larp','--region','ap-southeast-2']
params={'commands':['echo '+base64.b64encode(script.read_bytes()).decode()+' | base64 --decode | bash']}
p=root/(name+'-parameters.json');p.write_text(json.dumps(params))
def aws(extra):
 r=subprocess.run(args+extra,capture_output=True,text=True)
 if r.returncode:
  (root/(name+'-aws-error.txt')).write_text(r.stderr);raise RuntimeError('AWS_CALL_FAILED; private diagnostic retained')
 return json.loads(r.stdout)
x=aws(['ssm','send-command','--instance-ids','i-040fc5fea8b700e9a','--document-name','AWS-RunShellScript','--parameters','file://'+str(p),'--output','json'])
c=x['Command']['CommandId'];(root/(name+'-command-id.txt')).write_text(c)
for i in range(80):
 time.sleep(2)
 y=aws(['ssm','get-command-invocation','--command-id',c,'--instance-id','i-040fc5fea8b700e9a','--output','json'])
 if y['Status'] not in ('Pending','InProgress','Delayed'):break
(root/(name+'-ssm-result.json')).write_text(json.dumps(y))
(root/(name+'-stdout.txt')).write_text(y.get('StandardOutputContent',''))
print(json.dumps({'command_id':c,'status':y['Status'],'stdout_bytes':len(y.get('StandardOutputContent','').encode()),'stderr_bytes':len(y.get('StandardErrorContent','').encode())}))
if y['Status']!='Success':sys.exit(1)
