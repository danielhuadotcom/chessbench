import asyncio

import chess
import chess.engine


async def main():
    # 2 knights + move odds, human is able to win with ascii board
    # fen = "r1bqkb1r/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    # knight + move odds, human struggles
    fen = "rnbqkb1r/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    # based on these two data points i estimate Limit(time=0.1) fish is about 2700 Elo
    # https://en.wikipedia.org/wiki/Handicap_(chess)#Rating_equivalent

    transport, engine = await chess.engine.popen_uci("/usr/games/stockfish")
    board: chess.Board = chess.Board(fen)
    while not board.outcome(claim_draw=True):
        print(board)
        print(board.fen())
        move = input("Your Move (SAN): ")
        try:
            board.push_san(move)
        except ValueError as e:
            print(f"ERROR: {move} is invalid. {str(e)}\n")
            continue
        print()
        if board.outcome(claim_draw=True):
            continue
        res = await engine.play(board, chess.engine.Limit(time=0.1))
        board.push_uci(res.move.uci())
        print(f"Fish plays: {res.move.uci()}")

    print(board.outcome(claim_draw=True).result())
    await engine.quit()


if __name__ == "__main__":
    asyncio.run(main())
