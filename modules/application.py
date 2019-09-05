from tkinter import ttk
try:
    import tkinter as tk
except ImportError:
    import Tkinter as tk
import tkinter.filedialog
import threading
import queue

from modules.threaded_task import ThreadedTask


class Application(tk.Frame):

    paths = []
    thread_lock = threading.Lock()
    thread_counter = 0
    title_label = None
    progress_label = None
    progress = None
    config = None
    isConvert_now = False

    def __init__(self, master=tk.Tk(),config=None):
        super().__init__(master)
        self.master = master
        self.master.title("ZIP圧縮")
        self.master.geometry("600x400")
        self.pack()
        self.delete_log = []
        self.create_widgets()
        Application.config = config

    def __call__(self, jd):
        self.mainloop()

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
