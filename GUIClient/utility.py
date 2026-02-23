class GuiUtility:
    @staticmethod
    def read_style_file(style_file_name: str) -> str:
        """Загрузка стилей из внешнего .qss файла"""
        path = f"./GUIClient/Style/{style_file_name}.qss"
        with open(path, "r", encoding="utf-8") as file:
            stylesheet = file.read()  # Read the entire file content into a string
            return stylesheet
