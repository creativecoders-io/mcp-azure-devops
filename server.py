#!/usr/bin/env python3
"""
Azure DevOps MCP Server

Provides tools for interacting with Azure DevOps repositories, branches, files, and pull requests.
"""

import os
import sys
import json
import base64
import logging
from typing import Any

import requests
from mcp.server import Server
from mcp.types import Tool, TextContent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration from environment variables
AZURE_DEVOPS_ORG = os.getenv('AZURE_DEVOPS_ORG')
AZURE_DEVOPS_PROJECT = os.getenv('AZURE_DEVOPS_PROJECT')
AZURE_DEVOPS_PAT = os.getenv('AZURE_DEVOPS_PAT')

if not AZURE_DEVOPS_PAT:
    logger.error("AZURE_DEVOPS_PAT environment variable is required")
    sys.exit(1)

if not AZURE_DEVOPS_ORG:
    logger.error("AZURE_DEVOPS_ORG environment variable is required")
    sys.exit(1)

if not AZURE_DEVOPS_PROJECT:
    logger.error("AZURE_DEVOPS_PROJECT environment variable is required")
    sys.exit(1)

BASE_URL = f"https://dev.azure.com/{AZURE_DEVOPS_ORG}"

# Create session with authentication
session = requests.Session()
session.auth = ('', AZURE_DEVOPS_PAT)
session.headers.update({
    'Content-Type': 'application/json',
    'Accept': 'application/json'
})


def search_repos(query: str, project: str | None = None) -> list[dict[str, Any]]:
    """Search for repositories by name or description."""
    target_project = project or AZURE_DEVOPS_PROJECT
    url = f"{BASE_URL}/{target_project}/_apis/git/repositories?api-version=7.0"
    
    logger.info(f"Searching repos with query: {query} in project: {target_project}")
    
    try:
        response = session.get(url)
        response.raise_for_status()
        repos = response.json().get('value', [])
        
        # Filter by query
        filtered = [
            repo for repo in repos
            if query.lower() in repo['name'].lower() or 
               query.lower() in repo.get('description', '').lower()
        ]
        
        return [{
            'id': repo['id'],
            'name': repo['name'],
            'description': repo.get('description', ''),
            'defaultBranch': repo.get('defaultBranch', 'refs/heads/main').replace('refs/heads/', ''),
            'webUrl': repo['webUrl'],
            'remoteUrl': repo['remoteUrl']
        } for repo in filtered]
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error searching repos: {e}")
        raise


def read_file(repo: str, path: str, branch: str | None = None) -> dict[str, Any]:
    """Read file contents from a repository."""
    target_branch = branch or 'main'
    url = f"{BASE_URL}/{AZURE_DEVOPS_PROJECT}/_apis/git/repositories/{repo}/items"
    
    params = {
        'path': path,
        'versionDescriptor.version': target_branch,
        'versionDescriptor.versionType': 'branch',
        'api-version': '7.0'
    }
    
    logger.info(f"Reading file: {path} from repo: {repo}, branch: {target_branch}")
    
    try:
        response = session.get(url, params=params)
        response.raise_for_status()
        
        # For text files, return content directly
        content = response.text
        
        return {
            'content': content,
            'path': path,
            'branch': target_branch
        }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error reading file: {e}")
        raise


def create_branch(repo: str, source_branch: str, new_branch: str) -> dict[str, Any]:
    """Create a new branch from an existing branch."""
    url = f"{BASE_URL}/{AZURE_DEVOPS_PROJECT}/_apis/git/repositories/{repo}/refs?api-version=7.0"
    
    # First, get the commit ID of the source branch
    refs_url = f"{BASE_URL}/{AZURE_DEVOPS_PROJECT}/_apis/git/repositories/{repo}/refs?filter=heads/{source_branch}&api-version=7.0"
    
    logger.info(f"Creating branch: {new_branch} from {source_branch} in repo: {repo}")
    
    try:
        # Get source branch commit
        refs_response = session.get(refs_url)
        refs_response.raise_for_status()
        refs = refs_response.json().get('value', [])
        
        if not refs:
            raise ValueError(f"Source branch '{source_branch}' not found")
        
        source_commit = refs[0]['objectId']
        
        # Create new branch
        payload = [{
            'name': f'refs/heads/{new_branch}',
            'oldObjectId': '0000000000000000000000000000000000000000',
            'newObjectId': source_commit
        }]
        
        response = session.post(url, json=payload)
        response.raise_for_status()
        result = response.json()['value'][0]
        
        return {
            'name': new_branch,
            'objectId': result['newObjectId'],
            'url': f"{BASE_URL}/{AZURE_DEVOPS_PROJECT}/_git/{repo}?version=GB{new_branch}"
        }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error creating branch: {e}")
        raise


