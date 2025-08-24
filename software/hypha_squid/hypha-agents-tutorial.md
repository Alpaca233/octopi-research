# Hypha Agent Creation Tutorial: A Beginner's Guide

<img src="https://agents.aicell.io/logo.png" width="320" alt="Hypha">

Welcome to the complete beginner's guide for creating Hypha Agents! This tutorial will walk you through everything you need to know to build your own AI assistant that can use external tools and interact with the Hypha platform ecosystem.

## 📚 Table of Contents
- [What You'll Learn](#what-youll-learn)
- [Prerequisites](#prerequisites)
- [Understanding Key Concepts](#understanding-key-concepts)
- [Part 1: Creating Your First Hypha Agent](#part-1-creating-your-first-hypha-agent)
- [Part 2: Adding External Tools](#part-2-adding-external-tools)
- [Part 3: Advanced Tool Integration with Pydantic](#part-3-advanced-tool-integration-with-pydantic)
- [Part 4: Cleaner Tool Definition with @schema_function](#part-4-cleaner-tool-definition-with-schema_function)
- [Troubleshooting](#troubleshooting)

---

## 🎯 What You'll Learn

By the end of this tutorial, you will be able to:

- Understand the Hypha platform architecture and core concepts
- Create a basic hypha agent from scratch
- Connect external tools (like a calculator) to your agent using Hypha-RPC
- Use Pydantic to create more sophisticated tool integrations
- Use `@schema_function` to define tools with modern best practices
- Debug common issues and troubleshoot problems
- Understand the architecture of hypha agents and tool services
- Build agents that can operate within Hypha's virtual workspace ecosystem

## 📋 Prerequisites

### Required Software

Before starting, make sure you have:
- **Python 3.8 or higher** installed on your computer
- **pip** (Python package installer) 
- Access to the **Hypha Agent Lab** interface
- A **web browser** (Chrome, Firefox, Safari, or Edge)

### Required Knowledge

This tutorial assumes you have:

- Basic familiarity with Python programming
- Understanding of how to run Python scripts
- Basic knowledge of using command line/terminal

### Installation Check

To verify your setup, open a terminal/command prompt and run:
```bash
python --version
pip --version
```
You should see version numbers for both commands.

---

## 🧠 Understanding Key Concepts

Before we dive in, let's understand the key concepts specific to building agents in the Hypha ecosystem:

### 🌟 What is Hypha?

**Hypha** is a generative AI-powered application framework designed for large-scale data management, AI model serving, and real-time communication. Hypha allows the creation of computational platforms consisting of both computational and user interface components.

#### **Key Features of Hypha**

- **Generative AI-Powered:** Leverage the power of generative AI to build advanced data management and AI model serving solutions.
- **Hypha-RPC:** Utilize [hypha-rpc](https://github.com/oeway/hypha-rpc), a bidirectional remote procedure call system, enabling seamless communication and integration across distributed components.
- **Real-Time Communication:** Support for real-time communication within virtual workspaces, similar to platforms like Zoom.
- **Scalable and Flexible:** Connect and orchestrate various compute services, AI models, tools, and services running on distributed locations.
- **GenAI-Powered Automation:** Build GenAI-powered automation platforms and agentic workflows, enabling fully autonomous agent systems.

**How Hypha Works**:

Hypha acts as a hub that connects different components through **Hypha-RPC**. Users and programmatic clients connect to the platform in virtual workspaces, where they can seamlessly make remote procedure calls (RPC) as if they are calling local functions. Developers can integrate all types of compute services, including AI models, tools, and services, across distributed locations.


**Virtual Workspaces**:

- Hypha's virtual workspaces are akin to Zoom rooms, where clients (users and programmatic) can connect and interact.
- Within these workspaces, all clients can perform seamless RPCs, facilitating easy and efficient collaboration and computation.
- Each workspace provides an isolated environment for your agents and services to operate.

#### Integration with Compute Services

- Hypha supports the integration of various compute services, including AI models and data analytics tools.
- These services, when connected to the platform, can be understood and orchestrated by large language models (LLMs), paving the way for creating next-generation GenAI-powered automation platforms and agentic workflows.
- External tools and services can be easily connected and made available to your AI agents.

**Hypha-RPC** is the backbone communication system that enables:
- **Bidirectional Communication**: Services can call each other seamlessly
- **Distributed Computing**: Connect services running on different machines
- **Real-time Interaction**: Live communication between agents and services
- **Platform Integration**: Easy integration of diverse computational components
- **Workspace Collaboration**: Multiple clients working together in virtual environments

**Hypha services** are external tools or functions that your agent can call through the Hypha-RPC system. They:

- Run independently as distributed microservices
- Can be shared across different agents and workspaces
- Provide specific capabilities (calculations, data processing, AI models, etc.)
- Are discoverable and callable through the Hypha platform
- Enable agents to access computational resources beyond their local environment

### What are Hypha Agents?

**Hypha Agents** are AI-powered assistants that operate within the Hypha platform ecosystem. They can:

- Interact with users through natural language
- Execute code and perform computations
- Connect to external tools and services via Hypha-RPC
- Operate within virtual workspaces alongside other agents and services
- Access distributed computational resources

### What is the Hypha Agent Lab?

The **Hypha Agent Lab** is a Jupyter notebook-like interface available at [https://agents.aicell.io/#/lab](https://agents.aicell.io/#/lab) where you can create and test your agent using code/markdown cells. It provides:

- **Interactive Development**: Real-time agent creation and testing
- **Code Execution**: Live Python code execution with immediate feedback
- **Agent Configuration**: System-level agent setup and tool integration
- **Collaborative Environment**: Share and collaborate on agent development

### What is a Hypha Agent System Configuration?

The **system configuration** is where you:

- Define your agent's personality and capabilities
- Initialize and connect to external tools and services
- Provide tool usage instructions and guidelines
- Set up the agent's operational parameters
- Configure the agent's behavior within the Hypha ecosystem

This is the foundational cell that determines how your agent will behave and what tools it can access within the Hypha platform.

---

## 🚀 Part 1: Creating Your First Hypha Agent

Let's start by creating a simple agent that can introduce itself.

### Step 1: Access the Hypha Agent Lab
1. Open your web browser
2. Navigate to the Hypha Agent Lab at [https://agents.aicell.io/#/lab](https://agents.aicell.io/#/lab)
3. Create a new chat session or open an existing one

Before you can start chatting with your agent, you need to configure the language model:

1. **Look for the robot icon (🤖)** in the lower right corner of the Agent Lab interface
2. **Click the robot icon** to open the LLM configuration panel
3. **Choose your LLM provider**:
   - **For OpenAI**: 
     - Select "OpenAI" as the provider
     - Enter your OpenAI API token
     - Select a model like "gpt-4o"
   - **For Ollama** (local models):
     - Select "Ollama" as the provider
     - Connect to your existing Ollama service
     - Choose from available local models
4. **Save your configuration** by clicking "Apply" or "Save"

**Note**: You'll need either an OpenAI API key or a running Ollama instance to proceed with the tutorial.


### Step 2: Create the System Configuration

A system configuration tells your agent who it is and how to behave.

1. **Create a new code cell** in your chat session
2. **Paste the following code**:

```python
print("You are a helpful assistant, your name is Bee.")
```

**What this code does:**
- The `print()` statement defines your agent's basic identity
- This message will be used as the agent's system prompt

3. **Change the cell type to "System"**:
   - Look for a user icon (👤) on the left side of the cell
   - Click it to change the cell role from "User" to "System"

4. **Run the cell**:
   - Press `Shift + Enter` or click the "Run" button
   - You should see the output: `You are a helpful assistant, your name is Bee.`

### Step 3: Test Your Agent

Now let's test if your agent works:

1. **Find the input box** at the bottom of the chat session
2. **Type a test message**: `What is your name?`
3. **Press "Send"** or hit Enter
4. **Expected response**: `I am Bee, a helpful assistant.`

🎉 **Congratulations!** You've created your first Hypha agent!

### Step 4: Save Your Work

To save your progress:

1. **Set the system cell role and hide it**:
   - Make sure your system cell is set to "System" role (click the user icon 👤 to change it)
   - Click the "Hide" button on the system cell to hide it from users
2. **Quick save**: Press `Ctrl + S` (Windows/Linux) or `Cmd + S` (Mac)
3. **Export**: Click the "Download" button in the top toolbar to export your chat session

### 💡 Pro Tips for Basic Agents

**Hiding System Configuration:**
- Always set your system configuration cells to "System" role by clicking the user icon (👤)
- Click the "Hide" button on system cells so users don't see your agent's internal configuration
- This keeps your agent's setup clean and professional

**Improving Your Agent's Personality:**
Try replacing the basic system message with something more detailed:

## 🔧 Part 2: Adding External Tools

Now let's make your agent more powerful by connecting external tools. We'll create a calculator service that your agent can use.

### Why Use External Tools?

External tools allow your agent to:
- Perform complex calculations accurately
- Access real-time data
- Interact with other systems
- Extend capabilities beyond language generation

### Step 1: Install Required Dependencies

First, we need to install the `hypha-rpc` package:

1. **Open your terminal/command prompt**
2. **Run the installation command**:
```bash
pip install hypha-rpc
```
3. **Verify installation**:
```bash
pip show hypha-rpc
```

### Step 2: Create the Calculator Service

Now we'll create a Python script that provides calculation functionality.

1. **Create a new file** called `calculator_service.py`:
2. **Copy and paste the following code**:

```python
import asyncio
from hypha_rpc import connect_to_server

async def start_server(server_url):
    # Connect to the Hypha server
    server = await connect_to_server({"server_url": server_url})

    def calculate(expression):
        """
        Evaluate a mathematical expression and return the result
        Example: "2 + 3 * 4" returns 14
        
        Args:
            expression (str): Mathematical expression to evaluate
            
        Returns:
            str: Result of the calculation or error message
        """
        # Safely evaluate the mathematical expression
        # We restrict available functions for security
        result = eval(expression, {"__builtins__": {}}, {"abs": abs, "round": round})
        return f"Result of {expression} = {result}"

    # Register our service with Hypha
    svc = await server.register_service({
        "name": "Calculator Service",
        "id": "calculator",
        "config": {
            "visibility": "public"  # Makes the service available to other users
        },
        "calculate": calculate  # Expose our calculate function
    })

    # Print service information for debugging
    print(f"Calculator service registered at workspace: {server.config.workspace}, id: {svc.id}")
    print(f'You can use this service using the service id: {svc.id}')
    print(f"You can also test the service via the HTTP proxy: {server_url}/{server.config.workspace}/services/{svc.id.split('/')[1]}/calculate?expression=2+3*4")

    # Keep the server running indefinitely
    await server.serve()

if __name__ == "__main__":
    # Replace this URL with your actual Hypha server URL
    server_url = "https://hypha.aicell.io"
    asyncio.run(start_server(server_url))
```

### Step 3: Run the Calculator Service

1. **Open terminal/command prompt**
2. **Navigate to the directory** containing `calculator_service.py`
3. **Run the service**:
```bash
python calculator_service.py
```

**Expected Output:**
```
Calculator service registered at workspace: ws-user-capable-raccoon-57051682, id: ws-user-capable-raccoon-57051682/2dk9AVHUyDW5waJsrJQnW9:calculator
You can use this service using the service id: ws-user-capable-raccoon-57051682/2dk9AVHUyDW5waJsrJQnW9:calculator
You can also test the service via the HTTP proxy: https://hypha.aicell.io/ws-user-capable-raccoon-57051682/services/2dk9AVHUyDW5waJsrJQnW9/calculate?expression=2+3*4
```

**Important:** 
- Keep this terminal window open! The service needs to keep running
- Copy the **service ID** (the part that looks like `ws-user-xxxxx/xxxxxxxxxx:calculator`) - you'll need it in the next step

### Step 4: Connect the Service to Your Agent

Now let's modify your agent to use the calculator service.

1. **Go back to your Hypha Agent Lab**
2. **Modify your system configuration cell** with this code:

```python
import micropip

# Install hypha-rpc in the chat session environment
await micropip.install(["hypha-rpc"])

from hypha_rpc import connect_to_server

# Connect to the same Hypha server
server = await connect_to_server({"server_url": "https://hypha.aicell.io"})

# Connect to your calculator service
# REPLACE the service ID below with your actual service ID from Step 3
calculator_service = await server.get_service("ws-user-capable-raccoon-57051682/2dk9AVHUyDW5waJsrJQnW9:calculator")

# Define your agent's role and capabilities
print("You are a helpful assistant that can perform mathematical calculations.")
print("You can use the calculator service by calling `result = await calculator_service.calculate(expression)` where expression is a mathematical expression like '2 + 3 * 4'")
print("Always use the calculator for any mathematical operations instead of doing them manually.")
```

3. **Run this cell** by pressing `Shift + Enter`

### Step 5: Test the Calculator Service

Before testing with your agent, let's make sure the service connection works:

1. **Create a new code cell**
2. **Add this test code**:
```python
result = await calculator_service.calculate("2 + 3 * 4")
print(result)
```
3. **Run the cell**
4. **Expected output**: `Result of 2 + 3 * 4 = 14`

If you see an error, check the [Troubleshooting](#troubleshooting) section.

### Step 6: Test Your Enhanced Agent

Now test your agent with calculations:
1. **Set the system cell role and hide it**:
   - Make sure your system cell is set to "System" role (click the user icon 👤 to change it)
   - Click the "Hide" button on the system cell to hide it from users
2. **In the chat input box**, type: `What is the result of 4983*234 + (2^5)?`
3. **Send the message**
4. **You should see**:
   - Your agent generates code to use the calculator
   - The calculation results appear
   - Final answer: `The result of the expression 4983*234 + (2^5) is 1,166,029.`

### Step 7: Save Your Enhanced Agent

Save your work:
1. **Press `Ctrl + S`** to save
2. **Export** using the Download button
3. **Name your file**: `bee_agent_with_calculator_tool.ipynb`

🎉 **Excellent!** You now have an agent that can use external tools!

---

## 🔬 Part 3: Advanced Tool Integration with Pydantic

In the previous section, we manually wrote instructions for our agent. Now we'll learn how to use **Pydantic** to automatically generate tool schemas and instructions.

### Why Use Pydantic?

**Pydantic** helps us:
- Define clear tool interfaces
- Automatically generate documentation
- Validate inputs and outputs
- Create better error messages
- Make tools more maintainable

### Step 1: Create an Advanced Calculator Service

Create a new file called `annotated_calculator_service.py`:

```python
from enum import Enum
from typing import Union
from pydantic import BaseModel, Field
from hypha_rpc import connect_to_server
import asyncio
import math

# Define allowed operations using an Enum
class OperationType(str, Enum):
    """Enumeration of supported calculator operations"""
    ADD = "+"
    SUBTRACT = "-"
    MULTIPLY = "*"
    DIVIDE = "/"

# Define the tool structure using Pydantic
class CalculatorTool(BaseModel):
    """
    Calculator tool for performing mathematical operations
    
    Supports basic arithmetic operations: addition, subtraction, 
    multiplication, and division.
    """
    operation: OperationType = Field(
        ..., 
        description="The mathematical operation to perform (+, -, *, or /)"
    )
    x: float = Field(
        ..., 
        description="First number for the operation"
    )
    y: float = Field(
        ..., 
        description="Second number for the operation"
    )

# The actual calculator function
def calculator(config):
    """
    Perform a mathematical calculation
    
    Args:
        config (dict): Dictionary containing operation, x, and y
        
    Returns:
        float: Result of the calculation
    """
    operation = config.get("operation")
    x = config.get("x")
    y = config.get("y")
    
    # Perform the calculation based on operation
    if operation == "+":
        return x + y
    elif operation == "-":
        return x - y
    elif operation == "*":
        return x * y
    elif operation == "/":
        if y == 0:
            raise ValueError("Cannot divide by zero")
        return x / y
    else:
        raise ValueError(f"Unsupported operation: {operation}")

def get_schema():
    """
    Generate the JSON schema for the calculator tool
    
    Returns:
        dict: A dictionary containing the JSON schema
    """
    return {
        "calculator": CalculatorTool.model_json_schema()
    }

# Define the complete extension
calculator_extension = {
    "id": "annotated-calculator-extension",
    "type": "hypha-chatbot-extension",
    "name": "Calculator",
    "description": "A versatile calculator extension for the Hypha Chatbot with support for various mathematical operations",
    "get_schema": get_schema,
    "tools": {
        "calculator": calculator
    },
    "config": {"visibility": "public"},
    "info": {
        "calculator": {
            "name": "calculator", 
            "description": "Performs basic mathematical calculations", 
            "reference": "https://en.wikipedia.org/wiki/Calculator"
        }
    }
}

async def start_server(server_url):
    """Start the annotated calculator service"""
    server = await connect_to_server({"server_url": server_url})

    svc = await server.register_service(calculator_extension)
    print(f"Calculator service registered at workspace: {server.config.workspace}, id: {svc.id}")
    print(f'You can use this service using the service id: {svc.id}')
    print(f"Service URL: {server_url}/{server.config.workspace}/services/{svc.id}")

    # Keep the server running
    await server.serve()

if __name__ == "__main__":
    server_url = "https://hypha.aicell.io"
    asyncio.run(start_server(server_url))
```

### Step 2: Run the Advanced Service

1. **Stop the previous calculator service** (Ctrl+C in the terminal)
2. **Run the new service**:
```bash
python annotated_calculator_service.py
```
3. **Copy the new service ID** that appears in the output


### Step 3: Connect to the Advanced Service and Test the Schema

Create a new cell to examine the automatically generated schema:

```python
import json
import micropip

# Install required packages
await micropip.install(["hypha-rpc"])
from hypha_rpc import connect_to_server

# Connect to server
server = await connect_to_server({"server_url": "https://hypha.aicell.io"})

# Connect to the annotated calculator service
# REPLACE with your actual service ID
calculator_extension = await server.get_service("ws-user-capable-raccoon-57051682/SwqeFiN2UjJum:annotated-calculator-extension")
annotation = await calculator_extension.get_schema()
print("Generated Tool Schema:")
print(json.dumps(annotation, indent=2))
```

**Expected Output:**
```json
{
  "calculator": {
    "$defs": {
      "OperationType": {
        "description": "Enumeration of supported calculator operations",
        "enum": ["+", "-", "*", "/"],
        "title": "OperationType",
        "type": "string"
      }
    },
    "description": "Calculator tool for performing mathematical operations...",
    "properties": {
      "operation": {
        "allOf": [{"$ref": "#/$defs/OperationType"}],
        "description": "The mathematical operation to perform (+, -, *, or /)"
      },
      "x": {
        "description": "First number for the operation",
        "title": "X",
        "type": "number"
      },
      "y": {
        "description": "Second number for the operation", 
        "title": "Y",
        "type": "number"
      }
    },
    "required": ["operation", "x", "y"],
    "title": "CalculatorTool",
    "type": "object"
  }
}
```

Next we will try to for the schema along with the tool usage instructions and print it in the system cell.

### Step 4: Configure Your Agent with Tool Instructions

Update your system configuration in the Hypha Agent Lab:

````python
import json
import micropip

# Install required packages
await micropip.install(["hypha-rpc"])
from hypha_rpc import connect_to_server

# Connect to server
server = await connect_to_server({"server_url": "https://hypha.aicell.io"})

# Connect to the annotated calculator service
# REPLACE with your actual service ID
calculator_extension = await server.get_service("ws-user-capable-raccoon-57051682/SwqeFiN2UjJum:annotated-calculator-extension")

# Get tools and schema
tools = calculator_extension.tools
tools_schema = await calculator_extension.get_schema()
tools_schema_json = json.dumps(tools_schema, indent=2)

# Define agent role and capabilities
print("You are a helpful assistant.") # Role definition

print(f"""You can use the tools defined below to help answer questions.
Here are the available tool functions with their arguments schema:
```json
{tools_schema_json}
```
These tools are accessible from the variable `tools`.
For example, to use the calculator tool:
```python
result = await tools.calculator({{"operation": "+", "x": 5, "y": 3}})
```
""") # Tool schema and usage instructions

print("""⚠️ **Important guidelines**:
- Always use the calculator tool for mathematical operations
- Do not perform calculations manually
- Only use supported operations (+, -, *, /)
- Make sure to provide both x and y values as numbers
""")  # Additional guidelines
````

Run the above cell and you will see the tool schema and usage instructions in the system cell.

> **📋 Important Note:** Read the output of the cell carefully and you will see the tool schema and usage instructions. You should think as if you are the agent and check if the instructions are correct and informative.


Now you can set the system cell role and hide it:
   - Make sure your system cell is set to "System" role (click the user icon 👤 to change it)
   - Click the "Hide" button on the system cell to hide it from users

### Step 5: Test Your Advanced Agent

Try your enhanced agent with complex calculations:

**Test Message 1:**
```
What is 4983 * 234 + (2^5)?
```

**Test Message 2:**
```
If I have 150 items and I want to divide them equally among 12 people, how many items does each person get?
```

You should see your agent:

1. Break down complex expressions into individual operations
2. Use the calculator tool for each operation
3. Combine results to give final answers

### 📝 Best Practices for Creating Hypha Agent Prompts

When creating an agent prompt in the system configuration, make sure your prompt is informative and helpful. Your prompt should contain the following information:

**1. Role Definition:**

- Clearly define what the agent is (general purpose, specialized, etc.)
- Specify domains of expertise
- List tasks it can help with
- Define limitations and boundaries

**2. Tool Schema and Usage Instructions:**

- List all available tools and their purposes
- Show exact syntax and format for calling each tool
- Include example usage with sample inputs/outputs
- Explain required parameters and configurations
- Document error handling and edge cases

**3. Additional Guidelines:**

- Provide best practices and usage patterns
- Warn about common pitfalls
- Include performance considerations
- Add security guidelines if applicable
- Link to further documentation
- List known limitations or restrictions

---

## 🧪 Part 4: Cleaner Tool Definition with `@schema_function`

In this section, you'll learn a **modern and elegant** way to define tools for your Hypha agent using the `@schema_function` decorator from `hypha-rpc`. This method simplifies tool creation, improves maintainability, and makes integration with large language models seamless.

### 🧠 What is `@schema_function`?

The `@schema_function` decorator is a **useful utility of the hypha framework** that automatically generates JSON schemas for your Python functions, making them compatible with Large Language Models (LLMs) and AI agents.

**Key Features:**

- **Automatic Schema Generation**: Converts Python type hints into JSON schemas
- **LLM Integration**: Creates function calling schemas compatible with OpenAI and other LLM providers
- **Type Safety**: Leverages Python's type system and Pydantic models
- **Zero Boilerplate**: Eliminates manual schema writing

For comprehensive documentation and advanced usage patterns, see the [Hypha Service Type Annotation Guide](https://docs.amun.ai/#/service-type-annotation).

### 🧠 Why Use `@schema_function`?

Previously, defining tools involved:

- Creating separate Pydantic models
- Writing a `get_schema()` function manually
- Accepting inputs as `dict` objects
- Verbose configuration

With `@schema_function`, you can:

✅ Eliminate boilerplate (`get_schema()` not needed)  
✅ Use **typed keyword arguments** instead of dicts  
✅ Automatically expose the schema via `__schema__`  
✅ Enable **native function calling** in LLMs with minimal code  
✅ Write **cleaner, more maintainable** services

### How to use `@schema_function`

To use `@schema_function`, you need to import the `schema_function` decorator from `hypha_rpc.utils.schema`, then use it to decorate your tool function.

Importantly, you can define tool with `__doc__` string and pydantic `Field` object to specify the the arguments using the `description` parameter, and the schema will be generated automatically. See the example below:

```python
from pydantic import Field
from hypha_rpc.utils.schema import schema_function

@schema_function
def add(
    a: int = Field(..., description="first number"),
    b: int = Field(..., description="second number")
) -> int:
    """Add two numbers."""
    return a + b
```

You can verify the generated json schema by calling the `__schema__` property of the function:

```python
print(add.__schema__)
```

Or you can print the schema in a more readable format:

```python
print(json.dumps(add.__schema__, indent=2))
```

The output will be like this:

```json
{
  "name": "add",
  "description": "Add two numbers.",
  "parameters": {
    "properties": {
      "a": {
        "description": "first number",
        "type": "integer"
      },
      "b": {
        "description": "second number",
        "type": "integer"
      }
    },
    "required": [
      "a",
      "b"
    ],
    "type": "object"
  }
}
```

**For Class Methods**: If you're defining tools as methods within a class, use `@schema_method` instead of `@schema_function`:

```python
from pydantic import Field
from hypha_rpc.utils.schema import schema_method

class CalculatorService:
    @schema_method
    def add(
       self,
       a: int = Field(..., description="first number"),
       b: int = Field(..., description="second number")
    ) -> int:
        """Add two numbers."""
        return a + b
```

```python
print(CalculatorService.add.__schema__)
```

**When to Use Each:**

- `@schema_function`: For standalone functions
- `@schema_method`: For class methods and instance methods
- Both decorators provide the same automatic schema generation capabilities


### Step 1: Define the Tool Using `@schema_function`

Create a Python file named `modern_calculator.py` with the following content:

```python
from enum import Enum
from pydantic import Field
from hypha_rpc.utils.schema import schema_function
from hypha_rpc import connect_to_server
import asyncio

class Operation(str, Enum):
    ADD = "+"
    SUBTRACT = "-"
    MULTIPLY = "*"
    DIVIDE = "/"

@schema_function
def calculate(
    operation: Operation = Field(..., description="The operation to perform: +, -, *, or /"),
    a: float = Field(..., description="The first number"),
    b: float = Field(..., description="The second number")
) -> float:
    """Performs a basic arithmetic calculation."""
    if operation == Operation.ADD:
        return a + b
    elif operation == Operation.SUBTRACT:
        return a - b
    elif operation == Operation.MULTIPLY:
        return a * b
    elif operation == Operation.DIVIDE:
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b

async def main():
    server = await connect_to_server({"server_url": "https://hypha.aicell.io"})
    svc = await server.register_service({
        "id": "modern-calculator",
        "name": "Modern Calculator",
        "description": "A calculator tool using schema_function",
        "config": {
            "visibility": "public" # make the service public so it can be used by anyone
        },
        "calculate": calculate
    })
    
    print(f"Modern Calculator service registered at workspace: {server.config.workspace}, id: {svc.id}")
    print(f'You can use this service using the service id: {svc.id}')
    
    # Keep the server running
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
```

In the Hypha Agent Lab, create a new **Code** cell and paste the following:

1. **Run this script** in a terminal:

```bash
python modern_calculator.py
```

2. **Copy the service ID** shown in the terminal for the next step



### Step 2: Connect to the Tool and Check the Schema

In your Hypha Agent Lab, create a new **Code** cell, change the role to **System** and paste the following:

```python
import json
import micropip
await micropip.install("hypha-rpc")

from hypha_rpc import connect_to_server

# Connect to server
server = await connect_to_server({"server_url": "https://hypha.aicell.io"})

# Connect to your modern calculator tool
# REPLACE with your actual service ID from Step 1
tools = await server.get_service("ws-user-yourworkspace/your-service-id:modern-calculator")

result = await tools.calculate(operation="+", a=12, b=30)
print(result)  # Expected output: 42

# Get schema and format it nicely
calculator_schema = json.dumps(tools.calculate.__schema__, indent=2)
print(calculator_schema)
```

If you get the correct result, your tool is connected and functional, and you can see the schema of the tool in the output.

### Step 3: Configure Your Agent with Tool Instructions

Now you can configure your agent with tool instructions by following the structure of prompt in the previous part.

Here is an example:

````python
import json
import micropip
await micropip.install("hypha-rpc")

from hypha_rpc import connect_to_server

# Connect to server
server = await connect_to_server({"server_url": "https://hypha.aicell.io"})

# Connect to your modern calculator tool
# REPLACE with your actual service ID from Step 1
tools = await server.get_service("ws-user-yourworkspace/your-service-id:modern-calculator")

# Get schema and format it nicely
calculator_schema = json.dumps(tools.calculate.__schema__, indent=2)

# Define agent role and capabilities
print("You are a helpful AI assistant that performs calculations using external tools.")

# Provide tool schema and usage instructions
print(f"""
You have access to the following tools:
```json
{calculator_schema}
```
To use a tool, call:

```python
result = await tools.calculate(operation="+", a=3, b=5)
```
""")

# Provide additional guidelines
print("""⚠️ Important guidelines:
- Always use this tool for any mathematical operations
- Never do math manually
- Only use supported operations: +, -, *, /
- Avoid invalid input such as dividing by zero
""")
````

### 💡 Pro Tip: Managing Multiple Tools

When you have many tools available, you can use a for loop to automatically generate a formatted list of all tool schemas:

```python

all_tools = [tools.calculator, tools.weather, tools.news]
tool_schemas = [json.dumps(tool.__schema__) for tool in all_tools]

# Print all tool schemas in a formatted way
print("You have access to the following tools:")
for schema in tool_schemas:
    print(f" - {schema['name']}:\n```json\n{schema}\n```")
```

### Step 4: Putting It All Together

You now have:

- A **clean tool definition** using `@schema_function`
- A **registered Hypha service**
- An **Hypha agent** that can access and use the tool
- A fully formatted tool schema used in the agent's prompt

Make sure you configure the system cell with the role "System" and hide the content.

Try chatting with your agent in the Hypha Agent Lab:

**Test Message:**
```
What is 345 * 9 divided by 3?
```

You should see the agent:

1. Parse the request
2. Break it into operations
3. Call the `calculate()` tool
4. Respond with the correct result

### 💡 Advantages of `@schema_function`

**Comparison with Previous Methods:**

| Feature | Manual | Manual Pydantic | `@schema_function` |
|---------|----------------|----------------|-------------------|
| Boilerplate Code | Very High | High | Minimal |
| Schema Generation | None | Manual | Automatic |
| Function Signature | String-based | Dict-based | Native Python |
| Type Safety | Poor | Good | Excellent |
| Maintainability | Low | Medium | High |
| LLM Integration | Manual | Manual | Seamless |

**Key Benefits:**

- **Less Code**: Eliminate boilerplate schema generation
- **Better Types**: Use native Python type hints
- **Automatic Documentation**: Schema is generated from function signature
- **Easier Testing**: Test functions directly without service wrapper
- **Modern Approach**: Follows current best practices

### 💡 Pro Tips for Schema Functions

**For Class Methods**: If you're defining tools as methods within a class, use `@schema_method` instead of `@schema_function`:

```python
from hypha_rpc.utils.schema import schema_method

class CalculatorService:
    @schema_method
    def calculate(self, operation: Operation, a: float, b: float) -> float:
        """Performs a basic arithmetic calculation."""
        # ... implementation
```

**When to Use Each:**

- `@schema_function`: For standalone functions
- `@schema_method`: For class methods and instance methods
- Both decorators provide the same automatic schema generation capabilities

### 🚀 Summary of Part 4

✅ **Modern Tool Definition**: Use `@schema_function` for cleaner code  
✅ **Automatic Schema Generation**: No need for manual `get_schema()` functions  
✅ **Native Function Calls**: Use keyword arguments instead of dictionaries  
✅ **Reduced Boilerplate**: Focus on business logic, not configuration  
✅ **Better Maintainability**: Easier to read, test, and modify  
✅ **Seamless Integration**: Works perfectly with Hypha agents  

This cleaner, modern approach makes it easier to scale and maintain your agent's capabilities. You're now ready to build rich, powerful agents with professional tool integrations.

**Onward! 🚀**

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### Problem: "Module not found" error

**Solution:**
```bash
pip install hypha-rpc
# or for notebook environment:
await micropip.install(["hypha-rpc"])
```

#### Problem: Service connection fails

**Causes and Solutions:**

1. **Wrong service ID**: Double-check the service ID from terminal output
2. **Service not running**: Make sure the Python service script is still running
3. **Network issues**: Check your internet connection

#### Problem: Calculator gives wrong results

**Solution:**
- Check that you're using the correct syntax

- Verify that x and y are numbers, not strings
- Make sure the operation is one of: +, -, *, /

#### Problem: Agent doesn't use the calculator

**Possible causes:**
1. **System configuration not run**: Make sure you ran the system cell

2. **Instructions unclear**: Check that tool instructions are clear
3. **Service not connected**: Verify the service connection works

### Debugging Tips

1. **Test services independently** before connecting to agents
2. **Check terminal output** for error messages
3. **Use simple test cases** first
4. **Verify service IDs** are correct
5. **Keep service scripts running** in separate terminal windows

---

## 🚀 Next Steps

Congratulations! You've successfully created Hypha agents with external tools.

---

## 📋 Summary

In this tutorial, you learned:

✅ **Basic Agent Creation**: How to create a simple Hypha agent with personality  
✅ **External Tool Integration**: How to connect external services to your agent  
✅ **Service Development**: How to create and deploy Hypha services  
✅ **Advanced Tool Design**: How to use Pydantic for better tool interfaces  
✅ **Modern Schema Functions**: How to use `@schema_function` for cleaner tool definitions  
✅ **Best Practices**: How to structure prompts and handle errors  
✅ **Troubleshooting**: How to debug common issues  

You now have the foundation to build sophisticated AI agents that can interact with external tools and services. The possibilities are endless!

**Happy coding! 🎉**