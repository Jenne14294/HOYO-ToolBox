import os
import json
import sys
import customtkinter as ctk
import threading
import textwrap
import functions

from tkinter import messagebox, filedialog
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QComboBox, QLabel, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView

# Initialize custom tkinter
ctk.set_appearance_mode("System")  # Modes: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "dark-blue", "green"

local_folder_path = os.environ.get("LOCALAPPDATA")
data_path = os.path.join(local_folder_path, "HoYo ToolBox")  # pyright: ignore[reportCallIssue, reportArgumentType]
user_path = os.path.join(data_path, "user_data")

# PyQt5部分
def start_pyqt5_app(game):
    if game == "原神":
        url = "https://act.hoyolab.com/app/community-game-records-sea/index.html?bbs_presentation_style=fullscreen&bbs_auth_required=true&v=104&gid=2&utm_source=hoyolab&utm_medium=tools&bbs_theme=dark&bbs_theme_device=1#/ys"
    elif game == "崩鐵":
        url = "https://act.hoyolab.com/app/community-game-records-sea/rpg/index.html?bbs_presentation_style=fullscreen&gid=6&utm_campaign=battlechronicle&utm_id=6&utm_medium=tools&utm_source=hoyolab&v=101&bbs_theme=dark&bbs_theme_device=0#/hsr"
    elif game == "絕區零":
        url = "https://act.hoyolab.com/app/zzz-game-record/index.html?hyl_presentation_style=fullscreen&utm_campaign=battlechronicle&utm_id=8&utm_medium=tools&utm_source=hoyolab&lang=zh-tw&bbs_theme=dark&bbs_theme_device=0#/zzz"

    app = QApplication([])

    # 創建主窗口
    window = QWidget()
    window.setWindowTitle("HOYO 工具箱")

    # 設定窗口的大小
    window.resize(1200, 800)

    # 設定窗口的背景顏色
    window.setStyleSheet("background-color: #2f2f2f;")

    # 創建QWebEngineView來顯示網頁
    webview = QWebEngineView()
    webview.setUrl(QUrl(url))

    # 設置Webview的樣式
    webview.setStyleSheet("border: none;")

    # 創建佈局
    layout = QVBoxLayout()

    # 添加標題文字
    title_label = QLabel("選擇遊戲以查看詳細資料")
    title_label.setStyleSheet("font-size: 24px; color: #ffffff; font-weight: bold; margin-bottom: 20px;")
    title_label.setFixedHeight(50)
    layout.addWidget(title_label)

    # 創建水平布局來放下拉選單和四個按鈕
    h_layout = QHBoxLayout()

    # 創建下拉選單
    combo_box = QComboBox()
    combo_box.setFixedWidth(150)  # 设置固定宽度为 150
    combo_box.addItem("原神")
    combo_box.addItem("崩鐵")
    combo_box.addItem("絕區零")

    # 設定下拉選單的樣式
    combo_box.setStyleSheet("""
        QComboBox {
            background-color: #444444;
            color: white;
            padding: 10px;
            border-radius: 5px;
            font-size: 16px;
        }
        QComboBox::drop-down {
            background-color: #555555;
        }
    """)

    # 當選擇項目改變時的處理函數
    def on_combobox_changed(index):
        selected_option = combo_box.currentText()
        if selected_option == "原神":
            url = "https://act.hoyolab.com/app/community-game-records-sea/index.html?bbs_presentation_style=fullscreen&bbs_auth_required=true&v=104&gid=2&utm_source=hoyolab&utm_medium=tools&bbs_theme=dark&bbs_theme_device=1#/ys"

        elif selected_option == "崩鐵":
            url = "https://act.hoyolab.com/app/community-game-records-sea/rpg/index.html?bbs_presentation_style=fullscreen&gid=6&utm_campaign=battlechronicle&utm_id=6&utm_medium=tools&utm_source=hoyolab&v=101&bbs_theme=dark&bbs_theme_device=0#/hsr"

        elif selected_option == "絕區零":
            url = "https://act.hoyolab.com/app/zzz-game-record/index.html?hyl_presentation_style=fullscreen&utm_campaign=battlechronicle&utm_id=8&utm_medium=tools&utm_source=hoyolab&lang=zh-tw&bbs_theme=dark&bbs_theme_device=0#/zzz"

        selected_game.set(selected_option)
        webview.setUrl(QUrl(url))

    # 設置當選擇的項目改變時觸發的事件
    combo_box.currentIndexChanged.connect(on_combobox_changed)

    # 創建按鈕外觀
    combo_box.setFixedHeight(40)
    button_style = "background-color: #444444; color: white; padding: 10px; border-radius: 5px; font-size: 16px;"

    # 創建按鈕並設置樣式
    button1 = QPushButton("查看戰績")
    button2 = QPushButton("每日簽到")
    button3 = QPushButton("兌換碼")

    if selected_game.get() != "絕區零":
        button4 = QPushButton("互動地圖")
        button4.setStyleSheet(button_style)
    
    # 設定按鈕樣式
    button1.setStyleSheet(button_style)
    button2.setStyleSheet(button_style)
    button3.setStyleSheet(button_style)

    # 按鈕按下時的處理函數
    def on_button_click(button_name):
        print(selected_game.get(), button_name)
        if "戰績" in button_name:
            if selected_game.get() == "原神":
                url = "https://act.hoyolab.com/app/community-game-records-sea/index.html?bbs_presentation_style=fullscreen&bbs_auth_required=true&v=104&gid=2&utm_source=hoyolab&utm_medium=tools&bbs_theme=dark&bbs_theme_device=1#/ys"
            
            elif selected_game.get() == "崩鐵":
                url = "https://act.hoyolab.com/app/community-game-records-sea/rpg/index.html?bbs_presentation_style=fullscreen&gid=6&utm_campaign=battlechronicle&utm_id=6&utm_medium=tools&utm_source=hoyolab&v=101&lang=zh-tw&bbs_theme=dark&bbs_theme_device=0#/hsr"

            elif selected_game.get() == "絕區零":
                url = "https://act.hoyolab.com/app/zzz-game-record/index.html?hyl_presentation_style=fullscreen&utm_campaign=battlechronicle&utm_id=8&utm_medium=tools&utm_source=hoyolab&bbs_theme=dark&bbs_theme_device=0#/zzz"

        elif "簽到" in button_name:
            if selected_game.get() == "原神":
                url = "https://act.hoyolab.com/ys/event/signin-sea-v3/index.html?act_id=e202102251931481&utm_source=hoyolab&utm_medium=tools&v=0928&lang=zh-tw&bbs_theme=dark&bbs_theme_device=1"

            elif selected_game.get() == "崩鐵":
                url = "https://act.hoyolab.com/bbs/event/signin/hkrpg/e202303301540311.html?act_id=e202303301540311&hyl_auth_required=true&hyl_presentation_style=fullscreen&utm_source=hoyolab&utm_medium=tools&utm_campaign=checkin&utm_id=6&lang=zh-tw&bbs_theme=dark&bbs_theme_device=0"

            elif selected_game.get() == "絕區零":
                url = "https://act.hoyolab.com/bbs/event/signin/zzz/e202406031448091.html?act_id=e202406031448091&hyl_auth_required=true&hyl_presentation_style=fullscreen&utm_campaign=checkin&utm_id=8&utm_medium=tools&utm_source=hoyolab&lang=zh-tw&bbs_theme=dark&bbs_theme_device=0"

        elif "兌換碼" in button_name:
            if selected_game.get() == "原神":
                url = "https://genshin.hoyoverse.com/zh-tw/gift"

            elif selected_game.get() == "崩鐵":
                url = "https://hsr.hoyoverse.com/gift?lang=zh-tw"

            elif selected_game.get() == "絕區零":
                url = "https://zenless.hoyoverse.com/redemption?lang=zh-tw"


        elif "地圖" in button_name:
            if selected_game.get() == "原神":
                url = "https://act.hoyolab.com/ys/app/interactive-map/index.html?bbs_presentation_style=no_header&utm_source=hoyolab&utm_medium=tools&lang=zh-tw&bbs_theme=dark&bbs_theme_device=1#/map/2?shown_types=3,154,212"

            elif selected_game.get() == "崩鐵":
                url = "https://act.hoyolab.com/sr/app/interactive-map/index.html?hyl_presentation_style=fullscreen&utm_campaign=map&utm_id=6&utm_medium=tools&utm_source=hoyolab&lang=zh-tw&bbs_theme=dark&bbs_theme_device=0#/map/325?zoom=-1.00&center=92.00,41.00"

            elif selected_game.get() == "絕區零":
                url = "https://act.hoyolab.com/app/zzz-game-record/index.html?hyl_presentation_style=fullscreen&utm_campaign=battlechronicle&utm_id=8&utm_medium=tools&utm_source=hoyolab&bbs_theme=dark&bbs_theme_device=0#/zzz"


        webview.setUrl(QUrl(url))

    # 設置按鈕點擊事件
    button1.clicked.connect(lambda: on_button_click("戰績"))
    button2.clicked.connect(lambda: on_button_click("簽到"))
    button3.clicked.connect(lambda: on_button_click("兌換碼"))
    button4.clicked.connect(lambda: on_button_click("地圖"))

    # 將下拉選單和按鈕放入水平佈局中
    h_layout.addWidget(combo_box)
    h_layout.addWidget(button1)
    h_layout.addWidget(button2)
    h_layout.addWidget(button3)

    if selected_game.get() != "絕區零":
        h_layout.addWidget(button4)

    # 添加到主佈局中
    layout.addLayout(h_layout)

    # 設定網頁顯示的佈局
    layout.addWidget(webview)

    window.setLayout(layout)

    # 顯示窗口
    window.show()

    # 開始應用的事件循環
    app.exec_()

