# Task Decomposition
Decomposing end-to-end Goal into a text analytics pipeline.

# Launching
## Back-end 
1. Set up virtual environment 
2. run `pip install -r server/requirements.txt`
3. run `python -m server.main`

## Front-end
1. run `npm i`
2. run `npm run dev`

## TODOs
0. add primitive task execution parameter generation
1. Implement beam-search + self evaluation/consistency estimation for decomposer
2. add confidence and complexity estimation for semantic tasks
3. design visual encodings for confidence and complexity
4. add execution result evaluation in evaluator (using entropy or semantic uncertainty) (to be visualized in observation panel)
5. Add better direct manipulation design of pipeline refinement
