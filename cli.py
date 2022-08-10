import os

from core.utils.loggining import logger
from core.server.server import Server
from config.config import get_config
from settings import BASE_DIR


class App:
    def __init__(self):
        logger.info(f"Current run dir: {os.getcwd()}")
        conf = get_config(f"{BASE_DIR}/applied_files/config/config.json")
        self.server = Server(conf)

    def run(self):
        self.server.run()


if __name__ == '__main__':
    App().run()
