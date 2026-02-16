import sys
from GUIClient.gui_client import GUIClient
from config_manager import ConfigManager


if __name__ == "__main__":
    config = ConfigManager()
    client = GUIClient(config)
    sys.exit(client.run())
