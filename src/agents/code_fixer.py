import os
import json
import re
import subprocess
import google.generativeai as genai
from github import Github
from src.agents.issue_creation_agent import Issue

def create_pull_request(branch_name: str, issue: Issue, repo_url: str):
    """Creates a pull request on GitHub."""
    try:
        token = os.environ["GITHUB_TOKEN"]
        repo_name = repo_url.replace("https://github.com/", "")

        g = Github(token)
        repo = g.get_repo(repo_name)

        # Format log entries outside f-string to avoid backslash issues
        log_entries_text = "\n".join(issue.log_entries)
        pr_body = f"This PR fixes the following issue: {issue.description}\n\n**Relevant Log Entries:**\n```\n{log_entries_text}\n```"

        repo.create_pull(
            title=f"Fix: {issue.description}",
            body=pr_body,
            head=branch_name,
            base="main", # Assuming the base branch is main
        )
        print(f"Successfully created pull request for branch {branch_name}")
        
    except Exception as e:
        print(f"Error creating pull request: {e}")

def apply_fix(file_path: str, code_fix: str, issue: Issue, repo_url: str, repo_path: str):
    """Applies a code fix to a file in a new branch and creates a pull request."""
    
    branch_name = f"fix/{issue.description.replace(' ', '-')[:20]}"
    
    try:
        # Create a new branch
        subprocess.run(["git", "checkout", "-b", branch_name], check=True, cwd=repo_path)
        
        # Apply the fix
        full_path = os.path.join(repo_path, file_path)
        with open(full_path, "w") as f:
            f.write(code_fix)
            
        # Stage the changes
        subprocess.run(["git", "add", file_path], check=True, cwd=repo_path)
        
        # Commit the changes
        subprocess.run(["git", "commit", "-m", f"Fix: {issue.description}"], check=True, cwd=repo_path)
        
        # Push the new branch
        subprocess.run(["git", "push", "-u", "origin", branch_name], check=True, cwd=repo_path)
        
        print(f"Successfully applied fix in branch {branch_name}")
        
        # Create a pull request
        create_pull_request(branch_name, issue, repo_url)
        
    except subprocess.CalledProcessError as e:
        print(f"Error applying fix: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def code_fixer_agent(issue: Issue, repo_url: str) -> str:
    """Analyzes an issue, reads the relevant code, and suggests a fix."""

    # Clone the repository to a temporary directory
    import tempfile
    repo_path = tempfile.mkdtemp()
    subprocess.run(["git", "clone", repo_url, repo_path], check=True)

    # Get a list of all files in the repository
    all_files = []
    for root, _, files in os.walk(repo_path):
        for file in files:
            relative_path = os.path.relpath(os.path.join(root, file), repo_path)
            all_files.append(relative_path)

    # Use LLM to identify relevant files
    # Format strings outside f-string to avoid backslash issues
    log_entries_text = "\n".join(issue.log_entries)
    all_files_text = "\n".join(all_files)

    file_selection_prompt = f"""Given the following issue and log entries, and a list of files in the repository, identify the most relevant files that might need modification to fix the issue.

    Issue: {issue.description}

    Log Entries:
    {log_entries_text}

    All Files in Repository:
    {all_files_text}

    Return a JSON array of the relative file paths that are most relevant. For example: ["src/main.py", "tests/test_main.py"]
    """
    file_selection_model = genai.GenerativeModel(os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash"))
    file_selection_response = file_selection_model.generate_content(file_selection_prompt)

    relevant_files = []
    try:
        match = re.search(r"```json\n(.*?)\n```", file_selection_response.text, re.DOTALL)
        if match:
            json_text = match.group(1)
            relevant_files = json.loads(json_text)
        else:
            print(f"Error parsing file selection response: No JSON block found\nResponse text: {file_selection_response.text}")
    except (json.JSONDecodeError, TypeError) as e:
        print(f"Error parsing file selection response: {e}\nResponse text: {file_selection_response.text}")

    # Read only the relevant files
    code = ""
    for file_path in relevant_files:
        full_path = os.path.join(repo_path, file_path)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            try:
                with open(full_path, "r") as f:
                    code += f"--- {file_path} ---\n{f.read()}\n"
            except Exception:
                print(f"Warning: Could not read file {file_path}")
        else:
            print(f"Warning: Identified relevant file {file_path} does not exist or is not a file.")

    # Format log entries outside f-string to avoid backslash issues
    log_entries_text_2 = "\n".join(issue.log_entries)

    prompt = f"""Analyze the following issue, log entries, and code, and suggest a fix.

    Issue: {issue.description}

    Log Entries:
    {log_entries_text_2}

    Code:
    {code}

    Please provide the fix in JSON format with two keys: 'file_path' and 'code_fix'.
    The 'file_path' should be the relative path to the file to be modified.
    The 'code_fix' should be the complete code for the file with the fix applied.
    """

    model = genai.GenerativeModel(os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash"))
    response = model.generate_content(prompt)

    try:
        # The response may contain markdown, so we need to extract the JSON part
        match = re.search(r"```json\n(.*?)\n```", response.text, re.DOTALL)
        if match:
            json_text = match.group(1)
            fix_data = json.loads(json_text)
            
            file_path = fix_data['file_path']
            code_fix = fix_data['code_fix']
            
            apply_fix(file_path, code_fix, issue, repo_url, repo_path)
            
            return f"Fix applied and pull request created for issue: {issue.description}"
        else:
            print(f"Error parsing response from Gemini API: No JSON block found\nResponse text: {response.text}")
            return f"Error applying fix for issue: {issue.description}"
        
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        print(f"Error parsing response from Gemini API: {e}\nResponse text: {response.text}")
        return f"Error applying fix for issue: {issue.description}"