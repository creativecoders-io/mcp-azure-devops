# Example: Using Azure DevOps MCP Server with OpenClaw

This directory contains an example Docker Compose configuration showing how to connect OpenClaw (or another MCP client) to the Azure DevOps MCP server running in separate containers.

## Architecture

```
┌─────────────────────────────────┐
│      OpenClaw Container         │
│                                 │
│  - Connects to MCP server       │
│  - Uses tools via stdio exec    │
└─────────────┬───────────────────┘
              │ docker exec
              │ via mcp-network
              ▼
┌─────────────────────────────────┐
│  Azure DevOps MCP Container     │
│                                 │
│  - Exposes stdio interface      │
│  - Communicates with Azure APIs │
└─────────────────────────────────┘
```

## docker-compose-with-openclaw.yml

This is an example showing how to run both containers together:

```yaml
version: '3.8'

services:
  # Azure DevOps MCP Server
  azure-devops-mcp:
    build: .
    container_name: azure-devops-mcp
    environment:
      - AZURE_DEVOPS_ORG=${AZURE_DEVOPS_ORG}
      - AZURE_DEVOPS_PROJECT=${AZURE_DEVOPS_PROJECT}
      - AZURE_DEVOPS_PAT=${AZURE_DEVOPS_PAT}
    stdin_open: true
    tty: true
    restart: unless-stopped
    networks:
      - mcp-network

  # OpenClaw (example MCP client)
  openclaw:
    image: openclaw:latest  # Replace with your OpenClaw image
    container_name: openclaw
    volumes:
      - ./openclaw-config:/config
      - ./workspace:/workspace
    environment:
      - MCP_CONFIG=/config/mcp-servers.json
    depends_on:
      - azure-devops-mcp
    networks:
      - mcp-network
    ports:
      - "3000:3000"  # Adjust based on your needs

networks:
  mcp-network:
    driver: bridge
    name: mcp-network
```

## MCP Configuration for OpenClaw

Save this as `openclaw-config/mcp-servers.json`:

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
      ],
      "env": {}
    }
  }
}
```

## Usage

1. **Start both containers:**
   ```bash
   docker compose -f docker-compose-with-openclaw.yml up -d
   ```

2. **Verify MCP server is accessible:**
   ```bash
   # Test the MCP server from OpenClaw container
   docker exec openclaw docker exec -i azure-devops-mcp python3 /app/server.py <<EOF
   {"jsonrpc":"2.0","id":1,"method":"tools/list"}
   
   EOF
   ```

3. **Use via OpenClaw:**
   - OpenClaw will automatically discover and use the Azure DevOps tools
   - You can ask: "List all branches in the MyRepo repository"
   - Or: "Create a new branch called feature/update-docs from main"

## Alternative: Using Docker Networks

If your OpenClaw is already running, you can connect it to the MCP network:

```bash
# Start the Azure DevOps MCP server
docker compose up -d

# Connect OpenClaw to the same network
docker network connect mcp-network openclaw-container-name

# Update OpenClaw's MCP config to use the server
```

## Testing the Connection

From within the OpenClaw container:

```bash
# Enter OpenClaw container
docker exec -it openclaw bash

# Test MCP server
docker exec -i azure-devops-mcp python3 /app/server.py <<EOF
{"jsonrpc":"2.0","id":1,"method":"tools/list"}

EOF
```

You should see a JSON response listing all available tools.

## Troubleshooting

### Container can't communicate

Check that both containers are on the same network:
```bash
docker network inspect mcp-network
```

### stdin/stdout issues

Ensure the MCP server container has `stdin_open: true` and `tty: true` in docker-compose.yml.

### Authentication errors

Verify environment variables are set correctly:
```bash
docker exec azure-devops-mcp env | grep AZURE_DEVOPS
```

## Security Notes

- Never commit `.env` file with real credentials
- Use Docker secrets for production deployments
- Rotate PAT tokens regularly
- Limit PAT permissions to only what's needed