# Main window
root = ctk.CTk()
root.title("抽卡紀錄與HOYO工具箱")
root.geometry("1200x600")

selected_game = ctk.StringVar(value="原神")
selected_category = ctk.StringVar(value="角色")
selected_game_path = ctk.StringVar()

input_frame = ctk.CTkFrame(root, fg_color="white")
message_label = ctk.CTkLabel(root, text="", font=("Arial", 14), text_color="black", anchor="w")

# Helper functions
def change_account(account):
    selected_account.set(account)
    show_record_options()

def get_options():
    account_options = []
    folder_path = f"{data_path}/user_data"
    if not os.path.exists(folder_path):
        return account_options

    for file in os.listdir(folder_path):
        start_index = file.find("_", 10)
        end_index = file.find(".json")
        if selected_game.get() == "原神" and file.startswith("GenshinImpact"):
            account_options.append(file[start_index + 1:end_index])
        elif selected_game.get() == "崩鐵" and file.startswith("Honkai_StarRail"):
            account_options.append(file[start_index + 1:end_index])
        elif selected_game.get() == "絕區零" and file.startswith("ZenlessZoneZero"):
            account_options.append(file[start_index + 1:end_index])
    return account_options

selected_account = ctk.StringVar(value=get_options()[0]) if get_options() else ctk.StringVar()

