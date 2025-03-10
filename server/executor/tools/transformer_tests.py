import json
from data_transform_tool import data_transform_tool

#=============================================================================
# MAP Transformation Test
#=============================================================================

# Test data for schema transformation
map_test_data = [
    {"first_name": "John", "last_name": "Doe", "dob": "1990-01-15", "salary": 75000},
    {"first_name": "Jane", "last_name": "Smith", "dob": "1985-07-22", "salary": 85000},
    {"first_name": "Alex", "last_name": "Johnson", "dob": "1992-11-30", "salary": 65000}
]

# Basic map transformation
basic_map_result = data_transform_tool(
    map_test_data,
    operation='map',
    template="""
    {
        "name": "{{first_name}} {{last_name}}",
        "birth_year": {{dob.split('-')[0]}},
        "tax": {{round(salary * 0.3, 2)}}
    }
    """
)

print("Basic Map Transformation:")
print(json.dumps(basic_map_result, indent=2))

# Advanced map transformation with conditional logic
advanced_map_result = data_transform_tool(
    map_test_data,
    operation='map',
    template="""
    {
        "person": {
            "fullName": "{{first_name}} {{last_name}}",
            "birthInfo": {
                "fullDate": "{{dob}}",
                "year": "{{dob.split('-')[0]}}",
                "month": "{{dob.split('-')[1]}}",
                "day": "{{dob.split('-')[2]}}"
            }
        },
        "financialData": {
            "income": {{salary}},
            "tax": {{round(salary * 0.3, 2)}},
            "netIncome": {{salary - round(salary * 0.3, 2)}},
            "taxBracket": "{% if salary > 80000 %}High{% elif salary > 70000 %}Medium{% else %}Standard{% endif %}"
        }
    }
    """
)

print("\nAdvanced Map Transformation with Conditional Logic:")
print(json.dumps(advanced_map_result, indent=2))

#=============================================================================
# FILTER Transformation Test
#=============================================================================

# Test data for filtering
filter_test_data = [
    {"name": "John", "age": 30, "department": "IT", "salary": 75000, "skills": ["Python", "SQL", "AWS"]},
    {"name": "Jane", "age": 25, "department": "HR", "salary": 60000, "skills": ["Communication", "Management"]},
    {"name": "Bob", "age": 35, "department": "IT", "salary": 85000, "skills": ["Java", "DevOps"]},
    {"name": "Alice", "age": 28, "department": "HR", "salary": 62000, "skills": ["Recruitment", "Training"]},
    {"name": "David", "age": 40, "department": "Finance", "salary": 90000, "skills": ["Accounting", "Excel"]},
    {"name": "Emily", "age": 32, "department": "Marketing", "salary": 72000, "skills": ["SEO", "Content Writing"]}
]

# Filter people in IT department
it_dept_filter = data_transform_tool(
    filter_test_data,
    operation='filter',
    filter_code="""
def filter_data(data):
    return [item for item in data if item.get('department') == 'IT']
"""
)

print("\nFilter - IT Department Only:")
print(json.dumps(it_dept_filter, indent=2))

# Filter people with high salary
high_salary_filter = data_transform_tool(
    filter_test_data,
    operation='filter',
    filter_code="""
def filter_data(data):
    return [item for item in data if item.get('salary', 0) >= 80000]
"""
)

print("\nFilter - High Salary (>= 80000):")
print(json.dumps(high_salary_filter, indent=2))

# Filter people with Python skills
python_skills_filter = data_transform_tool(
    filter_test_data,
    operation='filter',
    filter_code="""
def filter_data(data):
    return [item for item in data if 'Python' in item.get('skills', [])]
"""
)

print("\nFilter - Python Skills:")
print(json.dumps(python_skills_filter, indent=2))

# Complex filter condition
complex_filter = data_transform_tool(
    filter_test_data,
    operation='filter',
    filter_code="""
def filter_data(data):
    result = []
    for item in data:
        age = item.get('age', 0)
        dept = item.get('department', '')
        if age > 30 and ('IT' in dept or 'Finance' in dept):
            result.append(item)
    return result
"""
)

print("\nComplex Filter - Age > 30 AND (Department is IT OR Finance):")
print(json.dumps(complex_filter, indent=2))

#=============================================================================
# REDUCE Transformation Test
#=============================================================================

