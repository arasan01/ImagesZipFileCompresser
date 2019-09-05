from tkinter import ttk
try:
    import tkinter as tk
except ImportError:
    import Tkinter as tk
import tkinter.filedialog
import sys
import json
import queue
import threading
import subprocess
import shutil
import glob
import os
from pprint import pprint


class Application(tk.Frame):

    paths = []
    thread_lock = threading.Lock()
    thread_counter = 0
    title_label = None
    progress_label = None
    progress = None
    config = None
    isConvert_now = False

    def __init__(self, master=None, config=None):
        super().__init__(master)
        self.master = master
        self.pack()
        self.delete_log = []
        self.create_widgets()
        Application.config = config

    def create_widgets(self):
        # ペインウィンドウ
        # PanedWindow
        # orient : 配置（vertical or horizontal）
        # bg : 枠線の色
        # pack
        # expand ：可変（True or False(固定)
        # fill : スペースが空いている場合の動き（tk.BOTH　縦横に広がる）
        # side ：　配置する際にどの方向からつめていくか（side or top ・・・）
        pw_main = tk.PanedWindow(self.master, orient='vertical')
        pw_main.pack(expand=True, fill=tk.BOTH, side="left")

        # ツールボタン領域とアイテムリスト領域を定義
        pw_buttons = tk.PanedWindow(pw_main, orient='horizontal')
        pw_main.add(pw_buttons)

        pw_lists = tk.PanedWindow(pw_main, orient='vertical')
        pw_main.add(pw_lists)

        pw_progress = tk.PanedWindow(pw_main, orient='horizontal')
        pw_main.add(pw_progress)

        Application.progress = tk.ttk.Progressbar(
            pw_progress, orient="horizontal", length=100)
        Application.progress.pack(side="left")
        Application.progress_label = tk.Label(pw_progress, text="")
        Application.progress_label.pack(side="left")
        Application.title_label = tk.Label(pw_progress, text="処理中ファイルの名前")
        Application.title_label.pack(side="left")

        # ツールボタン領域のボタンを定義
        btn_size = {
            "width": 15,
            "height": 3
        }
        btn_select = tk.Button(
            pw_buttons, text="選択", command=lambda: self.select_item(lb) if not Application.isConvert_now else None, **btn_size)
        btn_select.grid(row=0, column=0)
        btn_delete = tk.Button(
            pw_buttons, text="削除", command=lambda: self.delete_item(lb) if not Application.isConvert_now else None, **btn_size)
        btn_delete.grid(row=0, column=1)
        btn_undo = tk.Button(
            pw_buttons, text="復元", command=lambda: self.undo_item(lb) if not Application.isConvert_now else None, **btn_size)
        btn_undo.grid(row=0, column=2)
        btn_convert = tk.Button(
            pw_buttons, text="変換", command=lambda: self.convert(lb) if not Application.isConvert_now else None, **btn_size)
        btn_convert.grid(row=0, column=3)
        btn_cancel = tk.Button(
            pw_buttons, text="中止", command=lambda: self.cancel(), **btn_size)
        btn_cancel.grid(row=0, column=4)

        # アイテムリスト領域のあれこれを定義
        lb = tk.Listbox(pw_lists, selectmode="single", width=90, height=19)
        lb.grid(row=0, column=0, sticky=tk.W+tk.E)
        sb = tk.Scrollbar(pw_lists, command=lb.yview)
        sb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        lb.configure(yscrollcommand=sb.set)

    def select_item(self, lb):
        fileType = [("", "*.zip")]
        files = tk.filedialog.askopenfilenames(filetypes=fileType)
        for x in list(files):
            lb.insert('end', x)

    def delete_item(self, lb):
        xs = lb.curselection()
        if len(xs) != 0:
            self.delete_log.append((xs[0], lb.get(xs[0])))
            lb.delete(xs[0])

    def undo_item(self, lb):
        if len(self.delete_log) != 0:
            index, element = self.delete_log.pop()
            lb.insert(index, element)

    def convert(self, lb):
        Application.paths = list(reversed(lb.get(0, tk.END)))
        self.paths_len = len(Application.paths)
        if self.paths_len:
            Application.thread_counter = 0
            Application.isConvert_now = True
            self.queue = queue.Queue()
            for _ in range(self.paths_len):
                ThreadedTask(self.queue).start()
            self.master.after(100, self.process_queue)

    def process_queue(self):
        try:
            if self.queue.qsize() != self.paths_len:
                self.master.after(100, self.process_queue)
            # Show result of the task if needed
            else:
                msg = self.queue.get(0)
                Application.title_label["text"] = "終了しました"
                Application.isConvert_now = False
        except queue.Empty:
            self.master.after(100, self.process_queue)

    def cancel(self):
        Application.isConvert_now = False