def add_line_spacing(text, width, line_spacing=1):
    wrapped_lines = textwrap.wrap(text, width=width)
    spaced_text = ("\n" * line_spacing).join(wrapped_lines)
    return spaced_text

def fetch_data_in_thread():
    def thread_target():
        try:
            game = selected_game.get()
            if game == "原神":
                message_label.configure(text="正在讀取原神歷史紀錄，請稍等...")
                functions.get_GSdata_by_api()
            elif game == "崩鐵":
                message_label.configure(text="正在讀取崩鐵歷史紀錄，請稍等...")
                functions.get_HSRdata_by_api()
            elif game == "絕區零":
                message_label.configure(text="正在讀取絕區零歷史紀錄，請稍等...")
                functions.get_ZZZdata_by_api()

            message_label.configure(text="抽卡紀錄已讀取")
        except Exception as e:
            messagebox.showerror("Error", f"無法讀取歷史紀錄，請先在遊戲裡開啟")
            print(e)

    threading.Thread(target=thread_target).start()
    show_game_options(selected_game.get())

def handle_dropdown_selection(selection):
    if "手動輸入" in selection:
        show_entry()
        
    elif "導入 JSON" in selection:
        import_json()

def show_entry():
    input_frame.pack(fill="both", expand=True, padx=10, pady=10)

    for widget in input_frame.winfo_children():
        widget.destroy()

    # 創建框架來包含 Radio Button 和文本框
    entry_frame = ctk.CTkFrame(input_frame)
    entry_frame.pack(fill="both", expand=True, padx=5, pady=5)

    # 左側 Radio Button 框架
    radio_frame = ctk.CTkFrame(entry_frame)
    radio_frame.pack(side="left", fill="y", padx=5, pady=5)

    ctk.CTkRadioButton(radio_frame, text="角色", variable=selected_category, value="角色").pack(anchor="w", pady=5)
    ctk.CTkRadioButton(radio_frame, text="武器", variable=selected_category, value="武器").pack(anchor="w", pady=5)

    # 右側文本框
    text_box = ctk.CTkTextbox(entry_frame, height=300)
    text_box.pack(side="right", fill="both", expand=True, padx=5, pady=5)

    # 添加開始計算按鈕到 radio_frame
    start_button = ctk.CTkButton(radio_frame, text="開始計算", command=lambda: caculate_average_manual(text_box))
    start_button.pack(anchor="center", pady=10)