def update_file(repo: str, branch: str, path: str, content: str, commit_message: str, old_object_id: str | None = None) -> dict[str, Any]:
    """Update file contents and commit."""
    url = f"{BASE_URL}/{AZURE_DEVOPS_PROJECT}/_apis/git/repositories/{repo}/pushes?api-version=7.0"
    
    logger.info(f"Updating file: {path} in branch: {branch}, repo: {repo}")
    
    try:
        # If old_object_id not provided, get current branch commit
        if not old_object_id:
            refs_url = f"{BASE_URL}/{AZURE_DEVOPS_PROJECT}/_apis/git/repositories/{repo}/refs?filter=heads/{branch}&api-version=7.0"
            refs_response = session.get(refs_url)
            refs_response.raise_for_status()
            refs = refs_response.json().get('value', [])
            
            if not refs:
                raise ValueError(f"Branch '{branch}' not found")
            
            old_object_id = refs[0]['objectId']
        
        # Encode content to base64
        content_bytes = content.encode('utf-8')
        content_base64 = base64.b64encode(content_bytes).decode('utf-8')
        
        # Create push payload
        payload = {
            'refUpdates': [{
                'name': f'refs/heads/{branch}',
                'oldObjectId': old_object_id
            }],
            'commits': [{
                'comment': commit_message,
                'changes': [{
                    'changeType': 'edit',
                    'item': {'path': path},
                    'newContent': {
                        'content': content_base64,
                        'contentType': 'base64encoded'
                    }
                }]
            }]
        }
        
        response = session.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        
        return {
            'commitId': result['commits'][0]['commitId'],
            'branch': branch,
            'url': f"{BASE_URL}/{AZURE_DEVOPS_PROJECT}/_git/{repo}/commit/{result['commits'][0]['commitId']}"
        }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error updating file: {e}")
        raise


def create_pr(repo: str, source_branch: str, target_branch: str, title: str, description: str | None = None) -> dict[str, Any]:
    """Create a pull request."""
    url = f"{BASE_URL}/{AZURE_DEVOPS_PROJECT}/_apis/git/repositories/{repo}/pullrequests?api-version=7.0"
    
    logger.info(f"Creating PR: {source_branch} -> {target_branch} in repo: {repo}")
    
    try:
        payload = {
            'sourceRefName': f'refs/heads/{source_branch}',
            'targetRefName': f'refs/heads/{target_branch}',
            'title': title,
            'description': description or ''
        }
        
        response = session.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        
        return {
            'pullRequestId': result['pullRequestId'],
            'status': result['status'],
            'url': f"{BASE_URL}/{AZURE_DEVOPS_PROJECT}/_git/{repo}/pullrequest/{result['pullRequestId']}",
            'title': result['title']
        }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error creating PR: {e}")
        raise


def list_branches(repo: str) -> list[dict[str, Any]]:
    """List all branches in a repository."""
    url = f"{BASE_URL}/{AZURE_DEVOPS_PROJECT}/_apis/git/repositories/{repo}/refs?filter=heads/&api-version=7.0"
    
    logger.info(f"Listing branches for repo: {repo}")
    
    try:
        response = session.get(url)
        response.raise_for_status()
        refs = response.json().get('value', [])
        
        return [{
            'name': ref['name'].replace('refs/heads/', ''),
            'objectId': ref['objectId']
        } for ref in refs]
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error listing branches: {e}")
        raise