# Test data for reduce operations
reduce_test_data = [
    {"employee": "John", "department": "IT", "salary": 75000, "years_service": 5, "projects": ["CRM", "Website"]},
    {"employee": "Jane", "department": "IT", "salary": 82000, "years_service": 7, "projects": ["Mobile App", "API"]},
    {"employee": "Bob", "department": "HR", "salary": 65000, "years_service": 3, "projects": ["Recruitment"]},
    {"employee": "Alice", "department": "HR", "salary": 68000, "years_service": 4, "projects": ["Training", "Onboarding"]},
    {"employee": "David", "department": "Finance", "salary": 90000, "years_service": 8, "projects": ["Budgeting", "Reporting"]},
    {"employee": "Emily", "department": "Finance", "salary": 87000, "years_service": 6, "projects": ["Forecasting"]}
]

# Basic statistics reduce
basic_stats_reduce = data_transform_tool(
    reduce_test_data,
    operation='reduce',
    reduce_code="""
def reduce_data(data):
    total_salary = sum(item['salary'] for item in data)
    avg_salary = total_salary / len(data) if data else 0
    max_salary = max(item['salary'] for item in data) if data else 0
    min_salary = min(item['salary'] for item in data) if data else 0

    return {
        "total_employees": len(data),
        "total_salary": total_salary,
        "average_salary": avg_salary,
        "max_salary": max_salary,
        "min_salary": min_salary
    }
"""
)

print("\nBasic Statistics Reduce:")
print(json.dumps(basic_stats_reduce, indent=2))

# Department summary reduce using pure Python
dept_summary_reduce = data_transform_tool(
    reduce_test_data,
    operation='reduce',
    reduce_code="""
def reduce_data(data):
    # Group by department using Python dictionary
    departments = {}
    for item in data:
        dept = item['department']
        if dept not in departments:
            departments[dept] = {
                'employees': [],
                'salaries': [],
                'years': []
            }
        departments[dept]['employees'].append(item['employee'])
        departments[dept]['salaries'].append(item['salary'])
        departments[dept]['years'].append(item['years_service'])

    # Calculate summaries for each department
    result = {}
    for dept, values in departments.items():
        salaries = values['salaries']
        years = values['years']
        result[dept] = {
            'avg_salary': sum(salaries) / len(salaries) if salaries else 0,
            'total_salary': sum(salaries),
            'avg_years': sum(years) / len(years) if years else 0,
            'employee_count': len(values['employees'])
        }

    return result
"""
)

print("\nDepartment Summary Reduce:")
print(json.dumps(dept_summary_reduce, indent=2))

# All projects reduce
projects_reduce = data_transform_tool(
    reduce_test_data,
    operation='reduce',
    reduce_code="""
def reduce_data(data):
    # Extract all unique projects
    all_projects = set()
    for item in data:
        if 'projects' in item and isinstance(item['projects'], list):
            all_projects.update(item['projects'])

    return sorted(list(all_projects))
""",
    wrap_result=False
)

print("\nAll Projects Reduce:")
print(json.dumps(projects_reduce, indent=2))

# Graph generation from nodes and edges
graph_data = [
    {
        "type": "node",
        "id": "1",
        "label": "Alice",
        "properties": {"role": "Manager", "department": "IT"}
    },
    {
        "type": "node",
        "id": "2",
        "label": "Bob",
        "properties": {"role": "Developer", "department": "IT"}
    },
    {
        "type": "node",
        "id": "3",
        "label": "Charlie",
        "properties": {"role": "Designer", "department": "Marketing"}
    },
    {
        "type": "node",
        "id": "4",
        "label": "Diana",
        "properties": {"role": "Analyst", "department": "Finance"}
    },
    {
        "type": "edge",
        "source": "1",
        "target": "2",
        "label": "manages",
        "properties": {"since": "2022-01-15"}
    },
    {
        "type": "edge",
        "source": "1",
        "target": "3",
        "label": "collaborates",
        "properties": {"project": "Website Redesign"}
    },
    {
        "type": "edge",
        "source": "2",
        "target": "3",
        "label": "works_with",
        "properties": {"frequency": "daily"}
    },
    {
        "type": "edge",
        "source": "3",
        "target": "4",
        "label": "reports_to",
        "properties": {"for": "budget approval"}
    }
]

