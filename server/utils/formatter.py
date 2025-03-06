import json
import re
from typing import Optional, Dict, Any
import warnings


def escape_json_format_curly_braces(json_string: str) -> str:
    """
    Identifies the 'JSON_format' field inside a JSON string and escapes curly brackets within its value.
    """
    # Regular expression to find the "JSON_format" key and its string value
    # pattern = r'"JSON_format"\s*:\s*"([^"]*)"'
    # pattern = r'"JSON_format"\s*:\s*"\{[^}]+\}"'
    pattern = r'"JSON_format"\s*:\s*"\{.*?\}"'
    match = re.search(pattern, json_string)
    if match:
        content_inside_quotes = match.group(0)
        escaped_content = (
            content_inside_quotes.replace('"JSON_format":', "")
            .strip()[1:-1]
            .replace("{", "{{")
            .replace("}", "}}")
            .replace('"', "'")
        )
        escaped_content = '"JSON_format": "' + escaped_content + '"'

        return re.sub(pattern, escaped_content, json_string)
        # return escaped_content
    else:
        print("No match found.")
        return json_string


def extract_json_content(
    raw_response: str, escape_JSON_format=False
) -> Optional[Dict[str, Any]]:
    """
    Extract and parse JSON content from LLM response with robust error handling

    Args:
        raw_response: Raw string response from the LLM

    Returns:
        Parsed JSON dict or None if unrecoverable
    """
    raw_response = raw_response.strip()
    if escape_JSON_format:
        # replace single quotes with double quotes
        raw_response = re.sub(r"'", '"', raw_response)
        # reformat JSON_format field so that it is treated as a string
        raw_response = escape_json_format_curly_braces(raw_response)
    try:
        # try to extract the first JSON object from the raw response.
        brace_match = re.search(r"^\s*\n*(\{[\s\S]+\})\s*\n*$", raw_response, re.DOTALL)
        if brace_match:
            return json.loads(brace_match.group(1))
    except Exception:
        pass
    try:
        # Fallback: Try to extract JSON from a markdown JSON block.
        code_block_match = re.search(
            r"```json\s*\n(\{[\s\S]+\})\s*\n```", raw_response, re.DOTALL
        )
        if code_block_match:
            return json.loads(code_block_match.group(1))
    except Exception:
        pass
    try:
        # Fallback 2: Try to extract JSON from a markdown code block.
        code_block_match = re.search(
            r"```\s*\n(\{[\s\S]+\})\s*\n```", raw_response, re.DOTALL
        )
        if code_block_match:
            return code_block_match.group(1)
    except Exception:
        pass
    # Last resort: Find JSON-like structures in text
    json_candidates = re.findall(r"\{.*\}", raw_response, re.DOTALL)
    for candidate in json_candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            warnings.warn(f"JSON decode error in candidate: {e}\nContent: {candidate}")
            continue

    warnings.warn("No valid JSON found in response")
    return None


# for testing
if __name__ == "__main__":
    print(
        extract_json_content(
            """
{
  "next_steps": [
    {
      "id": "step_1",
      "label": "Entity Recognition",
      "description": "Identify and extract entities (e.g., people, organizations, locations, concepts) from the text.",
      "explanation": "Entity recognition is a crucial step in knowledge graph construction as it identifies the nodes (entities) that will populate the graph.",
      "parentIds": []
    },
    {
      "id": "step_2",
      "label": "Relation Extraction",
      "description": "Identify and extract relationships between the entities.",
      "explanation": "Relation extraction is the process of identifying the edges that connect the nodes in the knowledge graph, defining the relationships between entities.",
      "parentIds": ["step_1"]
    }
  ]
}
        """
        )
    )
    print(
        extract_json_content(
            """
```
{
  "next_steps": [
    {
      "id": "step_1",
      "label": "Entity Recognition",
      "description": "Identify and extract entities (e.g., people, organizations, locations, concepts) from the text.",
      "explanation": "Entity recognition is a crucial step in knowledge graph construction as it identifies the nodes (entities) that will populate the graph.",
      "parentIds": []
    },
    {
      "id": "step_2",
      "label": "Relation Extraction",
      "description": "Identify and extract relationships between the entities.",
      "explanation": "Relation extraction is the process of identifying the edges that connect the nodes in the knowledge graph, defining the relationships between entities.",
      "parentIds": ["step_1"]
    }
  ]
}
```
        """
        )
    )
    print(
        extract_json_content(
            """```json
{
  "next_steps": [
    {
      "id": "step_1",
      "label": "Entity Recognition",
      "description": "Identify and extract entities (e.g., people, organizations, locations, concepts) from the text.",
      "explanation": "Entity recognition is a crucial step in knowledge graph construction as it identifies the nodes (entities) that will populate the graph.",
      "parentIds": []
    },
    {
      "id": "step_2",
      "label": "Relation Extraction",
      "description": "Identify and extract relationships between the entities.",
      "explanation": "Relation extraction is the process of identifying the edges that connect the nodes in the knowledge graph, defining the relationships between entities.",
      "parentIds": ["step_1"]
    }
  ]
}
```
"""
        )
    )

    print(
        extract_json_content(
            """
Here's the response from AI.
- Step1
- Step2
```json
{
  "next_steps": [
    {
      "id": "step_1",
      "label": "Entity Recognition",
      "description": "Identify and extract entities (e.g., people, organizations, locations, concepts) from the text.",
      "explanation": "Entity recognition is a crucial step in knowledge graph construction as it identifies the nodes (entities) that will populate the graph.",
      "parentIds": []
    },
    {
      "id": "step_2",
      "label": "Relation Extraction",
      "description": "Identify and extract relationships between the entities.",
      "explanation": "Relation extraction is the process of identifying the edges that connect the nodes in the knowledge graph, defining the relationships between entities.",
      "parentIds": ["step_1"]
    }
  ]
}
```
"""
        )
    )
