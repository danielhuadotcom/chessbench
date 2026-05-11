import argparse
import asyncio
import os
from datetime import datetime
from pathlib import Path

import chess
import chess.engine
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel


class RunResult(BaseModel):
    starting_position_fen: str
    starting_position_description: str
    modelstring: str
    success: bool
    cost: float
    illegals: int
    messages: list[dict]


async def testPosition(
    client: AsyncOpenAI,
    description: str,
    fen: str,
    modelstring: str,
    verbose: bool,
    sem,
):
    async with sem:
        cost = 0.0
        illegals = 0
        transport, engine = await chess.engine.popen_uci("/usr/games/stockfish")
        board: chess.Board = chess.Board(fen)
        messages: list[dict] = [
            {
                "role": "user",
                "content": "Let's play chess! You play White. Answer only in SAN without any other content.",
            },
        ]
        _lastIllegal = 0

        print(f"{modelstring} vs. Fish (4 seconds/move) from position: {description}")
        if verbose:
            print()
            print(board)
            print()

        try:
            while not board.outcome(claim_draw=True):
                # I'd love to remove this to save on tokens but I think this is needed for playability
                messages.append(
                    {
                        "role": "user",
                        "content": f"Your turn from this position:\n{board}\nFEN: {board.fen()}",
                    }
                )
                response = await client.chat.completions.create(
                    model=modelstring,
                    messages=messages,
                )
                if verbose:
                    print(f"Move {len(board.move_stack) // 2 + 1}")
                    print(f"{modelstring} plays: {response.choices[0].message.content}")
                cost += response.usage.cost
                messages.append(
                    {
                        "role": "assistant",
                        "content": response.choices[0].message.content,
                    }
                )
                try:
                    board.push_san(response.choices[0].message.content)
                except ValueError as e:
                    illegals += 1
                    # max 15 illegal moves/turn to prevent infinite chess hell
                    if not _lastIllegal:
                        _lastIllegal = illegals
                    if _lastIllegal and illegals - _lastIllegal + 1 >= 15:
                        return RunResult(
                            starting_position_fen=fen,
                            starting_position_description=description,
                            modelstring=modelstring,
                            messages=messages,
                            cost=cost,
                            illegals=illegals,
                            success=False,
                        )
                    if verbose:
                        print(
                            f"ERROR: {modelstring}'s last move {response.choices[0].message.content} is invalid. {str(e)}\n"
                        )
                    messages.append(
                        {
                            "role": "user",
                            "content": f"ERROR (last move invalid): {str(e)}",
                        }
                    )
                    continue
                _lastIllegal = 0
                if board.outcome(claim_draw=True):
                    continue
                if verbose:
                    info = await engine.analyse(board, chess.engine.Limit(time=4))
                    print(f"Fish eval: {info['score'].white()}")
                res = await engine.play(board, chess.engine.Limit(time=4))
                fish_move_san = board.san(res.move)
                board.push_uci(res.move.uci())
                if verbose:
                    print(f"Fish plays: {fish_move_san}")
                    print()
                    print(board)
                    print()
                    print()
                messages.append(
                    {
                        "role": "user",
                        "content": f"{fish_move_san}",
                    }
                )
        except Exception:
            # crash = loss (even it's my fault, e.g. not handling long context)
            return RunResult(
                starting_position_fen=fen,
                starting_position_description=description,
                modelstring=modelstring,
                messages=messages,
                cost=cost,
                illegals=illegals,
                success=False,
            )
        finally:
            await engine.quit()

        return RunResult(
            starting_position_fen=fen,
            starting_position_description=description,
            modelstring=modelstring,
            messages=messages,
            cost=cost,
            illegals=illegals,
            success=board.outcome(claim_draw=True).result() == "1-0",
        )


async def _saveResults(results):
    run_logs_dir = Path("run_logs")
    with (run_logs_dir / datetime.now().strftime("%Y-%m-%d-%H%M.jsonl")).open("w") as f:
        for r in results:
            f.write(r.model_dump_json() + "\n")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--samples", type=int, default=1)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    load_dotenv()

    client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL")
    )

    POSITIONS = [
        ("Forced-winning Queen Endgame (K+Q vs. K)", "8/8/8/3k4/8/3K4/8/Q7 w - - 0 1"),
        #("Forced-winning Rook Endgame (K+R vs. K)", "8/8/8/8/3k4/8/3K4/R7 w - - 0 1"),
        #("Forced-winning Pawn Endgame (K+P vs. K)","8/8/8/3k4/8/2K5/3P4/8 w - - 0 1"),
        #("Difficult forced-winning Knight and Bishop checkmate endgame","8/8/3k4/8/8/1BNK4/8/8 w - - 0 1"),
        #("Two Knights + Move Odds vs. 4s Fish","r1bqkb1r/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
    ]

    MODELS = [
        #"openai/gpt-3.5-turbo-instruct",
        #"google/gemini-3-flash-preview",
        #"google/gemini-3.1-flash-lite-preview",
        #"google/gemini-3.1-pro-preview",
        #"anthropic/claude-sonnet-4.6",
        #"anthropic/claude-opus-4.6",
        #"openai/gpt-5.5",
        #"openai/gpt-5.4-mini",
        #"x-ai/grok-4.20",
        #"moonshotai/kimi-k2.6",
        #"deepseek/deepseek-v4-pro",
        "deepseek/deepseek-v4-flash",
        "qwen/qwen3.5-plus-20260420",
        #"z-ai/glm-5.1",
        #"minimax/minimax-m2.7",
    ]

    sem = asyncio.Semaphore(20)  # limit number of ongoing runs/stockfish processes
    runs = []
    for p in POSITIONS:
        for m in MODELS:
            for _ in range(args.samples):
                runs.append(testPosition(client, p[0], p[1], m, args.verbose, sem))
    results = await asyncio.gather(*runs)

    if args.verbose:
        for r in results:
            print(
                f"{r.modelstring} playing {r.starting_position_description} success: {r.success}"
            )

    await _saveResults(results)


if __name__ == "__main__":
    asyncio.run(main())
