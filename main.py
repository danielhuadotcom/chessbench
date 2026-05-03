import argparse
import asyncio
import os

import chess
import chess.engine
from dotenv import load_dotenv
from openai import AsyncOpenAI

# might not even want these because I could just string parse + prompt?
from openai.lib._pydantic import to_strict_json_schema
from pydantic import BaseModel, Field

async def testPosition(
    client: AsyncOpenAI,
    fen: str,
    modelstring: str,
):
    #for now the model is always White in these test cases
    transport, engine = await chess.engine.popen_uci(
        "/usr/games/stockfish"
    )
    '''
    init board

    loop
        let model make move
            send fen + board ascii drawing
            if pass exception of push_san back if fails (Illegal)
        update fen
            check for illegal move and game end 
                checkmate, insuffient mat, 3fold repeat pos, stalemate, 50 move)
        pass fen to fish
        update fen
        check for illegal move and game end
            shouldn't ever happen here but hey maybe the model will end up
            losing to fish in known forced winning endgames...
        update messages

    ret False if Loss, or Draw
    ret True if Checkmate

    api error: just crash
    '''
    board : chess.Board = chess.Board(fen)
    messages : list[dict] = [
        {
            "role":"user",
            "content":f"Let's play chess! You play White. Answer only in SAN without any other content.",
        },
    ]

    while not board.outcome(claim_draw=True):
        messages.append({
            "role":"user",
            "content":f"Your turn from this position:\n{board}\nFEN: {board.fen()}",
        })
        response = await client.chat.completions.create(
            model=modelstring,
            messages=messages
        )
        print(f"{modelstring} plays: {response.choices[0].message.content}")
        try:
            board.push_san(response.choices[0].message.content)
        except ValueError as e:
            print(f"ERROR: {modelstring}'s last move {response.choices[0].message.content} is invalid. {str(e)}\n")
            messages.append({
                "role":"user",
                "content":f"ERROR (last move invalid): {str(e)}",
            })
            continue
        print(board)
        print()
        if board.outcome(claim_draw=True):
            continue
        res = await engine.play(board, chess.engine.Limit(time=0.1))
        board.push_uci(res.move.uci())
        print(f"Fish plays: {res.move.uci()}")
        print(board)
        print()
        messages.append({
            "role":"user",
            "content":f"{res.move}",
        })


    await engine.quit()

    #TODO more complex return (could just return outcome to parse later for result)
    return board.outcome(claim_draw=True).result() == "1-0"


async def main():
    load_dotenv()

    client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL")
    )

    #TODO set up run configuration. list of positions vs list of models, tally results and pretty print
    #print(await testPosition(client, board.fen(), "deepseek/deepseek-v4-flash"))
    #print(f'model (white) wins: {await testPosition(client, "8/8/8/8/3k4/8/3K4/R7 w - - 0 1", "google/gemini-3-flash-preview")}')
    #print(f'model (white) wins: {await testPosition(client, "8/8/8/8/3k4/8/3K4/R7 w - - 0 1", "google/gemini-3.1-pro-preview")}')
    #print(f'model (white) wins: {await testPosition(client, "8/8/8/8/3k4/8/3K4/R7 w - - 0 1", "anthropic/claude-sonnet-4.6")}')
    print(f'model (white) wins: {await testPosition(client, "8/8/8/8/3k4/8/3K4/R7 w - - 0 1", "anthropic/claude-opus-4.6")}')
    """
    #cursed bullshit that kind of works. thank god for libraries
    proc = await asyncio.create_subprocess_shell(
        '/usr/games/stockfish',
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    commands = f"position fen {board.fen()}\n"
    print(commands.encode("utf-8"))
    proc.stdin.write(commands.encode("utf-8"))
    await proc.stdin.drain()
    await asyncio.sleep(1)
    commands = f"go depth 3\n"
    print(commands.encode("utf-8"))
    proc.stdin.write(commands.encode("utf-8"))
    await proc.stdin.drain()
    await asyncio.sleep(1)
    stdout, stderr = await proc.communicate()
    print(stdout)
    move = str(stdout).split("bestmove")[1][1:5]
    """



if __name__ == "__main__":
    asyncio.run(main())
