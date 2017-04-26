"""
This player keeps a map of the maze as much as known. Using this, it
can find areas that are left to explore, and try to find the nearest
one. Areas left to explore are called "Path" in this game.

We don't know where on the map we start, and we don't know how big the
map is. We could be lazy and simply make a very large 2-dimensional
array to hold the map; this will probably work fine since we know that
the map is loaded from a text file. However, we will go ahead and do
it all sweet and sexy-like and make a map that resizes itself to allow
for any arbitrary position.

This player will use the A* algorithm to find the number of steps to
get to any path that we have not yet explored.
"""
import heapq
import pprint
import sys

from game import moves
from game.mazefield_attributes import Path, Finish, Wall, Start
from players.player import Player

DEBUG = False


def dist(x0, y0, x1, y1):
    """distance between two positions using only cardinal movement"""
    return abs(x1-x0) + abs(y1-y0)


class Map:
    """
    Implements a rectangular 2-dimensional map of unknown size.
    """
    def __init__(self):
        self.pos_x = 0
        self.pos_y = 0
        self.map_x0 = self.map_x1 = 0
        self.map_y0 = self.map_y1 = 0
        self.map = [[Path]]     # we must have started on a Path

    def move_left(self):
        self.pos_x -= 1

    def move_right(self):
        self.pos_x += 1

    def move_up(self):
        self.pos_y += 1

    def move_down(self):
        self.pos_y -= 1

    def _map_height(self):
        return self.map_y1 - self.map_y0 + 1

    def _map_width(self):
        return self.map_x1 - self.map_x0 + 1

    def _grow_map_left(self):
        """
        To grow the map to the left, we have to add a new column.
        """
        new_column = [None] * self._map_height()
        self.map = [new_column] + self.map
        self.map_x0 -= 1

    def _grow_map_right(self):
        """
        To grow the map to the right, we have to add a new column.
        """
        new_column = [None] * self._map_height()
        self.map.append(new_column)
        self.map_x1 += 1

    def _grow_map_up(self):
        """
        To grow the map up, we add an unknown value to each column.
        """
        for column in self.map:
            column.append(None)
        self.map_y1 += 1

    def _grow_map_down(self):
        """
        To grow the map down, we have to add a new unknown value to
        the bottom of every column. There is no simple way to add an
        item to the start of a list, so we create a new map using new
        columns and then replace our map with this one.
        """
        new_map = []
        for column in self.map:
            column = [None] + column
            new_map.append(column)
        self.map = new_map
        self.map_y0 -= 1

    def remember_surroundings(self, surroundings):
        if DEBUG:
            print("---- before ---")
            pprint.pprint(vars(self))
        if self.pos_x == self.map_x0:
            self._grow_map_left()
        if self.pos_x == self.map_x1:
            self._grow_map_right()
        if self.pos_y == self.map_y0:
            self._grow_map_down()
        if self.pos_y == self.map_y1:
            self._grow_map_up()
        x = self.pos_x - self.map_x0
        y = self.pos_y - self.map_y0
        self.map[x-1][y] = surroundings.left
        self.map[x+1][y] = surroundings.right
        self.map[x][y-1] = surroundings.down
        self.map[x][y+1] = surroundings.up
        if DEBUG:
            print("---- after ---")
            pprint.pprint(vars(self))

    def dump(self):
        if DEBUG:
            pprint.pprint(vars(self))
        chars = {None: " ",
                 Path: ".",
                 Wall: "#",
                 Finish: ">",
                 Start: "<", }
        for y in range(self._map_height()-1, -1, -1):
            for x in range(self._map_width()):
                if (((y + self.map_y0) == self.pos_y) and
                        ((x + self.map_x0) == self.pos_x)):
                    sys.stdout.write("@")
                else:
                    sys.stdout.write(chars[self.map[x][y]])
            sys.stdout.write("\n")

    def is_interesting(self, x, y):
        x_idx = x - self.map_x0
        y_idx = y - self.map_y0
        # if we do not know if the place is a path, then it is not interesting
        if self.map[x_idx][y_idx] != Path:
            return False
        # if it is on the edge then it is interesting
        if x in (self.map_x0, self.map_x1):
            return True
        if y in (self.map_y0, self.map_y1):
            return True
        # if it has an unknown square next to it then it is interesting
        if self.map[x_idx-1][y_idx] is None:
            return True
        if self.map[x_idx+1][y_idx] is None:
            return True
        if self.map[x_idx][y_idx-1] is None:
            return True
        if self.map[x_idx][y_idx+1] is None:
            return True
        # everything else is uninteresting
        return False

    def all_interesting(self):
        interesting = []
        for x in range(self.map_x0, self.map_x1+1):
            for y in range(self.map_y0, self.map_y1+1):
                if self.is_interesting(x, y):
                    interesting.append((x, y))
        return interesting

    def _moves(self, x, y):
        result = []
        x_idx = x - self.map_x0
        y_idx = y - self.map_y0
        if (x > self.map_x0) and (self.map[x_idx-1][y_idx] in (Path, Start)):
            result.append((x-1, y))
        if (x < self.map_x1) and (self.map[x_idx+1][y_idx] in (Path, Start)):
            result.append((x+1, y))
        if (y > self.map_y0) and (self.map[x_idx][y_idx-1] in (Path, Start)):
            result.append((x, y-1))
        if (y < self.map_y1) and (self.map[x_idx][y_idx+1] in (Path, Start)):
            result.append((x, y+1))
        return result

    @staticmethod
    def _cur_priority(p, pos):
        """
        This is a very inefficient way to see if we are in the priority
        queue already. However, for this program it is good enough.
        """
        for n, node in enumerate(p):
            if node[1] == pos:
                return n
        return -1

    def find_path_to(self, x, y):
        """
        We can use Djikstra's algorithm to find the shortest path.
        This won't be especially efficient, but it should work.

        The algorithm is described here:
        http://www.roguebasin.com/index.php?title=Pathfinding
        """
        v = {}      # previously visited nodes
        p = []      # priority queue
        node = (0, (self.pos_x, self.pos_y))
        p.append(node)
        while p:
            cost, pos = heapq.heappop(p)
            # if we've reached our target, build our path and return it
            node_x, node_y = pos
            if (node_x == x) and (node_y == y):
                path = []
                path_pos = pos
                while path_pos != (self.pos_x, self.pos_y):
                    path.append(path_pos)
                    path_pos = v[path_pos][1]
                path.reverse()
                return path
            # otherwise check our possible moves from here
            cost_nxt = cost + 1
            for (x_nxt, y_nxt) in self._moves(node_x, node_y):
                enqueue = False
                est_nxt = cost_nxt + dist(x_nxt, y_nxt, x, y)
                if not (x_nxt, y_nxt) in v:
                    enqueue = True
                else:
                    cost_last = v[(x_nxt, y_nxt)][0]
                    if cost_last > est_nxt:
                        enqueue = True
                    else:
                        priority_idx = self._cur_priority(p, (x_nxt, y_nxt))
                        if priority_idx != -1:
                            if p[priority_idx][0] > est_nxt:
                                del p[priority_idx]
                                enqueue = True
                if enqueue:
                    p.append((est_nxt, (x_nxt, y_nxt)))
                    heapq.heapify(p)
                    v[(x_nxt, y_nxt)] = (est_nxt, (node_x, node_y))
        return None


