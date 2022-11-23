import random
import subprocess

import psutil
from kivy.clock import Clock
from kivy.config import ConfigParser
from kivy.uix.screenmanager import Screen
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.event import EventDispatcher
from kivy.properties import (
    StringProperty,
    BooleanProperty,
    NumericProperty,
    BoundedNumericProperty,
)


class Tile(ButtonBehavior, Image):
    def __init__(self, name, **kwargs):
        self.name = name
        super().__init__(**kwargs)


class Player(EventDispatcher):
    active = BooleanProperty(False)
    display_score = StringProperty("0")
    name = StringProperty("")
    active_dice_image = StringProperty()
    score = NumericProperty(0)
    winner = BooleanProperty(False)

    def __init__(
        self, name, dice, dice_image, winner_dice_image, active=False, **kwargs
    ) -> None:
        super(Player, self).__init__(**kwargs)
        self.dice = dice
        self.dice_image = dice_image
        self.winner_dice_image = winner_dice_image
        self.active_dice_image = dice_image
        self.active = active
        self.name = name

    def on_winner(self, obj, value):
        if value:
            obj.score += 1


class ExecutableClient:
    def __init__(self, path, dice):
        self.path = path
        self.dice = dice
        self.proc = None

        self.start()

    def start(self):
        self.proc = subprocess.Popen(self.path, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def stop(self):
        try:
            process = psutil.Process(self.proc.pid)
            for candidate in process.children(recursive=True):
                try:
                    candidate.kill()
                except:
                    pass
            process.kill()
        except:
            pass

    def send(self, value: str):
        if not isinstance(value, str):
            value = str(value)

        print(f"[{self.dice}] Sending value: {value}")
        self.proc.stdin.write(value.encode("utf-8"))
        if not value.endswith("\n"):
            self.proc.stdin.write("\n".encode("utf8"))
        self.proc.stdin.flush()

    def read_line(self):
        print(f"[{self.dice}] Reading value ...")
        x = self.proc.stdout.readline().decode("utf8").strip()
        print(f"[{self.dice}] Read value {x}")
        return x

    def __str__(self):
        return self.dice

    def __repr__(self):
        return self.__str__()


class TicTacToe(Screen):
    player1 = Player(
        name="Player 1",
        dice="X",
        dice_image="assets/images/X.png",
        winner_dice_image="assets/images/X-WIN.png",
        active=True,
    )
    player2 = Player(
        name="Player 2",
        dice="O",
        dice_image="assets/images/O.png",
        winner_dice_image="assets/images/O-WIN.png",
    )
    dim = NumericProperty()
    points_to_win = 5
    rows = BoundedNumericProperty(0)
    cols = BoundedNumericProperty(0)
    game_over = BooleanProperty(False)
    is_draw = BooleanProperty(False)
    winner_dice_image = StringProperty("")
    matrix = {}
    tiles = {}
    move_scheduler = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        config = ConfigParser.get_configparser("app")

        dim = int(config.get("board", "dimensions"))
        self.dim = dim
        TicTacToe.dim = dim
        self.rows = dim
        self.cols = dim

    player1_executable = None
    player2_executable = None

    def on_pre_enter(self, *args):

        self._highlight_active_player()
        return super().on_pre_enter(*args)

    def on_leave(self, *args):
        self._reset()
        self.player1_executable.stop()
        self.player2_executable.stop()
        return super().on_leave(*args)

    def on_enter(self, *args):
        config = ConfigParser.get_configparser("app")
        self.player1_executable = ExecutableClient(config.get("executables", "player1"), self.player1.dice)
        self.player2_executable = ExecutableClient(config.get("executables", "player2"), self.player2.dice)

        for ex, p in [(self.player1_executable, self.player1), (self.player2_executable, self.player2)]:
            ex.send(self.dim)
            ex.read_line()
            ex.send(p.dice)
            ex.read_line()
            ex.send(p.active)
            ex.read_line()

        self.move_scheduler = Clock.schedule_interval(self.computer_move, 0.5)
        return super().on_enter(args)

    def on_game_over(self, instance, value):
        if value:
            pass
            # Clock.schedule_once(self._switch_to_menu, 0.5)

    def _switch_to_menu(self, duration):
        self.manager.transition.direction = "left"
        self.manager.transition.duration = 0.5
        self.manager.current = "menu"

    def _current_player(self):
        player = self.player1 if self.player1.active else self.player2
        return player

    def _switch_player(self):
        self.player1.active, self.player2.active = (
            not self.player1.active,
            not self.player2.active,
        )

    def _reset(self):
        self.game_over = False
        self.player1.winner = False
        self.player2.winner = False
        self.matrix.clear()
        for tile in self.tiles.values():
            tile.source = ""

    def _highlight_winner(self, player, winner_matrix):
        for tile_name in winner_matrix:
            if tile_name in self.tiles:
                self.tiles[tile_name].source = player.winner_dice_image
            else:
                print(f"Whoa, what happened to {tile_name} ?")

    def _highlight_active_player(self):
        if not self.game_over:
            for player in [self.player1, self.player2]:
                if player.active:
                    player.active_dice_image = player.winner_dice_image
                else:
                    player.active_dice_image = player.dice_image

    def _set_winner(self, player, best_points):
        if len(best_points) == TicTacToe.points_to_win:
            player.winner = True
            self.game_over = True
            self.is_draw = False
            self.winner_dice_image = player.winner_dice_image
            self._highlight_winner(player, best_points)
            return True
        return False

    def _get_tile_name(self, row_index, column_index):
        return "{row}.{col}".format(row=int(row_index), col=int(column_index))

    def _check_dice_points(self, row_index, column_index, x_points, o_points):
        tile_name = self._get_tile_name(row_index, column_index)
        dice = self.matrix.get(tile_name)
        if dice == self.player1.dice:
            x_points += 1
        elif dice == self.player2.dice:
            o_points += 1
        return x_points, o_points

    def _check_player_points(self, player, start_x, start_y):
        directions = [(-1, -1), (-1, 0), (0, +1), (0, -1), (0, +1), (+1, -1), (+1, 0), (+1, +1)]
        tile_name = self._get_tile_name(start_x, start_y)
        dice = self.matrix.get(tile_name)
        if dice == player.dice:
            scores = {}
            for direction in directions:
                x = start_x
                y = start_y
                tile_name = self._get_tile_name(x, y)
                scores[direction] = [tile_name]

                for offset in range(TicTacToe.points_to_win - 1):
                    x += direction[0]
                    y += direction[1]
                    if (0 <= x < TicTacToe.dim) and (0 <= y < TicTacToe.dim):
                        tile_name = self._get_tile_name(x, y)
                        dice = self.matrix.get(tile_name)
                        if dice == player.dice:
                            scores[direction].append(tile_name)
            s = dict(sorted(scores.items(), key=lambda item: len(item[1])))
            return list(s.values())[-1]  # best score
        else:
            return []

    def _check_winner(self):
        for player in [self.player1, self.player2]:
            for row_index in range(self.rows):
                for column_index in range(self.cols):
                    best = self._check_player_points(player, row_index, column_index)
                    if self._set_winner(player, best):
                        return

    def _check_draw(self):
        if not self.game_over and len(self.matrix) >= self.dim * self.dim:
            self.game_over = True
            self.is_draw = True

    def _check_move(self):
        self._check_winner()
        self._check_draw()

    def _record_move(self, tile):
        player = self._current_player()
        tile.source = player.dice_image
        self.matrix[tile.name] = player.dice
        self.tiles[tile.name] = tile
        self._switch_player()

    def reset_scores(self):
        self.player1.score = 0
        self.player2.score = 0

    def computer_move(self, interval):
        if self.game_over:
            Clock.unschedule(self.move_scheduler)
            self.move_scheduler = None
            return

        players = [self.player1_executable, self.player2_executable] if self.player1.active else [self.player2_executable, self.player1_executable]
        move = players[0].read_line()
        players[1].send(move)

        move = move.replace(" ", "").replace(",", ".")
        for candidate in self.ids["grid_layout"].children:
            if candidate.name == move:
                self.make_move(candidate)
                break
        else:
            print(f"Couldn't find tile for move {move}")

    def make_move(self, tile):
        if not tile.source and not self.game_over:
            self._record_move(tile)
            self._check_move()
            self._highlight_active_player()
