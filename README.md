# Azure DevOps MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides tools for interacting with Azure DevOps repositories, branches, files, and pull requests.

## Features

This MCP server implements the following tools:

- **azure_devops_search_repos** - Search for repositories by name or description
- **azure_devops_read_file** - Read file contents from a repository
- **azure_devops_create_branch** - Create a new branch from an existing branch
- **azure_devops_update_file** - Update file contents and commit changes
- **azure_devops_create_pr** - Create a pull request
- **azure_devops_list_branches** - List all branches in a repository

## Prerequisites

- Python 3.10 or higher
- Azure DevOps organization and project
- Azure DevOps Personal Access Token (PAT) with the following permissions:
  - Code (Read & Write)
  - Pull Requests (Read, Write & Manage)

## Installation

### Local Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/mcp-azure-devops.git
cd mcp-azure-devops
```

2. Create a virtual environment and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Set environment variables:
```bash
export AZURE_DEVOPS_ORG="<organization-name>"
export AZURE_DEVOPS_PROJECT="<project-name>"
export AZURE_DEVOPS_PAT="<your-pat-token>"
```

4. Run the server:
```bash
python3 server.py
```

### Docker Installation

1. Build the Docker image:
```bash
docker build -t mcp-azure-devops .
```

2. Run the container:
```bash
docker run -i \
  -e AZURE_DEVOPS_ORG="<organization-name>" \
  -e AZURE_DEVOPS_PROJECT="<project-name>" \
  -e AZURE_DEVOPS_PAT="<your-pat-token>" \
  mcp-azure-devops
```

### Docker Compose

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and set your Azure DevOps credentials:
```env
AZURE_DEVOPS_ORG=<organization-name>
AZURE_DEVOPS_PROJECT=<project-name>
AZURE_DEVOPS_PAT=<your-pat-token>
```

3. Start the server:
```bash
docker compose up -d
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_DEVOPS_ORG` | Yes | Azure DevOps organization name |
| `AZURE_DEVOPS_PROJECT` | Yes | Azure DevOps project name |
| `AZURE_DEVOPS_PAT` | Yes | Personal Access Token with Code and PR permissions |
| `MCP_TRANSPORT` | No | Transport mode: `stdio` (default) or `http` |
| `PORT` | No | Port for HTTP transport (default: `8000`) |

### Transport Modes

The server supports two transport modes:

#### stdio Transport (Default)
For local process integrations. The server communicates over standard input/output.

```bash
# Run with stdio (default)
python3 server.py

# Or explicitly set
export MCP_TRANSPORT=stdio
python3 server.py
```

#### SSE/HTTP Transport
For independently running MCP servers over HTTP using Server-Sent Events (SSE). This is the recommended production transport.

```bash
# Run with HTTP transport
export MCP_TRANSPORT=http
export PORT=8000
python3 server.py
```

The server will be available at `http://0.0.0.0:8000` with SSE endpoint at `/messages`

### Docker Configuration

For HTTP transport with Docker:

```bash
docker run -i \
  -e AZURE_DEVOPS_ORG="<organization-name>" \
  -e AZURE_DEVOPS_PROJECT="<project-name>" \
  -e AZURE_DEVOPS_PAT="<your-pat-token>" \
  -e MCP_TRANSPORT=http \
  -e PORT=8000 \
  -p 8000:8000 \
  mcp-azure-devops
```

Or update your `docker-compose.yml` to uncomment the HTTP transport configuration.

### Creating a Personal Access Token

1. Go to Azure DevOps → User Settings → Personal Access Tokens
2. Click "New Token"
3. Set the following scopes:
   - **Code**: Read & Write
   - **Pull Request Thread**: Read & Write
4. Copy the generated token and use it as `AZURE_DEVOPS_PAT`

## Integration with OpenClaw or Other MCP Clients

### Using with OpenClaw (Docker)

If you're running OpenClaw in a Docker container, add this MCP server to the network:

1. **docker-compose.yml for OpenClaw:**
```yaml
version: '3.8'

services:
  openclaw:
    image: openclaw:latest
    volumes:
      - ./config:/config
    environment:
      - MCP_CONFIG=/config/mcp-config.json
    depends_on:
      - azure-devops-mcp
    networks:
      - mcp-network

  azure-devops-mcp:
    image: mcp-azure-devops
    environment:
      - AZURE_DEVOPS_ORG=${AZURE_DEVOPS_ORG}
      - AZURE_DEVOPS_PROJECT=${AZURE_DEVOPS_PROJECT}
      - AZURE_DEVOPS_PAT=${AZURE_DEVOPS_PAT}
    networks:
      - mcp-network
    stdin_open: true
    tty: true

networks:
  mcp-network:
    driver: bridge
```

2. **MCP Configuration (mcp-config.json):**
```json
{
  "mcpServers": {
    "azure-devops": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "azure-devops-mcp",
        "python3",
        "/app/server.py"
      ]
    }
  }
}
```

### Using with Claude Desktop or VS Code

Add to your MCP configuration file:

