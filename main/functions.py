import os
import json
import requests
import time
import subprocess
import re
import zipfile
import shutil
import configparser

from datetime import datetime

local_folder_path = os.environ.get("LOCALAPPDATA")
data_path = os.path.join(local_folder_path, "HoYo ToolBox") # pyright: ignore[reportCallIssue, reportArgumentType]
exception = 123

def fetch_data_by_api(command, path, categories, gacha_size, game):
    result = subprocess.run(["powershell", "-Command", "Get-Clipboard", command], capture_output=True, text=True).stdout.split("\n")
    result = result[-3]
    UID = ""

    if not result.startswith("https"):
        exception.replace("Fetch failed!")

    if game == "原神":
        result += "hk4e_global&size=20&gacha_type=301&end_id="

    elif game == "崩鐵":
        result += "&size=20&gacha_type=11&end_id="

    elif game == "絕區零":      
        page_index = result.find("&page")
        result = result[:page_index]
        result += "&size=20&real_gacha_type=1&end_id="

    response = requests.get(result)
    resdict = response.json()

    account = resdict["data"]["list"][0]["uid"]

    data = {}

    path = path[:-5] + f"_{account}" + ".json"

    if os.path.exists(path):
        with open(path, "r", encoding="utf8") as file:
            existed_data = json.load(file)
    else:
        existed_data = {key: [] for key in categories.keys()}

    for key, value in categories.items():
        latest_id = existed_data[key][0]['id'] if key in existed_data and len(existed_data[key]) >= 1 else ""

        if "info" not in data:
            data["info"] = {
                "export_app":"HOYO ToolBox",
                "timezone": resdict["data"]["region_time_zone"] if "region_time_zone" in resdict["data"] else 0
            }

        data[key] = []

        if game == "原神":
            url = result.replace("gacha_type=301", f"gacha_type={value}")

        elif game == "崩鐵":
            url = result.replace("gacha_type=11", f"gacha_type={value}")

        elif game == "絕區零":
            url = result.replace("gacha_type=1", f"gacha_type={value}")
        
        print(f"正在讀取 {key} 的資料")

        while True:
            response = requests.get(url)
            resdict = response.json()

            if resdict["data"]["list"] == []:
                time.sleep(0.5)
                break
                
            if UID == "":
                UID = resdict["data"]["list"][0]["uid"]
 
            if "lang" not in data["info"]:
                data["info"]["lang"] = resdict["data"]["list"][0]["lang"]

            new_list = [item for item in resdict["data"]["list"] if item['id'] > latest_id]

            if new_list == []:
                time.sleep(0.5)
                break

            data[key].extend(new_list)
            last_id = new_list[-1]["id"]

            if "uid" not in data["info"]:
                data["info"]["uid"] = resdict["data"]["list"][0]["uid"]

            if last_id == latest_id:
                break

            end_id_index = url.find("end_id=")
            url = url[:end_id_index] + f"end_id={last_id}"

            time.sleep(0.5)

        data[key].extend(existed_data[key])

        print("讀取完成!")

    if game != "原神":
        data["info"]["version"] = "v4.0"

    with open(path, "w", encoding="utf8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    

def get_GSdata_by_api():
    command = "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex \"&{$((New-Object System.Net.WebClient).DownloadString('https://gist.github.com/MadeBaruna/1d75c1d37d19eca71591ec8a31178235/raw/getlink.ps1'))} global\""
    path = f"{data_path}/user_data/GenshinImpact.json"
    categories = {
        "novice": "100",
        "standard": "200",
        "characters": "301",
        "weapons": "302",
        "collection": "500"
    }
    
    fetch_data_by_api(command, path, categories, gacha_size=20, game="原神")

def get_HSRdata_by_api():
    command = "[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12; Invoke-Expression (New-Object Net.WebClient).DownloadString(\"https://gist.githubusercontent.com/Star-Rail-Station/2512df54c4f35d399cc9abbde665e8f0/raw/get_warp_link_os.ps1?cachebust=srs\")"
    path = f"{data_path}/user_data/Honkai_StarRail.json"
    categories = {
        "novice": "2",
        "standard": "1",
        "characters": "11",
        "weapons": "12",
    }
    fetch_data_by_api(command, path, categories, gacha_size=20, game="崩鐵")

def get_ZZZdata_by_api():
    command = "[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12; Invoke-Expression (New-Object Net.WebClient).DownloadString(\"https://zzz.rng.moe/scripts/get_signal_link_os.ps1\")"
    path = f"{data_path}/user_data/ZenlessZoneZero.json"

    category = {
        "standard": "1",
        "characters": "2",
        "weapons": "3",
        "bangboo": "5"
    }

    fetch_data_by_api(command, path, category, gacha_size=20, game="絕區零")

def get_average(file_path, game, input_text):
    # 定義標準角色和武器
    gi_standard_char = ["莫娜", "琴", "迪盧克", "迪希雅", "七七", "提納里", "刻晴"]
    hsr_standard_char = ["瓦爾特", "姬子", "彥卿", "布洛妮婭", "克拉拉", "白露", "傑帕德"]
    zzz_standard_char = ["貓又", "「11號」", "珂蕾妲", "萊卡恩", "格莉絲", "麗娜"]
    
    gi_standard_weapon = ["阿莫斯之弓", "天空之翼", "和璞鳶", "天空之脊", "四風原典", "天空之卷", "狼的末路", "天空之傲", "風鷹劍", "天空之刃"]
    hsr_standard_weapon = ["但戰鬥還未結束", "如泥酣眠", "以世界之名", "無可取代的東西", "銀河鐵道之夜", "時節不居", "制勝的瞬間"]
    zzz_standard_weapon = ["鋼鐵肉墊", "燃獄齒輪", "拘縛者", "硫磺石", "嵌合編譯器", "啜泣搖籃"]

    # 根據遊戲選擇標準角色和武器
    standard_char = gi_standard_char if game == "原神" else hsr_standard_char if game == "崩鐵" else zzz_standard_char
    standard_weapon = gi_standard_weapon if game == "原神" else hsr_standard_weapon if game == "崩鐵" else zzz_standard_weapon
    standard_items = standard_char + standard_weapon 

    # 初始化各種分類的列表
    novice, characters, weapons, standard = [], [], [], []
    limit_char, limit_weapon = [], []
    fivestar_novice, fivestar_standard, fivestar_char, fivestar_weapon = [], [], [], []

    # 定義類別映射
    category_map = {
        "novice": {"type": "100" if game == "原神" else "2" if game == "崩鐵" else "1", "list": novice, "fivestar_list": fivestar_novice},
        "standard": {"type": "200" if game == "原神" else "1" if game == "崩鐵" else "1", "list": standard, "fivestar_list": fivestar_standard},
        "characters": {"type": ["301", "400"] if game == "原神" else "11" if game == "崩鐵" else "2", "list": characters, "limit_list": limit_char, "fivestar_list": fivestar_char},
        "weapons": {"type": "302" if game == "原神" else "12" if game == "崩鐵" else "3", "list": weapons, "limit_list": limit_weapon, "fivestar_list": fivestar_weapon}
    }

    if game == "原神":
        collection, limit_coll, fivestar_coll = [], [], []
        category_map["collection"] = {"type": "500", "list": collection, "limit_list": limit_coll, "fivestar_list": fivestar_coll}

    elif game == "絕區零":
        bangboo, fivestar_bangboo = [], []
        category_map["bangboo"] = {"type": "5", "list": bangboo, "fivestar_list": fivestar_bangboo, "limit_list":[]}

    def process_item(item, category, standard_items):
        category["list"].append(item)
        if item["rank_type"] == "5":
            category["fivestar_list"].append(item)
            if item['name'] not in standard_items and item["gacha_type"] not in ["100", "200", "1", "2"]:
                category["limit_list"].append(item)

    def process_item_zzz(item, category, standard_items):
        category["list"].append(item)
        if item["rank_type"] == "4":
            category["fivestar_list"].append(item)
            if item['name'] not in standard_items and item["gacha_type"] in ["1", "2", "3", "5"]:
                category["limit_list"].append(item)

    if file_path:
        with open(file_path, "r", encoding="utf8") as file:
            data = json.load(file)

        for key in data:
            if key == "info":
                continue

            
            if game == "原神" and (len(data[key]) > 1 and data[key][0]['gacha_type'] not in ["100", "200", "301", "302", "400", "500"]):
                return "導入錯誤的遊戲資料"
            
            elif game == "崩鐵" and (len(data[key]) > 1 and data[key][0]['gacha_type'] not in ["1", "2", "11", "12"]):
                return "導入錯誤的遊戲資料"
            
            elif game == "絕區零" and (len(data[key]) > 1 and data[key][0]['gacha_type'] not in ["1", "2", "3", "5"]):
                return "導入錯誤的遊戲資料"
            
        for key, value in data.items():
            if key == "info":
                continue
            
            for item in value:
                for category, details in category_map.items():
                    category_type = details["type"]

                    if game != "絕區零":
                        if isinstance(category_type, list):
                            if item["gacha_type"] in category_type:
                                process_item(item, details, standard_items)
                            
                        else:
                            if item["gacha_type"] == category_type:
                                process_item(item, details, standard_items)

                    else:
                        if item["gacha_type"] == category_type:
                            process_item_zzz(item, details, standard_items)

        average_limit_character = round(len(characters) / len(limit_char), 2) if len(limit_char) > 0 else None
        average_limit_weapon = round(len(weapons) / len(limit_weapon), 2) if len(limit_weapon) > 0 else None

        average_novice = round((len(novice) / len(fivestar_novice)), 2) if len(fivestar_novice) > 0 else None
        average_character = round(len(characters) / len(fivestar_char), 2) if len(fivestar_char) > 0 else None
        average_weapon = round(len(weapons) / len(fivestar_weapon), 2) if len(fivestar_weapon) > 0 else None
        
        char_guarantee_rate = f"{round(((2 * len(limit_char) - len(fivestar_char)) / len(limit_char)) * 100, 2)} %" if len(fivestar_char) > 0 else None
        char_guarantee_rate = None if not char_guarantee_rate else "0.0 %" if "-" in char_guarantee_rate else char_guarantee_rate

        weapon_guarantee_rate = f"{round(((2 * len(limit_weapon) - len(fivestar_weapon)) / len(limit_weapon)) * 100, 2)} %" if len(fivestar_weapon) > 0 else None
        weapon_guarantee_rate = None if not weapon_guarantee_rate else "0.0 %" if "-" in weapon_guarantee_rate else weapon_guarantee_rate        

        status_text = f"限定池抽數：{len(characters)} | 限定角色數：{len(limit_char)} | 平均限定金：{average_limit_character} | 五星角色數：{len(fivestar_char)} | 平均五星金：{average_character} | 保底不歪率：{char_guarantee_rate}\n"
        status_text += f"武器池抽數：{len(weapons)} | 限定武器數：{len(limit_weapon)} | 平均限定金：{average_limit_weapon} | 五星武器數：{len(fivestar_weapon)} | 平均五星金：{average_weapon} | 保底不歪率：{weapon_guarantee_rate}\n"

        if game == "原神":
            average_limit_collection = round(len(collection) / len(limit_coll),2) if len(limit_coll) > 0 else None
            average_collection = round(len(collection) / len(fivestar_coll),2) if len(fivestar_coll) > 0 else None 
            coll_guarantee_rate = f"{round(((2 * (len(limit_coll) - len(fivestar_coll))) / len(limit_coll)), 2) * 100} %" if len(fivestar_coll) > 0 else None
            coll_guarantee_rate = None if not coll_guarantee_rate else "0.0 %" if "-" in coll_guarantee_rate else coll_guarantee_rate

            status_text += f"集錄池抽數：{len(collection)} | 限定數量：{len(limit_coll)} | 平均限定金：{average_limit_collection} | 五星數量：{len(fivestar_coll)} | 平均五星金：{average_collection} | 保底不歪率：{coll_guarantee_rate}\n"

        if game == "絕區零":
            average_bangboo = round(len(bangboo) / len(fivestar_bangboo),2) if len(fivestar_bangboo) > 0 else None

            status_text += f"邦布池抽數：{len(bangboo)} | 邦布五星數：{len(fivestar_bangboo)} | 平均五星數：{average_bangboo}\n"

        if game != "絕區零":
            status_text += f"新手池抽數：{len(novice)} | 新手五星數：{len(fivestar_novice)} | 平均五星數：{average_novice}\n"

        status_text += f"常駐池抽數：{len(standard)}"
        result_text = status_text
        
    else:
        items = input_text.split('\n')
        total = 0
        limit = []

        for item in items: 
            parts = re.findall(r'(\D+)(\d+)', item.strip()) 
            if parts: 
                name, count = parts[0][0], int(parts[0][1]) 
                total += count 
                if name.strip() not in standard_items: 
                    limit.append(name.strip())

        average = round(total / len(limit), 2) if len(limit) > 0 else None
        result_text = (
        f"總抽數：{total} | 限定數：{len(limit)} | 平均限定金：{average}"
    )
        
    return result_text


def compare_input_data(system_path, input_data, game):
    with open(system_path, "r", encoding="utf8") as file:
        system_data = json.load(file)   

    new_data = {}
    new_data["info"] = system_data["info"]
    keys = ["novice", "standard", "characters", "weapons"]

    if game == "原神":
        keys.append("collection")

    if game == "絕區零":
        keys.remove("novice")
        keys.append("bangboo")

    for key in keys:
        (system_data, input_data)
        input_latest_id = input_data[key][0]['id'] if (key in input_data) and (len(input_data[key]) > 0) else ""
        input_oldest_id = input_data[key][-1]['id'] if (key in input_data) and (len(input_data[key]) > 0) else ""

        system_latest_id = system_data[key][0]['id'] if (key in system_data) and (len(system_data[key]) > 0) else ""
        system_oldest_id = system_data[key][-1]['id'] if (key in system_data) and (len(system_data[key]) > 0) else ""

        if input_latest_id == "" and system_latest_id != "":
            new_data[key] = system_data[key]
        
        elif system_latest_id == "" and input_latest_id != "":
            new_data[key] = input_data[key]

        elif system_latest_id == input_latest_id == "":
            new_data[key] = []

        elif system_latest_id > input_latest_id:
            new_data[key] = [item for item in system_data[key] if item['id'] > input_latest_id]
            new_data[key].extend(input_data[key]) 

        elif system_latest_id < input_latest_id:
            new_data[key] = [item for item in input_data[key] if item['id'] > system_latest_id]
            new_data[key].extend(system_data[key])

        elif system_latest_id == input_latest_id:
            new_data[key] = system_data[key]

        if input_oldest_id == "" and system_oldest_id != "":
            new_data[key] = system_data[key]
        
        elif system_oldest_id == "" and input_oldest_id != "":
            new_data[key] = input_data[key]

        elif system_oldest_id == input_oldest_id == "":
            new_data[key] = []

        elif system_oldest_id > input_oldest_id:
            input_list = [item for item in input_data[key] if item['id'] < system_oldest_id]
            new_data[key].extend(input_list) 

        elif system_oldest_id < input_oldest_id:
            system_list = [item for item in input_data[key] if item['id'] < input_oldest_id]
            new_data[key].extend(system_list)

        elif system_oldest_id == input_oldest_id:
            new_data[key] = system_data[key]
                
    return new_data

def extract_data(game, input_path):
    with open(input_path, "r", encoding="utf8") as file:
        input_data = json.load(file)

    if "hkrpg" in input_data:
        input_data["info"]["uid"] = input_data["hkrpg"][0]["uid"]
        input_data["info"]["timezone"] = input_data["hkrpg"][0]["timezone"]
        input_data["info"]["lang"] = input_data["hkrpg"][0]["lang"]
        input_data['list'] = input_data["hkrpg"][0]['list']
        del input_data["hkrpg"]

    if "nap" in input_data:
        input_data["info"]["uid"] = input_data["nap"][0]["uid"]
        input_data["info"]["timezone"] = input_data["nap"][0]["timezone"]
        input_data["info"]["lang"] = input_data["nap"][0]["lang"]
        input_data['list'] = input_data["nap"][0]['list']
        del input_data["nap"]

    if game == "原神" and input_data["list"][0]["gacha_type"] not in ["100", "200", "301", "302", "400", "500"]:
        return "錯誤的遊戲資料"
    
    elif game == "崩鐵" and input_data["list"][0]["gacha_type"] not in ["1", "2", "11", "12"]:
        return "錯誤的遊戲資料"
    
    elif game == "絕區零" and input_data["list"][0]["gacha_type"] not in ["1", "2", "3", "5"]:
        return "錯誤的遊戲資料"

    novice = []
    standard = []
    character = []
    weapon = []
    new_data = {}

    if game == "原神":
        collection = []

        gacha_mapping = {
            "100": novice,
            "200": standard,
            "301": character,
            "400": character,
            "302": weapon,
            "500": collection
        }

        keys = {
            "100":"novice", 
            "200":"standard", 
            "301":"characters", 
            "302":"weapons", 
            "500":"collection"
            }

    elif game == "崩鐵":
        gacha_mapping = {
            "1": standard,
            "2": novice,
            "11": character,
            "12": weapon,
        }

        keys = {
            "2":"novice",
            "1":"standard", 
            "11":"characters", 
            "12":"weapons"
            }
        
    elif game == "絕區零":
        bangboo = []

        gacha_mapping = {
            "1": standard,
            "2": character,
            "3": weapon,
            "5": bangboo,
        }

        keys = {
            "1":"standard", 
            "2":"characters",
            "3":"weapons", 
            "5":"bangboo"
            }
        
    new_data["info"] = input_data["info"]

    for item in input_data["list"]:
        gacha_list = gacha_mapping.get(item["gacha_type"])
        
        if gacha_list is not None:
            gacha_list.append(item)


    for key, value in keys.items():
        new_data[value] = gacha_mapping.get(key)[::-1]


    for key in new_data:
        if key == "info" or new_data[key] == []:
            continue

        for item in new_data[key]:
            item["uigf_gacha_type"] = "400" if (game == "原神" and item["gacha_type"] == "301") else item["gacha_type"]

    return new_data


def export_json(file_path, folder_path, game):
    with open(file_path, "r", encoding="utf8") as file:
        data = json.load(file)

    new_data = {}
    new_data["info"] = data["info"]

    
    if game == "原神":
        new_data["list"] = []

    if game == "崩鐵":
        new_data["info"]["version"] = "v4.0"
        new_data["hkrpg"] = [{}]
        new_data["hkrpg"][0]["uid"] = data["info"]["uid"]
        new_data["hkrpg"][0]["lang"] = data["info"]["lang"]
        new_data["hkrpg"][0]["timezone"] = data["info"]["region_time_zone"]
        new_data["hkrpg"][0]["list"] = []

    if game == "絕區零":
        new_data["info"]["version"] = "v4.0"
        new_data["nap"] = [{}]
        new_data["nap"][0]["uid"] = data["info"]["uid"]
        new_data["nap"][0]["lang"] = data["info"]["lang"]
        new_data["nap"][0]["timezone"] = data["info"]["timezone"]

        new_data["nap"]["list"] = []


    new_data["info"]["export_time"] = datetime.now().strftime("%Y/%m/%d %H：%M：%S")

    for key in data:
        if key == "info":
            continue

        if game == "原神":
            new_data["list"].extend(data[key])
            new_data['list'].sort(key=lambda x: x['id'])

        if game == "崩鐵":
            new_data["hkrpg"][0]["list"].extend(data[key])
            new_data["hkrpg"][0]['list'].sort(key=lambda x: x['id'])

        if game == "絕區零":
            new_data["nap"][0]["list"].extend(data[key])
            new_data["hknap"][0]['list'].sort(key=lambda x: x['id'])

    new_data["info"]["export_app"] = "HOYO ToolBox"

    with open(folder_path, "w", encoding="utf8") as new_file:
        json.dump(new_data, new_file, indent=4, ensure_ascii=False)

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
        data['version'] = name_list[2][1:] + "." + name_list[3]
        data['name'] = asset['name']
        data['total_size'] = asset['size']
        data['path'] = f"./{asset['name']}"
        temp_path = "./temp"

        if not os.path.exists(temp_path):
            os.mkdir(temp_path)

        return data


def apply_update(zip_path, version):
    config = configparser.ConfigParser()
    config.read('config.ini')
    # 檢查解壓縮目的地資料夾是否存在，若不存在則創建
    if not os.path.exists("./temp"):
        os.makedirs("./temp")

    # 開啟 zip 檔案
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # 解壓所有檔案到指定資料夾
        zip_ref.extractall("./temp")
    
    file_path = (f"./temp/HOYO ToolBox v{version}")

    for file in os.listdir(file_path):
        source_path = os.path.join(file_path, file)
        try:
            shutil.copy(source_path, "./")
        except Exception as e:
            print(e)

    config.set('General', 'version', version)
    with open('config.ini', 'w') as configfile:
        config.write(configfile)
    
    shutil.rmtree("./temp")
    os.remove(zip_path)