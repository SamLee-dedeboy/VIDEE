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
    def transform(self, data: List[Dict[str, Any]], feature_key: str, **kwargs) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def __call__(self, data: List[Dict[str, Any]], feature_key: str, **kwargs) -> List[Dict[str, Any]]:
        """Allow transformer to be called directly"""
        return self.transform(data, feature_key, **kwargs)


# Transform operation with python executor
class PythonExecutorTransformer(DataTransformer):
    """
    Transform a list of documents to another schema using a provided Python code string.

    Args:
        data: List of document dictionaries
        transform_code: String containing Python code that defines a transform function
                    Format must be:
                    ```
                    def transform(data):
                        # Logic to transform the data
                    ```
        wrap_result: If True, wraps the return value in a list with a single document

    Returns:
        If wrap_result is True: A list containing one dictionary with the reduced result
        If wrap_result is False: The direct return value from the transform function
    """
    def _create_transform_function(self, transform_code: str) -> Callable:
        """Converts the transform code string to a callable function"""
        try:
            # Compile and execute the reduce function
            compiled_code = compile(transform_code, '<string>', 'exec')
            namespace = {}
            exec(compiled_code, namespace)

            # Check if the transform function was defined
            if 'transform' not in namespace or not callable(namespace['transform']):
                raise ValueError("The provided code must define a function called 'transform'")

            return namespace['transform']
        except Exception as e:
            logging.error(f"Error creating transform function from code: {e}")
            # Return a function that just returns the data if there's an error
            return lambda data: data

    def transform(self, data: List[Dict[str, Any]],
                 transform_code: str = None,
                 wrap_result: bool = False,
                 **kwargs) -> Any:
        if not transform_code or not data:
            return data

        try:
            # Create the transform function from the code string
            transform_func = self._create_transform_function(transform_code)

            # Call the transform_func function on the data
            result = transform_func(data)

            # Wrap the result if needed
            if wrap_result:
                if isinstance(result, dict):
                    return [result]
                else:
                    return [{'result': result}]
            else:
                return result

        except Exception as e:
            logging.error(f"Error in transform operation: {e}")
            return [{'error': str(e)}]


# Registry of available transformers
_TRANSFORMERS = {
    'transform': PythonExecutorTransformer(),
}

def register_transformer(name: str, transformer: DataTransformer):
    """Register a new data transformer"""
    _TRANSFORMERS[name] = transformer

def list_transformers():
    """List all available transformers"""
    return list(_TRANSFORMERS.keys())

def data_transform_tool(inputs: List[Dict[str, Any]],
                       operation: str = 'transform',
                       **kwargs) -> List[Dict[str, Any]]:
    """
    Transforms data structure according to the specified operation.

    Args:
        inputs: Input documents in json format
        operation: Transformation operation to apply (default: "transform")
        **kwargs: Additional parameters specific to the transformation operation

    Returns:
        Transformed data
    """
    try:
        if operation not in _TRANSFORMERS:
            logging.warning(f"Unknown transformation operation: {operation}, falling back to map")
            operation = 'transform'

        transformer = _TRANSFORMERS[operation]
        return transformer.transform(inputs, **kwargs)
    except Exception as e:
        logging.error(f"Error in data_transform_tool: {e}")
        return inputs