**Claude Desktop (~/.claude/config.json):**
```json
{
  "mcpServers": {
    "azure-devops": {
      "command": "python3",
      "args": ["/path/to/mcp-azure-devops/server.py"],
      "env": {
        "AZURE_DEVOPS_ORG": "<organization-name>",
        "AZURE_DEVOPS_PROJECT": "<project-name>",
        "AZURE_DEVOPS_PAT": "<your-pat-token>"
      }
    }
  }
}
```

**VS Code (settings.json):**
```json
{
  "mcp.servers": {
    "azure-devops": {
      "command": "python3",
      "args": ["/path/to/mcp-azure-devops/server.py"],
      "env": {
        "AZURE_DEVOPS_ORG": "<organization-name>",
        "AZURE_DEVOPS_PROJECT": "<project-name>",
        "AZURE_DEVOPS_PAT": "<your-pat-token>"
      }
    }
  }
}
```

## Testing

### Manual Testing

You can test the server manually using `stdio`:

```bash
# Start the server
python3 server.py

# Send a tools/list request (paste this JSON and press Enter twice):
{"jsonrpc":"2.0","id":1,"method":"tools/list"}

# Send a tools/call request:
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"azure_devops_search_repos","arguments":{"query":"MyRepo"}}}
```

### Example Queries

Once integrated with an MCP client, you can ask:

- "Can you find the RaiseTheRiff-Website repository?"
- "Show me the content of home.component.html from the main branch"
- "Create a new branch called feature/update-homepage from main"
- "Update the title in index.html to 'Welcome to My Site'"
- "Create a pull request from feature/update-homepage to main"

## Tools Reference

### azure_devops_search_repos

Search for repositories by name or description.

**Input:**
```json
{
  "query": "repository-name",
  "project": "optional-project-name"
}
```

**Output:**
```json
[
  {
    "id": "repo-id",
    "name": "repository-name",
    "description": "Repository description",
    "defaultBranch": "main",
    "webUrl": "https://dev.azure.com/...",
    "remoteUrl": "https://..."
  }
]
```

### azure_devops_read_file

Read file contents from a repository.

**Input:**
```json
{
  "repo": "repository-name",
  "path": "/path/to/file.txt",
  "branch": "main"
}
```

**Output:**
```json
{
  "content": "file contents...",
  "path": "/path/to/file.txt",
  "branch": "main"
}
```

### azure_devops_create_branch

Create a new branch from an existing branch.

**Input:**
```json
{
  "repo": "repository-name",
  "source_branch": "main",
  "new_branch": "feature/my-feature"
}
```

**Output:**
```json
{
  "name": "feature/my-feature",
  "objectId": "commit-sha",
  "url": "https://dev.azure.com/..."
}
```

### azure_devops_update_file

Update file contents and commit.

**Input:**
```json
{
  "repo": "repository-name",
  "branch": "feature/my-feature",
  "path": "/path/to/file.txt",
  "content": "new file contents",
  "commit_message": "Update file",
  "old_object_id": "optional-commit-sha"
}
```

**Output:**
```json
{
  "commitId": "new-commit-sha",
  "branch": "feature/my-feature",
  "url": "https://dev.azure.com/.../commit/..."
}
```

### azure_devops_create_pr

Create a pull request.

**Input:**
```json
{
  "repo": "repository-name",
  "source_branch": "feature/my-feature",
  "target_branch": "main",
  "title": "My Feature PR",
  "description": "Optional description"
}
```

**Output:**
```json
{
  "pullRequestId": 123,
  "status": "active",
  "url": "https://dev.azure.com/.../pullrequest/123",
  "title": "My Feature PR"
}
```

### azure_devops_list_branches

List all branches in a repository.

**Input:**
```json
{
  "repo": "repository-name"
}
```

**Output:**
```json
[
  {
    "name": "main",
    "objectId": "commit-sha"
  },
  {
    "name": "feature/my-feature",
    "objectId": "commit-sha"
  }
]
```

## Troubleshooting

### Authentication Errors

If you receive 401 Unauthorized errors:
- Verify your PAT is correct and hasn't expired
- Ensure your PAT has the required scopes (Code: Read & Write, Pull Requests: Read, Write & Manage)
- Check that the organization and project names are correct

### Repository Not Found

If you receive 404 errors:
- Verify the repository name is exact (case-sensitive)
- Ensure your PAT has access to the specified project
- Check that the project name matches your Azure DevOps project

### Branch Creation Fails

- Ensure the source branch exists
- Verify the new branch name doesn't already exist
- Check that your PAT has Write permissions

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -r requirements.txt pytest pytest-asyncio

# Run tests
pytest tests/
```

### Project Structure

```
mcp-azure-devops/
├── server.py           # Main MCP server implementation
├── requirements.txt    # Python dependencies
├── Dockerfile         # Docker container definition
├── docker-compose.yml # Docker Compose configuration
├── .env.example       # Example environment variables
└── README.md          # This file
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Resources

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Azure DevOps REST API](https://learn.microsoft.com/en-us/rest/api/azure/devops/)

## Author

Created by Creative Coders BV