# Create MCP server
app = Server("azure-devops-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="azure_devops_search_repos",
            description="Search for repositories by name or description",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (matches repo name or description)"
                    },
                    "project": {
                        "type": "string",
                        "description": f"Project name (default: {AZURE_DEVOPS_PROJECT})"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="azure_devops_read_file",
            description="Read file contents from a repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name or ID"
                    },
                    "path": {
                        "type": "string",
                        "description": "File path (e.g., 'src/index.html')"
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name (default: 'main')"
                    }
                },
                "required": ["repo", "path"]
            }
        ),
        Tool(
            name="azure_devops_create_branch",
            description="Create a new branch from an existing branch",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name or ID"
                    },
                    "source_branch": {
                        "type": "string",
                        "description": "Source branch name (e.g., 'main')"
                    },
                    "new_branch": {
                        "type": "string",
                        "description": "New branch name (e.g., 'feature/update-homepage')"
                    }
                },
                "required": ["repo", "source_branch", "new_branch"]
            }
        ),
        Tool(
            name="azure_devops_update_file",
            description="Update file contents and commit",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name or ID"
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name"
                    },
                    "path": {
                        "type": "string",
                        "description": "File path"
                    },
                    "content": {
                        "type": "string",
                        "description": "New file content"
                    },
                    "commit_message": {
                        "type": "string",
                        "description": "Commit message"
                    },
                    "old_object_id": {
                        "type": "string",
                        "description": "Previous commit ID (optional, for conflict detection)"
                    }
                },
                "required": ["repo", "branch", "path", "content", "commit_message"]
            }
        ),
        Tool(
            name="azure_devops_create_pr",
            description="Create a pull request",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name or ID"
                    },
                    "source_branch": {
                        "type": "string",
                        "description": "Source branch name (e.g., 'feature/my-feature')"
                    },
                    "target_branch": {
                        "type": "string",
                        "description": "Target branch name (e.g., 'main')"
                    },
                    "title": {
                        "type": "string",
                        "description": "Pull request title"
                    },
                    "description": {
                        "type": "string",
                        "description": "Pull request description (optional)"
                    }
                },
                "required": ["repo", "source_branch", "target_branch", "title"]
            }
        ),
        Tool(
            name="azure_devops_list_branches",
            description="List all branches in a repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name or ID"
                    }
                },
                "required": ["repo"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "azure_devops_search_repos":
            result = search_repos(
                query=arguments["query"],
                project=arguments.get("project")
            )
        elif name == "azure_devops_read_file":
            result = read_file(
                repo=arguments["repo"],
                path=arguments["path"],
                branch=arguments.get("branch")
            )
        elif name == "azure_devops_create_branch":
            result = create_branch(
                repo=arguments["repo"],
                source_branch=arguments["source_branch"],
                new_branch=arguments["new_branch"]
            )
        elif name == "azure_devops_update_file":
            result = update_file(
                repo=arguments["repo"],
                branch=arguments["branch"],
                path=arguments["path"],
                content=arguments["content"],
                commit_message=arguments["commit_message"],
                old_object_id=arguments.get("old_object_id")
            )
        elif name == "azure_devops_create_pr":
            result = create_pr(
                repo=arguments["repo"],
                source_branch=arguments["source_branch"],
                target_branch=arguments["target_branch"],
                title=arguments["title"],
                description=arguments.get("description")
            )
        elif name == "azure_devops_list_branches":
            result = list_branches(repo=arguments["repo"])
        else:
            raise ValueError(f"Unknown tool: {name}")
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(e)}, indent=2)
        )]


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    
    if transport == "http":
        logger.info("Starting Azure DevOps MCP Server with Streamable HTTP transport...")
        app.run(
            transport="streamable-http",
            host="0.0.0.0",
            port=int(os.getenv("PORT", "8000")),
        )
    else:
        logger.info("Starting Azure DevOps MCP Server with stdio transport...")
        app.run()
