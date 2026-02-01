import requests

from config_manager import ConfigManager

config = ConfigManager()
base_url = config.get_server_url()

print(base_url)


def PrintResponse(response: requests.Response, shoudPrintTime:bool=False ):
    method_and_url = str(response.request.method) + " " + response.url
    print()
    print(method_and_url.center(50, "="))
    status_code_mark = "✅" if str(response.status_code)[0] == "2" else "❔"
    print(f"Status code = {response.status_code} {status_code_mark}")
    print("Response data:")
    print(response.json())
    if (shoudPrintTime):
        print(f"Elapsed time: {response.elapsed.total_seconds()}s ⌚")
    print("=" * 50)
    print()


def TestGetAppRoot():
    response = requests.get(base_url)
    PrintResponse(response)


def TestAppHealth():
    response = requests.get(base_url + "/health")
    PrintResponse(response)

def TestTranscribe(testVoicePath: str):
    with open(testVoicePath, "rb") as f:
        files = {"audio": f}
        response = requests.post(base_url + "/transcribe", files=files)
        PrintResponse(response, shoudPrintTime=True)


def TestSttServer():
    TestGetAppRoot()
    TestAppHealth()
    TestTranscribe("./Tests/TestData/Kostya.wav")
