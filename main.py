import os
import sys

from kivy.app import App
from kivy.lang import Builder
from kivy.properties import BoundedNumericProperty
from kivy.resources import resource_add_path

from screens.tictactoe import Tile


class MainApp(App):
    title = "Tic Tac Toe"
    player1_executable = ""
    player2_executable = ""

    def build_config(self, config):
        config.setdefaults("executables", {
            "player1": "poetry run python client\\ttt_client.py",
            "player2": "poetry run python client\\ttt_client.py"
        })
        config.setdefaults("board", {
            "dimensions": 50
        })

    def get_application_config(self, defaultpath='%(appdir)s/%(appname)s.ini'):
        return str("./server.ini")

    def build(self):
        manager = Builder.load_file("templates/screen_manager.kv")
        self._build_grid_layout(manager)
        return manager

    def _build_grid_layout(self, manager):
        for row in range(manager.ids.tictactoe.rows):
            for column in range(manager.ids.tictactoe.cols):
                manager.screens[1].ids.grid_layout.add_widget(Tile("%d.%d" % (row, column)))
        return manager


if __name__ == "__main__":
    if hasattr(sys, '_MEIPASS'):
        resource_add_path(os.path.join(sys._MEIPASS))

    if getattr(sys, 'frozen', False):
        # this is a Pyinstaller bundle
        resource_add_path(sys._MEIPASS)
        resource_add_path(os.path.join(sys._MEIPASS, 'DATA'))

    main = MainApp()

    main.run()