def caculate_average_manual(text_box):
    result = functions.get_average("", selected_game.get(), text_box.get("1.0", "end").strip(), selected_category.get())
    message_label.configure(text=result)

def import_json():
    input_frame.pack(fill="both", expand=True, padx=10, pady=10)

    for widget in input_frame.winfo_children():
        widget.destroy()

    file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
    system_path = (f"{data_path}/user_data/GenshinImpact.json"
                   if selected_game.get() == "原神"
                   else f"{data_path}/user_data/Honkai_StarRail.json"
                   if selected_game.get() == "崩鐵"
                   else f"{data_path}/user_data/ZenlessZoneZero.json")

    if file_path:
        extracted_data = functions.extract_data(selected_game.get(), file_path)

        if extracted_data == "錯誤的遊戲資料":
            messagebox.showerror("錯誤", "導入錯誤或無法解析的資料")
            return

        account = extracted_data['info']['uid']
        system_path = system_path[:-5] + f"_{account}.json"

        if os.path.exists(system_path):
            extracted_data = functions.compare_input_data(system_path, extracted_data, selected_game.get())

        with open(system_path, "w", encoding="utf8") as file:
            json.dump(extracted_data, file, indent=4, ensure_ascii=False)

        selected_account.set(account)

        root.after(0, show_game_options, selected_game.get())
        root.after(0, show_record_options)

def export_to_folder():
    """讓用戶選擇資料夾並輸出檔案。"""
    folder_path = filedialog.askdirectory()  # 開啟選擇資料夾對話框
    if folder_path:
        try:
            # 載入當前帳號的資料
            accountID = selected_account.get()

            if selected_game.get() == "原神":
                file_path = f"{data_path}/user_data/GenshinImpact_{accountID}.json"
                export_file_name = f"GenshinImpact_{accountID}_export.json"

            elif selected_game.get() == "崩鐵":
                file_path = f"{data_path}/user_data/Honkai_StarRail_{accountID}.json"
                export_file_name = f"Honkai_StarRail_{accountID}_export.json"

            elif selected_game.get() == "絕區零":
                file_path = f"{data_path}/user_data/ZenlessZoneZero_{accountID}.json"
                export_file_name = f"ZenlessZoneZero_{accountID}_export.json"

            # 確保來源檔案存在
            if not os.path.exists(file_path):
                messagebox.showerror("錯誤", "無法找到要導出的檔案！")
                return

            export_path = os.path.join(folder_path, export_file_name)
            functions.export_json(file_path, export_path, selected_game.get())

            messagebox.showinfo("成功", f"檔案已成功輸出至：\n{export_path}")

        except Exception as e:
            messagebox.showerror("錯誤", f"檔案輸出失敗：{e}")


