import subprocess
import json

out = subprocess.check_output(['aws', 'ecs', 'describe-task-definition', '--task-definition', 'default-xaiote-backend'])
data = json.loads(out)
td = data['taskDefinition']
for key in ['taskDefinitionArn', 'revision', 'status', 'requiresAttributes', 'compatibilities', 'registeredAt', 'registeredBy']:
    td.pop(key, None)

container = td['containerDefinitions'][0]
container['image'] = '394920712303.dkr.ecr.ap-south-1.amazonaws.com/xaiote-backend:latest'
if 'environment' not in container:
    container['environment'] = []
container['environment'].append({
    'name': 'WHATSAPP_VERIFY_TOKEN',
    'value': 'XaioteWA_Verify_9f82Kp31_2026'
})

with open('td.json', 'w') as f:
    json.dump(td, f)
