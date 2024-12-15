import sqlite3
import json
import genshin
import os

from datetime import datetime

def read_cookies(cookie_file_path):
    if not os.path.exists(cookie_file_path):
        print(f"檔案 {cookie_file_path} 不存在!")
        return None

    conn = sqlite3.connect(cookie_file_path)
    cursor = conn.cursor()

    # 查詢 cookies 表格
    cursor.execute('SELECT name, value FROM cookies')
    cookies = cursor.fetchall()

    cookie_dict = {}
    for cookie in cookies:
        cookie_dict[cookie[0]] = cookie[1]

    conn.close()

    return cookie_dict

local_folder_path = os.environ.get("LOCALAPPDATA")
data_path = os.path.join(local_folder_path, "HoYo ToolBox") # pyright: ignore[reportCallIssue, reportArgumentType]
diary_path = os.path.join(data_path, "diary")
cookie_file_path = os.path.join(data_path, "QtWebEngine/Default/Cookies")

class CookieNotFound(Exception):
    pass

class API_function():
    def __init__(self):
        self.cookies = read_cookies(cookie_file_path)

        if not self.cookies:
            raise CookieNotFound("Cookie Not Found！")
        
        self.lang = self.cookies["mi18nLang"]
        self.client = genshin.Client(self.cookies, lang=self.lang)
        self.diary_path = diary_path


    #原神
    async def get_genshin_accounts(self):
        accounts = await self.client.get_game_accounts()
        account_list = [str(account.uid) for account in accounts if account.game.name == "GENSHIN"]

        return account_list

    async def get_genshin_diary(self, uid):
        diary = await self.client.get_genshin_diary(uid)
        diary_data = json.loads(diary.model_dump_json())
        uid = diary_data["uid"]
        month = diary_data["month"]
        current_year = datetime.now().year
        self.diary_path = os.path.join(self.diary_path, f"GenshinImpact_{uid}_{month}_{current_year}.json")

        with open(self.diary_path, "w", encoding="utf8") as file:
            json.dump(diary_data, file, indent=4, ensure_ascii=False)

    async def get_genshin_notes(self, uid):
        info = await self.client.get_genshin_user(uid=uid)
        notes = await self.client.get_genshin_notes(uid=uid)

        info_data = json.loads(info.model_dump_json())
        notes_data = json.loads(notes.model_dump_json())

        notes_data["info"] = info_data["info"]
        
        return notes_data




    ##崩鐵
    async def get_starrail_accounts(self):
        accounts = await self.client.get_game_accounts()
        account_list = [str(account.uid) for account in accounts if account.game.name == "STARRAIL"]

        return account_list

    async def get_starrail_diary(self, uid):
        diary = await self.client.get_starrail_diary(uid)
        diary_data = json.loads(diary.model_dump_json())
        uid = diary_data["uid"]
        month = str(diary_data["month"])[4:]
        current_year = datetime.now().year
        self.diary_path = os.path.join(self.diary_path, f"HonkaiStarRail_{uid}_{month}_{current_year}.json")

        with open(self.diary_path, "w", encoding="utf8") as file:
            json.dump(diary_data, file, indent=4, ensure_ascii=False)

    async def get_starrail_notes(self, uid):
        info = await self.client.get_starrail_user(uid)
        notes = await self.client.get_starrail_notes(uid)

        info_data = json.loads(info.model_dump_json())
        notes_data = json.loads(notes.model_dump_json())

        notes_data["info"] = info_data["info"]
        
        return notes_data

    ##崩鐵
    async def get_zzz_accounts(self):
        accounts = await self.client.get_game_accounts()
        account_list = [str(account.uid) for account in accounts if account.game.name == "ZZZ"]

        return account_list

    async def get_zzz_diary(self, uid):
        diary = await self.client.get_zzz_diary(uid)
        diary_data = json.loads(diary.model_dump_json())
        uid = diary_data["uid"]
        month = str(diary_data["data_month"])[4:]
        diary_data['nickname'] = diary_data['player']['nickname']
        diary_data['avatar_url'] = diary_data['player']['avatar_url']
        diary_data['server'] = diary_data['region']

        current_year = datetime.now().year
        self.diary_path = os.path.join(self.diary_path, f"ZenlessZoneZero_{uid}_{month}_{current_year}.json")

        with open(self.diary_path, "w", encoding="utf8") as file:
            json.dump(diary_data, file, indent=4, ensure_ascii=False)

    async def get_zzz_notes(self, uid):
        notes = await self.client.get_zzz_notes(uid)

        notes_data = json.loads(notes.model_dump_json())

        notes_data["info"] = {}
        notes_data["info"]["nickname"] = ""
        notes_data["info"]["level"] = ""
        
        return notes_data
    
    

