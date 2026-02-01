from STTServer.stt_server import STTServer
from config_manager import ConfigManager


def main():
    print("Hello from echotype!")


if __name__ == "__main__":
    config = ConfigManager()
    sttServer = STTServer(config)
    sttServer.run()
