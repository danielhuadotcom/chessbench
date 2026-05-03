# Chessbench

Benchmark LLM chess capability, especially in known forced-winning endgames. 

## Setup 
Python 3.13 via uv

Requires locally-installed stockfish used to make LLM's opponent as annoying as possible.
 (Marginally increases possibility of 50-move-rule draws)

```
sudo apt install stockfish
git clone git@github.com:danielhuadotcom/chessbench.git
cd chessbench
uv sync
uv run main.py
```
