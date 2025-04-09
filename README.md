# VIDEE
This is the open-source repository for paper: **V**isual and **I**nteractive **D**ecomposition, **E**xecution, and **E**valuation of Text Analytics with Intelligent Agents

# Reproduction Guide
## Back-end 
1. Set up virtual environment with python 3.11 (for parallel version)
2. Set up API keys using system environment 
- The system supports up to three models as evaluators: `gpt-4o-mini`, `claude-3-5-sonnet-latest`, and `gemini-2.0-flash-lite`.
- **You must set up at least one API key**. The system will automatically ignore models without available API keys.
- To set up, put your API keys in the environment variable:
```shell
# typically in your ~/.bashrc or ~/.zshrc:
OPENAI_API_KEY="xxx"
ANTHROPIC_API_KEY="xxx"
GEMENI_API_KEY="xxx"
```
4. run `pip install -r server/requirements.txt`
5. run `python -m server.main`

## Front-end
1. run `npm i`
2. run `npm run dev`
