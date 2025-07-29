import json
import subprocess
import os
import sys
import argparse

def upload_secret(project_id, secret_id, secret_value):
    # Create secret if it doesn't exist
    create_result = subprocess.run(
        ["gcloud", "secrets", "describe", secret_id, "--project", project_id],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if create_result.returncode != 0:
        print(f"Creating new secret: {secret_id}")
        create_process = subprocess.run(
            ["gcloud", "secrets", "create", secret_id, "--project", project_id],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        if create_process.returncode != 0:
            print(f"Error details: {create_process.stderr}")
            raise Exception(f"Failed to create secret {secret_id}: {create_process.stderr}")
    else:
        print(f"Secret already exists: {secret_id}, adding new version")

    # Add new version of the secret
    proc = subprocess.Popen(
        ["gcloud", "secrets", "versions", "add", secret_id,
         "--project", project_id, "--data-file", "-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = proc.communicate(input=secret_value.encode())
    if proc.returncode != 0:
        print(f"Error details: {stderr.decode() if stderr else 'No error details available'}")
        raise Exception(f"Failed to upload secret {secret_id}")

    print(f"Successfully uploaded secret: {secret_id}")

def is_valid_secret_name(name):
    """Check if secret name is valid according to GCP requirements"""
    import re
    # Allow uppercase letters in the pattern
    pattern = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]*$')
    return bool(pattern.match(name))

def main():
    parser = argparse.ArgumentParser(description='Upload secrets to Google Secret Manager')
    parser.add_argument('secrets_file', nargs='?', default='secrets.json', 
                        help='Path to the JSON file containing secrets to upload')
    args = parser.parse_args()
    
    project_id = os.environ.get("GCP_PROJECT_ID")
    if not project_id:
        print("Error: GCP_PROJECT_ID environment variable not set")
        sys.exit(1)
    
    secrets_file = args.secrets_file
    print(f"Using secrets file: {secrets_file}")
    
    try:
        with open(secrets_file, "r") as f:
            secrets = json.load(f)
    except FileNotFoundError:
        print(f"Error: Secrets file '{secrets_file}' not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in secrets file '{secrets_file}'")
        sys.exit(1)
    
    if not secrets:
        print("Warning: No secrets found in the secrets file")
        return
    
    print(f"Found {len(secrets)} secrets to upload")
    
    for secret_id, secret_value in secrets.items():
      if not is_valid_secret_name(secret_id):
        print(f"Warning: Invalid secret name format: {secret_id}")
        print("Secret names must start with a letter and contain only lowercase letters, numbers, hyphens, and underscores")
        continue
        
      try:
        upload_secret(project_id, secret_id, secret_value)
      except Exception as e:
        print(f"Error uploading secret {secret_id}: {str(e)}")
        sys.exit(1)
    
    print("All secrets uploaded successfully")

if __name__ == "__main__":
    main()