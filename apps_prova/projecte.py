# aws sso login --profile projecte1
# aws sts get-caller-identity --profile projecte1
import boto3

session= boto3.Session(profile_name='projecte1')
bedrock = session.client('bedrock')
response = bedrock.list_foundation_models()
models = response['modelSummaries']
print(f'{len(models)} available models.')
for model in models:
    print(f'- {model["modelId"]}')
