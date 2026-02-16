from Client.client import Client
from config_manager import ConfigManager


if __name__ == "__main__":
    config = ConfigManager()
    client = Client(config)
    client.run()