graph_result = data_transform_tool(
    graph_data,
    operation='reduce',
    reduce_code="""
def reduce_data(data):
    # Initialize graph structure
    graph = {
        "nodes": {},
        "edges": [],
        "metadata": {
            "node_count": 0,
            "edge_count": 0,
            "departments": set()
        }
    }

    # Process each item in the data
    for item in data:
        item_type = item.get('type')

        if item_type == 'node':
            node_id = item.get('id')
            if node_id:
                # Add node to graph
                graph["nodes"][node_id] = {
                    "id": node_id,
                    "label": item.get('label', f'Node {node_id}'),
                    "properties": item.get('properties', {}),
                    "connections": []
                }

                # Update metadata
                graph["metadata"]["node_count"] += 1

                # Add department to set if it exists
                dept = item.get('properties', {}).get('department')
                if dept:
                    graph["metadata"]["departments"].add(dept)

        elif item_type == 'edge':
            source = item.get('source')
            target = item.get('target')

            if source and target:
                edge = {
                    "source": source,
                    "target": target,
                    "label": item.get('label', 'connects'),
                    "properties": item.get('properties', {})
                }

                # Add edge to graph
                graph["edges"].append(edge)

                # Update metadata
                graph["metadata"]["edge_count"] += 1

                # Add connection to source node if it exists
                if source in graph["nodes"]:
                    graph["nodes"][source]["connections"].append(target)

                # Add connection to target node if it exists
                if target in graph["nodes"]:
                    graph["nodes"][target]["connections"].append(source)

    # Convert sets to lists for JSON serialization
    graph["metadata"]["departments"] = sorted(list(graph["metadata"]["departments"]))

    return graph
"""
)

print("\nGraph Generation:")
print(json.dumps(graph_result, indent=2))

#=============================================================================
# CHAIN Transformation Test
#=============================================================================

# Test data for chain transformation
chain_test_data = [
    {"name": "John", "age": 30, "department": "IT", "salary": 75000, "skills": ["Python", "SQL", "AWS"]},
    {"name": "Jane", "age": 25, "department": "HR", "salary": 60000, "skills": ["Communication", "Management"]},
    {"name": "Bob", "age": 35, "department": "IT", "salary": 85000, "skills": ["Java", "DevOps"]},
    {"name": "Alice", "age": 28, "department": "HR", "salary": 62000, "skills": ["Recruitment", "Training"]},
    {"name": "David", "age": 40, "department": "Finance", "salary": 90000, "skills": ["Accounting", "Excel"]},
    {"name": "Emily", "age": 32, "department": "Marketing", "salary": 72000, "skills": ["SEO", "Content Writing"]}
]

# Chain: Map -> Filter -> Reduce
map_filter_reduce_chain = data_transform_tool(
    chain_test_data,
    operation='chain',
    map_config={
        "template": """
        {
            "employee": "{{name}}",
            "department": "{{department}}",
            "salary_info": {
                "annual": {{salary}},
                "monthly": {{salary / 12}},
                "tax_rate": "{% if salary > 80000 %}0.35{% elif salary > 70000 %}0.30{% else %}0.25{% endif %}"
            }
        }
        """
    },
    filter_config={
        "filter_code": """
def filter_data(data):
    return [item for item in data if float(item.get('salary_info', {}).get('tax_rate', 0)) >= 0.3]
"""
    },
    reduce_config={
        "reduce_code": """
def reduce_data(data):
    # Calculate average salary for high-tax employees
    if not data:
        return {"count": 0, "avg_salary": 0}

    total_salary = sum(item.get('salary_info', {}).get('annual', 0) for item in data)
    return {
        "high_tax_employees_count": len(data),
        "average_salary": total_salary / len(data)
    }
"""
    }
)

print("\nChain: Map -> Filter -> Reduce:")
print(json.dumps(map_filter_reduce_chain, indent=2))

# Chain: Map -> Filter only
map_filter_chain = data_transform_tool(
    chain_test_data,
    operation='chain',
    map_config={
        "template": """
        {
            "full_name": "{{name}}",
            "department": "{{department}}",
            "age": {{age}},
            "skill_count": {{len(skills)}}
        }
        """
    },
    filter_config={
        "filter_code": """
def filter_data(data):
    return [item for item in data if item.get('skill_count', 0) >= 2]
"""
    }
)

print("\nChain: Map -> Filter only:")
print(json.dumps(map_filter_chain, indent=2))

# Chain: Filter -> Reduce only
filter_reduce_chain = data_transform_tool(
    chain_test_data,
    operation='chain',
    filter_config={
        "filter_code": """
def filter_data(data):
    return [item for item in data if item.get('age', 0) > 30]
"""
    },
    reduce_config={
        "reduce_code": """
def reduce_data(data):
    # Group people older than 30 by department
    departments = {}
    for item in data:
        dept = item.get('department', 'Unknown')
        if dept not in departments:
            departments[dept] = []
        departments[dept].append(item.get('name'))

    return {
        "older_employees_by_dept": departments,
        "total_count": len(data)
    }
"""
    }
)

print("\nChain: Filter -> Reduce only:")
print(json.dumps(filter_reduce_chain, indent=2))