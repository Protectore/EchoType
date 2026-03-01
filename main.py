from STTServer.stt_server import STTServer
from Utility import ConfigManager


if __name__ == "__main__":
    config = ConfigManager()
    sttServer = STTServer(config)
    sttServer.run()
