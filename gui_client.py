import sys
from GUIClient.gui_client import GUIClient
from Utility import ConfigManager


if __name__ == "__main__":
    config = ConfigManager()
    client = GUIClient(config)
    sys.exit(client.run())
