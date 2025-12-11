import configparser
import base64
import requests
import json
import os
import sys

# --- Configuration ---
FILE_TO_CREATE = 'new_file.txt' # The name of the new file in the repo
FILE_CONTENT = 'This is the content of the new file created by the script.'
COMMIT_MESSAGE = 'Automated file addition via Python script'
BRANCH_NAME = 'main' # The target branch for the commit

# --- Main Logic ---

def update_github_file_from_env():
    # 1. Determine the Config File Path using GITHUB_WORKSPACE
    github_workspace = os.environ.get('GITHUB_WORKSPACE')
    
    if not github_workspace:
        print("❌ Error: GITHUB_WORKSPACE environment variable is not set.")
        print("This script requires GITHUB_WORKSPACE to locate the config file.")
        sys.exit(1)
        
    # Construct the full path to the config file
    CONFIG_FILE = os.path.join(github_workspace, '.git', 'config')

    if not os.path.exists(CONFIG_FILE):
        print(f"❌ Error: Config file not found at path: {CONFIG_FILE}")
        sys.exit(1)
    
    print(f"✅ Reading config from: {CONFIG_FILE}")
    
    # 2. Read the configuration file
    config = configparser.ConfigParser()
    try:
        # Note: configparser may need explicit encoding if the file has unusual characters, 
        # but the default should work for standard git config.
        config.read(CONFIG_FILE)
    except Exception as e:
        print(f"❌ Error reading config file: {e}")
        sys.exit(1)

    # 3. Extract and Decode Authentication
    try:
        # Get the full extraheader value from the [http "https://github.com/"] section
        full_header = config.get('http "https://github.com/"', 'extraheader')
        # Expected format: AUTHORIZATION: basic <base64_string>

        # Split and get the base64 part
        parts = full_header.split('basic')
        if len(parts) < 2:
            print("❌ Error: 'basic' keyword not found in extraheader.")
            sys.exit(1)

        base64_string = parts[1].strip()

        # Base64 decode
        decoded_bytes = base64.b64decode(base64_string)
        decoded_auth = decoded_bytes.decode('utf-8')

        # The decoded string is typically "username:token"
        _, github_token = decoded_auth.split(':', 1)
        
        # Security Note: Avoid printing the full token in production logs.
        print(f"Decoded Authentication Token (first 8 chars): **{github_token[:8]}...**")

    except configparser.NoSectionError:
        print(f"❌ Error: Section '[http \"https://github.com/\"]' not found in config.")
        sys.exit(1)
    except configparser.NoOptionError:
        print(f"❌ Error: Option 'extraheader' not found in the http section.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during decoding or parsing: {e}")
        sys.exit(1)

    # 4. Determine Repository Details
    try:
        repo_url = config.get('remote "origin"', 'url')
        
        # Extract owner and repo name from the URL: https://github.com/owner/repo
        if repo_url.startswith('https://github.com/'):
            # The URL might end with or without .git, so we clean it up
            clean_url = repo_url.replace('.git', '')
            path_parts = clean_url.split('/')[3:]
            if len(path_parts) >= 2:
                owner = path_parts[0]
                repo = path_parts[1]
            else:
                print("❌ Error: Could not parse owner and repo from URL.")
                sys.exit(1)
        else:
            print(f"❌ Error: Repository URL is not in expected GitHub format: {repo_url}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error getting repository details: {e}")
        sys.exit(1)
        
    # Construct the GitHub API URL for the contents
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{FILE_TO_CREATE}"
    print(f"GitHub Target Repo: **{owner}/{repo}**")
    print(f"GitHub API URL: {api_url}")


    # 5. Prepare and Make the API Request
    
    # Content must be Base64 encoded for the GitHub Contents API
    file_content_base64 = base64.b64encode(FILE_CONTENT.encode('utf-8')).decode('utf-8')

    payload = {
        "message": COMMIT_MESSAGE,
        "content": file_content_base64,
        "branch": BRANCH_NAME
    }

    headers = {
        # Using the PAT requires 'token <TOKEN>' for the value in the Authorization header
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    print(f"Attempting to PUT file '{FILE_TO_CREATE}' to branch '{BRANCH_NAME}'...")
    
    try:
        response = requests.put(api_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        # Success!
        print("\n🎉 File successfully created/updated on GitHub!")
        print(f"Response status: {response.status_code}")
        print(f"Commit SHA: {response.json().get('commit', {}).get('sha')}")

    except requests.exceptions.HTTPError as errh:
        print(f"\n❌ HTTP Error occurred: {errh}")
        try:
            # Print the error message from the GitHub API response
            error_message = response.json().get('message', 'No specific API message provided.')
            print(f"GitHub API Message: {error_message}")
        except json.JSONDecodeError:
             print("Could not decode error response body.")
    except requests.exceptions.RequestException as err:
        print(f"\n❌ An error occurred during the request: {err}")

# Execute the function
if __name__ == "__main__":
    # Ensure the 'requests' library is installed
    try:
        import requests
    except ImportError:
        print("❌ The 'requests' library is required. Install it using: pip install requests")
        sys.exit(1)
        
    update_github_file_from_env()