## extract_json_content

This function extract and parse JSON content from LLM response with robust error handling. Currently I consider those 4 cases as valid:
- Raw JSON objects - Direct JSON output without formatting
- Markdown JSON blocks - Wrapped in ```json code fences
- Generic code blocks - JSON in unspecified code blocks
- Loose JSON patterns - Partial matches within freeform text

input: raw_response: Raw string response from the LLM

Returns: Parsed JSON dict or None if unrecoverable

Example usage:
````python
response = '''{
    "next_steps": [{
        "id": "step_1",
        "label": "Entity Recognition"
    }]
}'''
extract_json_content(response)  # Returns parsed dict


response = """
```json
{
    "status": "success",
    "data": {"count": 42}
}
```
extract_json_content(response) # Detects JSON through json code fence

response = """
```
{
    "status": "success",
    "data": {"count": 42}
}
```
extract_json_content(response) # Detects JSON through general fence


response = """
This is some random text by AI from JSON block
```json
{
    "status": "success",
    "data": {"count": 42}
}
```
extract_json_content(response) # Detects JSON in random response
````

See the main function in formatter.py for more examples and tests.