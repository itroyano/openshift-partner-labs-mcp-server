# MCP Tools Directory

All MCP server capabilities are implemented as **tools** for maximum compatibility with AI agents.

## 🔧 **Tool Development Guidelines**

### **Required Tool Documentation Format**

**CRITICAL**: All tools MUST use this structured format for agent compatibility:

```python
def your_tool_function(
    input_param: str,
    optional_param: str = "default"
) -> Dict[str, Any]:
    """
    TOOL_NAME=your_tool_function
    DISPLAY_NAME=Human-Readable Tool Name
    USECASE=When/why to use this tool (specific scenarios)
    INSTRUCTIONS=Step-by-step usage guide for agents
    INPUT_DESCRIPTION=Expected data format with examples
    OUTPUT_DESCRIPTION=What format you'll receive back
    EXAMPLES=your_tool_function("example_input", "optional_value")
    PREREQUISITES=What to do first (workflow sequence)
    RELATED_TOOLS=Other tools to use with this one

    Traditional docstring for developers goes here...
    """
    try:
        # Input validation
        if not input_param:
            raise ValueError("input_param is required")

        # Your business logic here
        result = process_input(input_param, optional_param)

        return {
            "status": "success",
            "operation": "your_operation",
            "result": result,
            "message": "Operation completed successfully"
        }

    except Exception as e:
        return {
            "status": "error",
            "operation": "your_operation",
            "error": str(e),
            "message": "Operation failed"
        }
```

### **Tool Registration**

Add your tool to `../mcp.py`:

```python
# Import your tool
from openshift_partner_labs_mcp_server.src.tools.your_tool import your_tool_function

# Register in _register_mcp_tools()
self.mcp.tool()(your_tool_function)
```

## 📋 **Current Tools**

### **Core Lab Management** (`lab_tools.py`)
- `create_lab` - Create new OpenShift Partner Lab requests
- `approve_lab` - Approve lab requests and initiate cluster creation via ACM
- `deny_lab` - Deny lab requests with documented reasoning
- `complete_lab` - Complete labs and clean up cluster resources
- `extend_lab` - Extend lab duration beyond original end date
- `get_lab_status` - Retrieve detailed lab information and status
- `list_labs` - List labs with comprehensive filtering and pagination

### **Company Management** (`company_tools.py`)
- `create_company` - Create new partner companies in the system
- `get_company` - Retrieve company information by name
- `list_companies` - List companies with pagination and filtering
- `get_company_labs` - Retrieve labs associated with specific companies
- `mark_company_curated` - Manage curated partner status

### **Cluster Operations** (`cluster_tools.py`)
- `create_cluster` - Create OpenShift clusters via ACM
- `delete_cluster` - Delete clusters and clean up resources
- `hibernate_cluster` - Put clusters into hibernation mode
- `resume_cluster` - Resume hibernated clusters
- `get_cluster_status` - Get current cluster status from ACM

### **Database Queries** (`database_tools.py`)
- `query_labs` - Execute custom lab queries with filters
- `query_companies` - Execute custom company queries
- `get_lab_stats` - Get lab statistics and summaries
- `get_company_stats` - Get company statistics and summaries

### **Utility Tools**
- `multiply_tool.py` - Basic arithmetic operations for capacity planning
- `code_review_tool.py` - Generate code review prompts
- `redhat_logo_tool.py` - Red Hat branding asset retrieval

## ✅ **Best Practices**

1. **Consistent Returns**: Always return `Dict[str, Any]` with `status` field
2. **Error Handling**: Wrap in try/catch, return structured errors
3. **Input Validation**: Validate all inputs before processing
4. **Logging**: Use `from openshift_partner_labs_mcp_server.utils.pylogger import get_python_logger`
5. **Testing**: Add tests to `../../tests/test_tools.py`

## 🎯 **Agent-Friendly Tips**

- Use **clear, action-oriented names** (`generate_report` not `report_generator`)
- Include **concrete examples** in EXAMPLES field
- Specify **prerequisites** for workflow guidance
- List **related tools** to help agents chain operations
- Keep **error messages** descriptive but concise
