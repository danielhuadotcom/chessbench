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
    print(f"{modelstring} vs. Fish (4 seconds/move) from position:")
    print()
    print(board)
    print()

    messages : list[dict] = [
        {
            "role":"user",
            "content":f"Let's play chess! You play White. Answer only in SAN without any other content.",
        },
    ]

    while not board.outcome(claim_draw=True):
        #I'd love to remove this to save on tokens but I think this is needed for playability
        messages.append({
            "role":"user",
            "content":f"Your turn from this position:\n{board}\nFEN: {board.fen()}",
        })
        response = await client.chat.completions.create(
            model=modelstring,
            #reasoning_effort="medium", #opus fix
            messages=messages,
        )
        print(f"Move {len(board.move_stack)//2 + 1}")
        print(f"{modelstring} plays: {response.choices[0].message.content}")
        try:
            board.push_san(response.choices[0].message.content)
        except Exception as e:
            print(f"ERROR: {modelstring}'s last move {response.choices[0].message.content} is invalid. {str(e)}\n")
            messages.append({
                "role":"user",
                "content":f"ERROR (last move invalid): {str(e)}",
            })
            continue
        if board.outcome(claim_draw=True):
            continue
        #don't do this if not verbose mode or opening analysis mode
        #TODO could use this to short circuit endgame eval if fish believes is draw
        #TODO track cost somehow
        info = await engine.analyse(board, chess.engine.Limit(time=4))
        print(f'Fish eval: {info["score"].white()}')
        res = await engine.play(board, chess.engine.Limit(time=4)) #TODO increase for forced endgame bench?
        fish_move_san = board.san(res.move)
        board.push_uci(res.move.uci())
        print(f"Fish plays: {fish_move_san}")
        print()
        print(board)
        print()
        print()
        messages.append({
            "role":"user",
            "content":f"{fish_move_san}",
        })


    await engine.quit()

    #TODO more complex return (could just return outcome to parse later for result)
    #need outcome, number of moves (less better), number of illegal moves (less better)

    #TODO return crash as loss
    return board.outcome(claim_draw=True).result() == "1-0"


async def main():
    load_dotenv()

    client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL")
    )

    #TODO set up run configuration. list of positions vs list of models, tally results and pretty print
    #tally cost too
    #also needs args for number of samples per scenario, since some scenarios are inconsistent
    #and for long runs print status in realtime in verbose mode

    #print(await testPosition(client, board.fen(), "deepseek/deepseek-v4-flash"))
    #print(f'model (white) wins: {await testPosition(client, "8/8/8/8/3k4/8/3K4/R7 w - - 0 1", "gemini-3.1-pro-preview")}')
    #queen endgame
    #print(f'model (white) wins: {await testPosition(client, "8/8/8/3k4/8/3K4/8/Q7 w - - 0 1", "gemini-3.1-pro-preview")}')
    #print(f'model (white) wins: {await testPosition(client, "8/8/8/3k4/8/3K4/8/Q7 w - - 0 1", "gemini-3-flash-preview")}')
    #print(f'model (white) wins: {await testPosition(client, "8/8/8/3k4/8/3K4/8/Q7 w - - 0 1", "gemini-3.1-flash-lite-preview")}')
    #single pawn endgame, winning
    #print(f'model (white) wins: {await testPosition(client, "8/8/8/3k4/8/2K5/3P4/8 w - - 0 1", "gemini-3.1-pro-preview")}')
    #print(f'model (white) wins: {await testPosition(client, "8/8/8/8/3k4/8/3K4/R7 w - - 0 1", "google/gemini-3.1-pro-preview")}')
    #print(f'model (white) wins: {await testPosition(client, "rnb1kbnr/ppppp1pp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "google/gemini-3.1-pro-preview")}')
    #print(f'model (white) wins: {await testPosition(client, "r1bqkb1r/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "google/gemini-3.1-pro-preview")}')
    #print(f'model (white) wins: {await testPosition(client, "r1bqkb1r/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "gemini-3-flash-preview")}')
    #print(f'model (white) wins: {await testPosition(client, "8/8/8/8/3k4/8/3K4/R7 w - - 0 1", "anthropic/claude-sonnet-4.6")}')
    #print(f'model (white) wins: {await testPosition(client, "8/8/8/8/3k4/8/3K4/R7 w - - 0 1", "anthropic/claude-opus-4.6")}')
    #modelstring human/me: 12 seconds to win https://lichess.org/0RgWuO4p

    #single pawn endgame "trebuchet" moving side wins with one winning move
    #TODO unfortunately i don't like this one because i got it from a chess.com blog with good SEO
    #and the intent of this project is to test grokking, not memorization
    #yeah this one is suspicious even flash lite is playing the right move...LOL
    #that's actually cool to benchmark, my DIY positions vs. endgame puzzles in the training data of similar difficulty
    print(f'model (white) wins: {await testPosition(client, "8/8/6K1/4p3/2k1P3/8/8/8 w - - 0 1", "gemini-3.1-flash-lite-preview")}')


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
