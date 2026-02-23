from Client import CliClient
from config_manager import ConfigManager


if __name__ == "__main__":
    config = ConfigManager()
    client = CliClient(config)
    client.run()
