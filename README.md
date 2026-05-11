# Chessbench

Benchmark LLM chess capability vs. memorization

Test LLMs on known forced-winning endgames and opening performance (based on eval score)

## Setup 
Python 3.13 via uv

Requires locally-installed stockfish used to make LLM's opponent as annoying as possible.
 (Marginally increases possibility of 50-move-rule draws)
Instructions below for installing this via apt.

Run the benchmark (results saved as .jsonl to run\_logs/)

```
sudo apt update
sudo apt install stockfish
git clone git@github.com:danielhuadotcom/chessbench.git
cd chessbench
cp .env.example .env
vim .env #fill in your OpenRouter API key
uv sync
uv run main.py
```