def show_game_options(selected_game):
    # 清空先前的內容
    for widget in game_frame.winfo_children():
        widget.destroy()

    options = []
    colors = ["#F0F8FF", "#FFE4B5", "#E0FFFF", "#FFFACD", "#F5F5DC"]  # 柔和顏色
    accountID = selected_account.get() if selected_account != "" else ""

    # 根據遊戲選擇設定選項和資料檔案
    if selected_game == "原神":
        options = ["資訊", "新手", "常駐", "角色", "武器", "集錄"]
        path = f"{data_path}/user_data/GenshinImpact_{accountID}.json"
    elif selected_game == "崩鐵":
        options = ["資訊", "新手", "常駐", "角色", "光錐"]
        path = f"{data_path}/user_data/Honkai_StarRail_{accountID}.json"
    elif selected_game == "絕區零":
        options = ["資訊", "常駐", "代理人", "音擎", "邦布"]
        path = f"{data_path}/user_data/ZenlessZoneZero_{accountID}.json"

    # 創建選項框架
    option_frame = ctk.CTkScrollableFrame(game_frame, height=400)  # 使用可滾動框架
    option_frame.pack(pady=10, fill="both", expand=True)

    # 創建按鈕框架
    button_frame = ctk.CTkFrame(game_frame)
    button_frame.pack(side="bottom", pady=10)

    ctk.CTkButton(button_frame, text="讀取抽卡紀錄", command=fetch_data_in_thread).pack(side="left", padx=5)
    selected_option = ctk.StringVar(value="外部資料源")
    dropdown = ctk.CTkOptionMenu(button_frame, variable=selected_option,
                                 values=["手動輸入(不會儲存資料)", "導入 JSON(會儲存資料)"],
                                 command=handle_dropdown_selection)
    dropdown.pack(side="left", padx=5)

    if os.path.exists(path):
        export_button = ctk.CTkButton(button_frame, text="導出Json", command=export_to_folder)
        export_button.pack(side="left", padx=5)

    # 如果資料檔案存在，讀取資料
    if os.path.exists(path):
        with open(path, "r", encoding="utf8") as file:
            data = json.load(file)

        for i, option in enumerate(options):
            if option == "資訊":
                continue

            counter = 0
            text = ""
            keys = list(data.keys())

            label_frame = ctk.CTkFrame(option_frame, fg_color=colors[i % len(colors)])
            label_frame.pack(fill="x", padx=5, pady=5)

            ctk.CTkLabel(label_frame, text=option, font=("Arial", 16), text_color="black", anchor="w").pack(fill="x", pady=2)

            if keys[i] == "info":
                continue

            reversed_data = data[keys[i]][::-1]
            if reversed_data == []:
                continue

            for items in reversed_data:
                counter += 1
                if selected_game != "絕區零" and items['rank_type'] == '5':
                    text += f"{items['name']} [{counter}] "
                    counter = 0
                elif selected_game == "絕區零" and items['rank_type'] == "4":
                    text += f"{items['name']} [{counter}] "
                    counter = 0

            result = add_line_spacing(text, width=300, line_spacing=2)  # 調整寬度
            ctk.CTkLabel(label_frame, text=result, font=("Arial", 20), justify="left", wraplength=500, text_color="black").pack(fill="x", pady=2)

        input_data = functions.get_average(path, selected_game, "", selected_category.get())
        message_label.configure(text=input_data)
    else:
        message_label.configure(text="")

    message_label.pack(anchor="center", pady=5)



# Core GUI sections
def show_record_options():
    # Clear frames
    for widget in option_frame.winfo_children():
        widget.destroy()
    for widget in game_frame.winfo_children():
        widget.destroy()

    # Game selection
    ctk.CTkLabel(option_frame, text="選擇遊戲:").pack(anchor="w", pady=5)
    game_selection = ctk.CTkFrame(option_frame)
    game_selection.pack(anchor="w", padx=10)
    ctk.CTkRadioButton(game_selection, text="原神", variable=selected_game, value="原神", command=show_record_options).pack(anchor="w")
    ctk.CTkRadioButton(game_selection, text="崩鐵", variable=selected_game, value="崩鐵", command=show_record_options).pack(anchor="w")
    ctk.CTkRadioButton(game_selection, text="絕區零", variable=selected_game, value="絕區零", command=show_record_options).pack(anchor="w")

    # Account selection
    ctk.CTkLabel(option_frame, text="選擇帳號:").pack(anchor="w", padx=10, pady=5)
    account_options = get_options()
    if account_options:
        if selected_account.get() not in account_options:
            selected_account.set(account_options[0])
        account_menu = ctk.CTkOptionMenu(option_frame, variable=selected_account, values=account_options, command=change_account)
        account_menu.pack(anchor="w", padx=10)

    message_label.pack(anchor="center", pady=10)
    show_game_options(selected_game.get())

# Set up main frames
option_frame = ctk.CTkFrame(root, width=300)
option_frame.pack(side="left", fill="y", padx=10, pady=10)

game_frame = ctk.CTkFrame(root)
game_frame.pack(fill="both", expand=True, padx=10, pady=10)

message_label = ctk.CTkLabel(root, text="", font=("Arial", 14))

# Menu bar buttons
button_frame = ctk.CTkFrame(root)
button_frame.pack(side="bottom", pady=10)
ctk.CTkButton(button_frame, text="抽卡紀錄", command=show_record_options).pack(side="left", padx=10)
ctk.CTkButton(button_frame, text="HOYO工具箱", command=lambda: start_pyqt5_app(selected_game.get())).pack(side="left", padx=10)
ctk.CTkButton(button_frame, text="遊戲功能", command=lambda: messagebox.showinfo("提示", "遊戲功能尚未實現")).pack(side="left", padx=10)

# Run the app
root.mainloop()
