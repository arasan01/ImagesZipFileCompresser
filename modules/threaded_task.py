from modules.application import Application
import threading

import queue
import subprocess
import shutil
import glob
import os


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