class AStarPlayer(Player):
    name = "A* Player"

    def __init__(self):
        self.map = Map()

    def turn(self, surroundings):
        # TODO: save the path between turns

        # hack to handle victory condition
        if surroundings.left == Finish:
            return moves.LEFT
        if surroundings.right == Finish:
            return moves.RIGHT
        if surroundings.up == Finish:
            return moves.UP
        if surroundings.down == Finish:
            return moves.DOWN

        self.map.remember_surroundings(surroundings)
        if DEBUG:
            self.map.dump()
        shortest_path = None
        for candidate in self.map.all_interesting():
            path = self.map.find_path_to(candidate[0], candidate[1])
            if path is None:
                # this should never happen, but...
                continue
            if (shortest_path is None) or (len(path) < len(shortest_path)):
                shortest_path = path
        if DEBUG:
            print(shortest_path)
        next_pos = shortest_path[0]
        if DEBUG:
            input()
        if self.map.pos_x+1 == next_pos[0]:
            self.map.move_right()
            return moves.RIGHT
        if self.map.pos_x-1 == next_pos[0]:
            self.map.move_left()
            return moves.LEFT
        if self.map.pos_y+1 == next_pos[1]:
            self.map.move_up()
            return moves.UP
        if self.map.pos_y-1 == next_pos[1]:
            self.map.move_down()
            return moves.DOWN
        return "pass"
