import os
import requests
import zipfile
import shutil
import configparser

temp_path = os.environ.get("TEMP")
if not os.path.exists(f"{temp_path}/HOYO ToolBox"):
    os.makedirs(f"{temp_path}/HOYO ToolBox/temp", exist_ok=True)

def check_version():
    config = configparser.ConfigParser()
    config.read('config.ini')
    # GitHub API URL for the latest release
    url = 'https://api.github.com/repos/jenne14294/HOYO-ToolBox/releases/latest'
    
    # Send a GET request to fetch the latest release data
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code != 200:
        return False
    
    # Extract the release data from the response
    release_data = response.json()
    latest_version = release_data["html_url"][release_data["html_url"].index("tag/") + 5:]

    system_version = config.get('General', 'version')

    if latest_version > system_version:
        return True
    
    else:
        return False
    
def download_release():
    # GitHub API URL for the latest release
    url = 'https://api.github.com/repos/jenne14294/HOYO-ToolBox/releases/latest'
    
    # Send a GET request to fetch the latest release data
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code != 200:
        return False
    
    # Extract the release data from the response
    release_data = response.json()
    data = {}
    # Iterate through the assets and download them
    for asset in release_data['assets']:
        name_list = asset['name'].split(".")

        data['url'] = asset['browser_download_url']
        data['version'] = name_list[2][1:]
        data['name'] = asset['name']
        data['total_size'] = asset['size']
        data['path'] = f"{temp_path}/HOYO ToolBox/{asset['name']}"

        for i in range(3, len(name_list) - 1):
            data['version'] += f".{name_list[i]}"

        path = f"{temp_path}/HOYO ToolBox/temp"
        if not os.path.exists(path):
            os.mkdir(path)

        return data


def apply_update(zip_path, version):
    config = configparser.ConfigParser()
    config.read('config.ini')
    path = f"{temp_path}/HOYO ToolBox/temp"
    print(version)
    # 檢查解壓縮目的地資料夾是否存在，若不存在則創建
    if not os.path.exists(path):
        os.makedirs(path)

    # 開啟 zip 檔案
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # 解壓所有檔案到指定資料夾
        zip_ref.extractall(path)
    
    file_path = (f"{path}/HOYO ToolBox v{version}")
    print(file_path)

    for file in os.listdir(file_path):
        source_path = os.path.join(file_path, file)

        try:
            if os.path.isdir(source_path):
                shutil.copytree(source_path, "./")
                break

            shutil.copy(source_path, "./")
            
        except Exception as e:
            print(e)

    config.set('General', 'version', version)
    with open('config.ini', 'w') as configfile:
        config.write(configfile)