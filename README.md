# Chessbench

Benchmark LLM chess capability vs. memorization

Test LLMs on known forced-winning endgames

## Setup 
Python 3.13 via uv

Requires locally-installed stockfish
 (Somewhat increases possibility of 50-move-rule draws, by being as annnoying of an opponent as possible)
Instructions below for installing this via apt

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
