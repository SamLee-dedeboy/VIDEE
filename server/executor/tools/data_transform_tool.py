import json
import logging
import re
from collections import defaultdict
from typing import List, Dict, Any, Optional, Callable

"""
Assumption:
Input is a list of documents in JSON format

Action:
Transform documents schema from one to another
Can also generate new schema from a group of documents, like
- generate a graph from entities and relationships
- group documents by attributes
"""

class DataTransformer:
    """Base class for data transformation operations"""
    def transform(self, data: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def __call__(self, data: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        """Allow transformer to be called directly"""
        return self.transform(data, **kwargs)

# MAP operation
class SchemaTransformer(DataTransformer):
    """
    Transforms each document from one schema to another using a template.

    Args:
        data: List of document dictionaries
        template: String template to format output with Jinja2-style syntax
                Supports variable substitution with {{field}} and expressions like {{field * 0.3}}
                Can include conditional logic with {% if %} statements and loops with {% for %}

    Returns:
        List of transformed dictionaries
    """
    def transform(self, data: List[Dict[str, Any]],
                 template: str = None,
                 **kwargs) -> List[Dict[str, Any]]:
        if not template:
            return data

        result = []

        for item in data:
            try:
                # for rendering template
                import jinja2
                env = jinja2.Environment(autoescape=False)
                template_obj = env.from_string(template.strip())

                # Create a context with the item data
                context = item.copy()

                # Add math functions
                import math
                for attr in dir(math):
                    if not attr.startswith('_'):
                        context[attr] = getattr(math, attr)

                # Add Python's built-in functions
                context['str'] = str
                context['int'] = int
                context['float'] = float
                context['bool'] = bool
                context['list'] = list
                context['tuple'] = tuple
                context['dict'] = dict
                context['set'] = set
                context['len'] = len
                context['sum'] = sum
                context['min'] = min
                context['max'] = max
                context['abs'] = abs
                context['round'] = round
                context['sorted'] = sorted
                context['enumerate'] = enumerate
                context['zip'] = zip
                context['range'] = range
                context['any'] = any
                context['all'] = all

                # Add datetime module
                import datetime
                context['datetime'] = datetime

                # Add re module
                import re
                context['re'] = re

                # Render the template
                rendered_text = template_obj.render(**context)

                try:
                    # Replace Python's True/False with JSON true/false, handling only standalone True/False, ignoring all variables/strings containing True/False like isTrue, True_value, "True", 'True'
                    rendered_text = re.sub(r'(?<![a-zA-Z0-9_"\'])True(?![a-zA-Z0-9_"\'])', 'true', rendered_text)
                    rendered_text = re.sub(r'(?<![a-zA-Z0-9_"\'])False(?![a-zA-Z0-9_"\'])', 'false', rendered_text)

                    '''
                    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
                    Replace Python single quotes with double quotes for JSON compatibility, with a state machin..
                    We need to focus on correctly handles single quotes while preserving those inside double quotes and any other scenarios
                    '''
                    result_text = ""
                    in_double_quotes = False
                    in_single_quotes = False
                    escape_next = False
                    i = 0

                    while i < len(rendered_text):
                        char = rendered_text[i]
                        # Handle escape character
                        if char == '\\' and not escape_next:
                            escape_next = True
                            result_text += char
                            i += 1
                            continue
                        if escape_next:
                            escape_next = False
                            result_text += char
                            i += 1
                            continue

                        # Handle quote state changes
                        if char == '"' and not in_single_quotes:
                            in_double_quotes = not in_double_quotes
                            result_text += char
                        elif char == "'" and not in_double_quotes:
                            # start or end of a single quoted string outside of double quotes, replace it with double quote
                            in_single_quotes = not in_single_quotes
                            result_text += '"'
                        elif char == "'" and in_double_quotes:
                            # Single quote inside double quotes - preserve it
                            result_text += char
                        else:
                            # Regular character
                            result_text += char
                        i += 1

                    rendered_text = result_text
                    '''
                    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
                    '''

                    json_result = json.loads(rendered_text)
                    result.append(json_result)
                except json.JSONDecodeError as e:
                    logging.warning(f"JSON decode error: {e} in text: {rendered_text[:100]}...")
                    # If not valid JSON, use as plain text
                    result.append({"result": rendered_text})

            except Exception as e:
                logging.warning(f"Error applying template: {e}")
                # If template fails, return the original item
                result.append(item)

        return result

# FILTER operation
class FilterTransformer(DataTransformer):
    """
    Filters documents based on a string containing filter code.

    Args:
        data: List of document dictionaries
        filter_code: String containing Python code that defines a filter function.
                    Format must be:
                    ```
                    def filter_data(data):
                        # Logic to filter the data
                        # Each item in data is processed and True/False is returned
                        # Example: return [item for item in data if item.get('department') == 'IT']
                    ```

    Returns:
        List of dictionaries that pass the filter
    """
    def _create_filter_function(self, filter_code: str) -> Callable:
        """Converts the filter code string to a callable function"""
        try:
            # Compile and execute the filter function
            compiled_code = compile(filter_code, '<string>', 'exec')
            namespace = {}
            exec(compiled_code, namespace)

            # Check if the filter_data function was defined
            if 'filter_data' not in namespace or not callable(namespace['filter_data']):
                raise ValueError("The provided code must define a function called 'filter_data'")

            return namespace['filter_data']
        except Exception as e:
            logging.error(f"Error creating filter function from code: {e}")
            # Return a function that passes everything if there's an error
            return lambda data: data

    def transform(self, data: List[Dict[str, Any]],
                 filter_code: str = None,
                 **kwargs) -> List[Dict[str, Any]]:
        if not filter_code:
            return data

        try:
            # Create the filter function from the code string
            filter_func = self._create_filter_function(filter_code)

            # Call the filter function on the whole data
            result = filter_func(data)

            # Ensure the result is a list
            if not isinstance(result, list):
                logging.warning("Filter function did not return a list, returning original data")
                return data

            return result
        except Exception as e:
            logging.error(f"Error in filter operation: {e}")
            return data

# REDUCE operation
class ReduceTransformer(DataTransformer):
    """
    Reduces a list of documents to a single result using a provided Python code string.

    Args:
        data: List of document dictionaries
        reduce_code: String containing Python code that defines a reduce function
                    Format must be:
                    ```
                    def reduce_data(data):
                        # Logic to process the data
                        # Return a single result
                    ```
        wrap_result: If True, wraps the return value in a list with a single document

    Returns:
        If wrap_result is True: A list containing one dictionary with the reduced result
        If wrap_result is False: The direct return value from the reduce function
    """
    def _create_reduce_function(self, reduce_code: str) -> Callable:
        """Converts the reduce code string to a callable function"""
        try:
            # Compile and execute the reduce function
            compiled_code = compile(reduce_code, '<string>', 'exec')
            namespace = {}
            exec(compiled_code, namespace)

            # Check if the reduce_data function was defined
            if 'reduce_data' not in namespace or not callable(namespace['reduce_data']):
                raise ValueError("The provided code must define a function called 'reduce_data'")

            return namespace['reduce_data']
        except Exception as e:
            logging.error(f"Error creating reduce function from code: {e}")
            # Return a function that just returns the data if there's an error
            return lambda data: data

    def transform(self, data: List[Dict[str, Any]],
                 reduce_code: str = None,
                 wrap_result: bool = False,
                 **kwargs) -> Any:
        if not reduce_code or not data:
            return data

        try:
            if isinstance(data, Dict):
                data = [data]
            # Create the reduce function from the code string
            reduce_func = self._create_reduce_function(reduce_code)

            # Call the reduce function on the data
            result = reduce_func(data)

            # Wrap the result if needed
            if wrap_result:
                if isinstance(result, dict):
                    return [result]
                else:
                    return [{'result': result}]
            else:
                return result

        except Exception as e:
            logging.error(f"Error in reduce operation: {e}")
            return [{'error': str(e)}]

# CHAIN operation
class TransformChain(DataTransformer):
    """
    Chains multiple transformers together in a specific order:
    1. Map (optional)
    2. Filter (optional)
    3. Reduce (optional, but can only be the last operation)

    Args:
        data: List of document dictionaries
        map_config: Configuration for map operation (optional)
        filter_config: Configuration for filter operation (optional)
        reduce_config: Configuration for reduce operation (optional)

    Returns:
        Transformed data after applying the chain of operations
    """
    def transform(self, data: List[Dict[str, Any]],
                 map_config: Dict[str, Any] = None,
                 filter_config: Dict[str, Any] = None,
                 reduce_config: Dict[str, Any] = None,
                 **kwargs) -> List[Dict[str, Any]]:
        result = data

        # Apply map operation if configured
        if map_config:
            map_transformer = SchemaTransformer()
            result = map_transformer.transform(result, **map_config)

        # Apply filter operation if configured
        if filter_config:
            filter_transformer = FilterTransformer()
            result = filter_transformer.transform(result, **filter_config)

        # Apply reduce operation if configured (always last)
        if reduce_config:
            reduce_transformer = ReduceTransformer()
            result = reduce_transformer.transform(result, **reduce_config)

        return result

# Registry of available transformers
_TRANSFORMERS = {
    'map': SchemaTransformer(),
    'filter': FilterTransformer(),
    'reduce': ReduceTransformer(),
    'chain': TransformChain()
}

def register_transformer(name: str, transformer: DataTransformer):
    """Register a new data transformer"""
    _TRANSFORMERS[name] = transformer

def list_transformers():
    """List all available transformers"""
    return list(_TRANSFORMERS.keys())

def data_transform_tool(inputs: List[Dict[str, Any]],
                       operation: str = 'map',
                       **kwargs) -> List[Dict[str, Any]]:
    """
    Transforms data structure according to the specified operation.

    Args:
        inputs: Input documents in json format
        operation: Transformation operation to apply (default: "map")
        **kwargs: Additional parameters specific to the transformation operation

    Returns:
        Transformed data
    """
    try:
        if operation not in _TRANSFORMERS:
            logging.warning(f"Unknown transformation operation: {operation}, falling back to map")
            operation = 'map'

        transformer = _TRANSFORMERS[operation]
        return transformer.transform(inputs, **kwargs)
    except Exception as e:
        logging.error(f"Error in data_transform_tool: {e}")
        return inputs