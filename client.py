from VoiceClient.voice_client import VoiceRecorderClient
from config_manager import ConfigManager


if __name__ == "__main__":
    config = ConfigManager()
    sttServer = VoiceRecorderClient(config)
    sttServer.run()
