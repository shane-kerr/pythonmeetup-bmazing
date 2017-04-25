from game import moves
from game.mazefield_attributes import Path, Finish
from players.player import Player

class Map:
    pass

class AStarPlayer(Player):
    name = "A* Player"

    def __init__(self):
        self.map = Map()

    def turn(self, surroundings):
        if surroundings.right in [Path, Finish]:
            return moves.RIGHT

        if surroundings.left == Path:
            return moves.LEFT

        if surroundings.up == Path:
            return moves.UP

        if surroundings.down == Path:
            return moves.DOWN
