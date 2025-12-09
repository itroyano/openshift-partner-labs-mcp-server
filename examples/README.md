# MCP Client Examples

Ready-to-use client examples for connecting to the OpenShift Partner Labs MCP server with different frameworks.

## 📁 **Client Examples**

- `fastmcp_client.py` - Direct FastMCP client connection
- `langgraph_client.py` - LangGraph integration with tool orchestration

## 🚀 **Quick Start**

### **1. FastMCP Client (Simple)**
```bash
# Install dependencies
pip install fastmcp httpx

# Run the example
python examples/fastmcp_client.py
```

**Use case**: Direct tool testing, simple integrations, debugging

### **2. LangGraph Client (Advanced)**
```bash
# Install dependencies
pip install langgraph httpx

# Run the example
python examples/langgraph_client.py
```

**Use case**: Complex workflows, agent orchestration, production systems

## 🔧 **Configuration**

**Update connection settings for your deployment:**

```python
# Both files - update these URLs
server_url = "http://localhost:8000/mcp"      # Local development
# server_url = "http://0.0.0.0:8000/mcp"     # Local development (all interfaces)
# server_url = "https://openshift-partner-labs-mcp-server.apps.cluster.com/mcp"  # Production OpenShift
```

## 📋 **What Each Example Shows**

### **FastMCP Client:**
- ✅ Basic server connection
- ✅ Tool discovery and listing
- ✅ Direct tool execution
- ✅ Error handling
- ✅ Response parsing

### **LangGraph Client:**
- ✅ Agent workflow orchestration
- ✅ Multi-tool coordination
- ✅ State management
- ✅ Complex business logic
- ✅ Production-ready patterns

## 🎯 **OpenShift Partner Labs Tools**

**Example lab management operations:**

```python
# Create a new lab
result = await client.call_tool("create_lab", {
    "generated_name": "partner-lab-demo",
    "cluster_name": "ocp-partner-demo",
    "openshift_version": "4.20.0",
    "cluster_size": "medium",
    "request_type": "general",
    "cloud_provider": "AWS",
    "primary_first": "Jane",
    "primary_last": "Doe",
    "primary_email": "jane.doe@partner.com",
    "secondary_first": "John",
    "secondary_last": "Smith",
    "secondary_email": "john.smith@partner.com",
    "region": "na1",
    "project_name": "demo-project",
    "lease_time": "1w",
    "description": "Partner demonstration lab",
    "notes": "Initial setup for partner onboarding",
    "start_date": "2024-12-01 09:00:00",
    "end_date": "2024-12-08 17:00:00",
    "company_name": "Acme Corp"
})

# Approve the lab (triggers cluster creation)
approval = await client.call_tool("approve_lab", {
    "generated_name": "partner-lab-demo"
})

# List all labs for a company
company_labs = await client.call_tool("get_company_labs", {
    "company_name": "Acme Corp"
})

# Create a new partner company
company = await client.call_tool("create_company", {
    "company_name": "New Partner Inc",
    "curated": 0  # 0=no, 1=yes
})
```

## 🔍 **Testing Your Server**

```bash
# Test server health first
curl http://localhost:8000/health

# Run client examples to verify lab management integration
python examples/fastmcp_client.py
python examples/langgraph_client.py

# Test specific lab management endpoints
curl http://localhost:8000/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{"method": "list_tools", "params": {}}'
```

## 📚 **Learn More**

- **FastMCP**: Simple, direct MCP connections
- **LangGraph**: Advanced agent workflows and orchestration
- **MCP Protocol**: https://modelcontextprotocol.io/