class ThreadedTask(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.deamon = True
        self.queue = queue

    def run(self):
        if not Application.isConvert_now:
            self.queue.put("cancel")
            return
        Application.thread_lock.acquire()
        path = Application.paths[Application.thread_counter]

        Application.progress_label[
            'text'] = f"{Application.thread_counter+1} / {len(Application.paths)} : "
        Application.title_label[
            'text'] = path
        archiver = Application.config["pathConfig"]["archivePath"]
        tempDir = Application.config["pathConfig"]["temporaryDirectory"]
        if os.path.exists(tempDir):
            shutil.rmtree(tempDir)

        if not Application.isConvert_now:
            Application.thread_lock.release()
            self.queue.put("cancel")
            return

        # ファイル展開
        Application.progress.configure(
            mode='indeterminate', value=0, maximum=100)
        Application.progress.start(interval=25)

        subprocess.run([archiver, 'x', path,
                        "-o"+tempDir], shell=True)
        count = 0
        for dirpath, dirnames, filenames in os.walk(tempDir):
            for filename in filenames:
                try:
                    os.rename(os.path.join(dirpath, filename),
                              os.path.join(tempDir, str(count) + filename))
                except OSError:
                    print("Could not move %s " %
                          os.path.join(dirpath, filename))
            count += 1

        Application.progress.stop()

        if not Application.isConvert_now:
            Application.thread_lock.release()
            self.queue.put("cancel")
            return

        # 画像圧縮
        converter = Application.config["pathConfig"]["convertPath"]
        imW = str(Application.config["mainConfig"]["Width"])
        imH = str(Application.config["mainConfig"]["Height"])
        imQuality = str(Application.config["advancedConfig"]["imageQuality"])
        files = list(glob.glob(tempDir + "/*.*"))
        file_num = len(files)
        Application.progress.configure(
            mode='determinate', value=0, maximum=file_num)

        for i, f in enumerate(files):
            if not Application.isConvert_now:
                break
            Application.progress.configure(value=i+1)
            Application.progress.update()
            fnew = f[:-4] + "_n" + f[-4:]
            subprocess.run([
                converter,
                "-define", "jpeg:size=" + imW + "+" + imH,
                "-resize", imW + "x" + imH,
                "-quality", imQuality,
                f,
                fnew], shell=True)
            os.remove(f)

        if not Application.isConvert_now:
            Application.thread_lock.release()
            self.queue.put("cancel")
            return

        # アーカイブ
        cl = str(Application.config["advancedConfig"]["compressLevel"])
        Application.progress.configure(
            mode='indeterminate', value=0, maximum=100)
        Application.progress.start(interval=25)
        pathnew = path[:-4] + "_new.zip"

        query = [archiver, 'a', pathnew, "-mmt=on",
                 "-mx="+cl, tempDir]
        subprocess.run(query, shell=True)

        Application.progress.stop()
        Application.progress.value = 0

        # 終了処理
        shutil.rmtree(tempDir)

        isDelete = Application.config["advancedConfig"]["purgeOriginal"]
        if isDelete:
            os.remove(path)
            os.rename(pathnew, path)
        self.queue.put("Finished")
        Application.thread_counter += 1
        Application.thread_lock.release()


with open("config/config.json", "r") as f:
    jd = json.load(f)
pprint(jd)
root = tk.Tk()
myapp = Application(master=root, config=jd)
myapp.master.title("ZIP圧縮")  # タイトル
myapp.master.geometry("600x400")  # ウィンドウの幅と高さピクセル単位で指定（width x height）

myapp.mainloop()
