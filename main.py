from datetime import datetime
import threading
import json
import os
import shutil
import sys
import hashlib
from urllib.parse import quote

import pysvn
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (QApplication, QTableWidget, QTableWidgetItem,
                               QWidget)


__path__ = os.path.dirname(os.path.realpath(__file__))

client = pysvn.Client()
# changes = client.status
# for change in changes:
#     print(change,change.text_status)


class Setting(object):

    class Data():
        username = None
        password = None
        workdir = None

    class TableMap():
        trunk = 0
        trunk_status = 1
        file_name = 2
        target = 3
        target_status = 4
        sync_status = 5
        log = 6

    def __init__(self):
        super(Setting, self).__init__()
        with open("setting\setting.json", "r", encoding="utf-8") as f:
            settingfile = json.load(f)
        self.Data.username = settingfile["UserName"]
        self.Data.password = settingfile["Password"]
        self.Data.workdir = settingfile["WorkDir"]


class WindowData(object):
    main = None


class WindowModule(object):
    class Main(QWidget):
        def __init__(self, parent=None):
            super(WindowModule.Main, self).__init__(parent)
            self.ui = None
            self.build_ui()  # 初始化UI
            self.set_style()

        def build_ui(self):
            ui = "%s/ui/main_window.ui" % __path__
            self.ui = QUiLoader().load(ui, parentWidget=None)

        def set_style(self):
            tab_map = Setting.TableMap
            self.ui.changeList.setColumnWidth(tab_map.file_name, 150)
            self.ui.changeList.setColumnWidth(tab_map.trunk, 200)
            self.ui.changeList.setColumnWidth(tab_map.target, 200)
            self.ui.changeList.setColumnWidth(tab_map.sync_status, 150)
            self.ui.changeList.setColumnWidth(tab_map.log, 400)


class WindowController(object):
    class Main(object):
        def __init__(self):
            ctr = WindowController.Main
            ui = WindowData.main.ui
            ui.findChanges.clicked.connect(ctr.on_findChanges_clicked)
            ui.syncBtn.clicked.connect(ctr.on_syncBtn_clicked)
            ui.compareCheck.stateChanged.connect(
                ctr.on_compareCheck_stateChanged)
            ui.commitBtn.clicked.connect(ctr.on_commitBtn_clicked)

        @staticmethod
        def on_findChanges_clicked():
            ui = WindowData.main.ui
            changelist: QTableWidget = ui.changeList
            # 清空rows
            changelist.setRowCount(0)
            changelist.setRowCount(1)
            empitem = QTableWidgetItem("——————未发现任何修改")
            changelist.setItem(0, 0, empitem)
            # 获取更改
            changes = ScriptManager.find_changes()
            ScriptManager.list_all_changes(changes)

        @staticmethod
        def on_syncBtn_clicked():
            ScriptManager.sync_changes()
            changes = ScriptManager.find_changes()
            ScriptManager.list_all_changes(changes)

        @staticmethod
        def on_compareCheck_stateChanged():
            ui = WindowData.main.ui
            ui.changeList.setRowCount(0)
            changes = ScriptManager.find_changes()
            ScriptManager.list_all_changes(changes)
            
        @staticmethod
        def on_commitBtn_clicked():
            ui = WindowData.main.ui
            tab_map = Setting.TableMap
            tab_list: QTableWidget =ui.changeList
            
            changed_files = ""
            
            rows = tab_list.rowCount()
            for row in range(0,rows):
                file_name_item = tab_list.item(row,tab_map.file_name)
                file_name = file_name_item.text()
                trunk = tab_list.item(row,tab_map.trunk).text()
                target = tab_list.item(row,tab_map.target).text()
                if file_name_item.checkState() != Qt.Checked:
                    continue
                trunk_file = trunk+"\\"+file_name
                target_file = target+"\\"+file_name
                if " " in trunk_file:
                    trunk_file = trunk
                if " " in target_file:
                    target_file = target
                if changed_files != "":
                    changed_files += "*"
                changed_files += trunk_file
                if changed_files != "":
                    changed_files += "*"
                changed_files += target_file
                
            t1 = SvnPro(trunk)
            t2 = SvnPro(target)
            t1.start()
            t2.start()


class WindowFunctions(object):

    @staticmethod
    def refresh_table():
        changes = ScriptManager.find_changes()
        ScriptManager.list_all_changes(changes)


class ScriptManager():

    @staticmethod
    def list_all_changes(changes):
        ui = WindowData.main.ui
        changelist: QTableWidget = ui.changeList

        r = 0
        for file_name, file_props in changes.items():
            trunk = file_props["trunk"]
            trunk_status = file_props["trunk_status"]
            target = file_props["target"]
            target_status = file_props["target_status"]
            sync_status = file_props["sync_status"]
            log = file_props["log"]
            # print(file_name, file_props)

            # get color
            trunk_brush = ScriptManager.get_change_color(trunk_status)
            target_brush = ScriptManager.get_change_color(target_status)

            # changed file's name
            iname = QTableWidgetItem()
            iname.setText(file_name)
            iname.setCheckState(Qt.Checked)
            iname.setForeground(trunk_brush)

            # changed item's path
            itrunk = QTableWidgetItem()
            itrunk.setText(trunk)
            itrunk.setForeground(trunk_brush)

            # changed item's type
            istatus = QTableWidgetItem()
            istatus.setText(trunk_status)
            istatus.setForeground(trunk_brush)

            # changed item's target
            itarget = QTableWidgetItem()
            itarget.setText(target)
            itarget.setForeground(target_brush)

            # target status of changed item
            itarget_status = QTableWidgetItem()
            itarget_status.setText(target_status)
            itarget_status.setForeground(target_brush)

            # sync status of changed item
            isync = QTableWidgetItem()
            isync.setText(sync_status)
            isync.setForeground(target_brush)

            # target logs
            itarget_log = QTableWidgetItem()
            itarget_log.setText(log)
            itarget_log.setForeground(target_brush)

            # write changeList
            tab_map = Setting.TableMap
            changelist.setRowCount(r+1)
            changelist.setItem(r, tab_map.trunk, itrunk)
            changelist.setItem(r, tab_map.trunk_status, istatus)
            changelist.setItem(r, tab_map.file_name, iname)
            changelist.setItem(r, tab_map.target, itarget)
            changelist.setItem(r, tab_map.target_status, itarget_status)
            changelist.setItem(r, tab_map.sync_status, isync)
            changelist.setItem(r, tab_map.log, itarget_log)
            r += 1

    @staticmethod
    def find_changes():
        ui = WindowData.main.ui
        workdir: dict = Setting.Data.workdir
        changes = {}

        client = pysvn.Client()
        status_parser = ScriptManager.status_parser
        md5 = ScriptManager.get_file_md5

        for trunk_dir, target_dir in workdir.items():

            trunk_dir = trunk_dir.replace("/", "\\")
            target_dir = target_dir.replace("/", "\\")

            trunk_status: list = client.status(trunk_dir)

            for status in trunk_status:

                # 工作文件
                file_path_trunk: str = status.path
                file_status_trunk = status_parser(file_path_trunk)
                file_path_target: str = file_path_trunk.replace(
                    trunk_dir, target_dir)
                file_status_target = status_parser(file_path_target)
                file_name = file_path_trunk.replace(trunk_dir+"\\", "")
                sync_status = "未同步"
                log_content = ""

                # print(file_path_target)
                # print(file_status_target)

                if not ui.compareCheck.isChecked():
                    if file_status_trunk == "正常":
                        continue

                # brach中不存在的，无论trunk的status情况如何都要加入列表
                # brach中存在的，对比两方信息，决定是否加入列表
                if file_status_target != "不存在":
                    # 目录类
                    if os.path.isdir(file_path_trunk):
                        # 如果目标版本管理状态是正常，就不用管了
                        if file_status_trunk == "正常" and file_status_target == "正常":
                            continue
                        # 名称（如果名称为空，说明其是工作路径本身）
                        file_name = file_path_trunk.replace(trunk_dir+"\\", "")
                        if file_name == "":
                            file_name = "工作路径"
                            
                        sync_status = "已同步"
                    # 文件类
                    else:
                        # 对比MD5
                        file_md5 = md5(file_path_trunk)
                        target_md5 = md5(file_path_target)
                        # 如果MD5码一样
                        if file_md5 == target_md5:
                            # 如果文件已正常处于版本控制中，则不再做处理
                            if file_status_trunk == "正常" and file_status_target == "正常":
                                continue
                            # 如果文件有任意一方发生改动
                            sync_status = "已同步"
                        else:
                            if file_status_target == "正常" or file_status_target == "不存在":
                                sync_status = "未同步"
                            else:
                                sync_status = "未同步，且目标本地有变动"

                        # target log
                        # print(file_path_target,file_status_target)
                        if file_status_target not in ["已增加","无版本控制", "已忽略", "未分类", "不存在"]:
                            target_log = client.log(file_path_target, limit=1)
                            author = target_log[0]["author"]
                            last_time = target_log[0]["date"]
                            last_time = datetime.fromtimestamp(
                                last_time).strftime("%Y-%m-%d %H:%M:%S")
                            log_message = target_log[0]["message"]
                            log_content = f"{last_time}由{author}：{log_message}"

                # Write data
                file_prop = {}
                file_prop["trunk"] = trunk_dir
                file_prop["trunk_status"] = file_status_trunk
                file_prop["target"] = target_dir
                file_prop["target_status"] = file_status_target
                file_prop["sync_status"] = sync_status
                file_prop["log"] = log_content

                changes[file_name] = file_prop

                # 是没有加入版本控制的目录吗？
                if file_status_trunk == "无版本控制" and os.path.isdir(file_path_trunk):
                    # print(file_path_trunk)
                    for root, dirs, files in os.walk(file_path_trunk):
                        for dir in dirs:
                            file_name = os.path.join(
                                root, dir).replace(trunk_dir+"\\", "")
                            file_prop = {}
                            file_prop["trunk"] = trunk_dir
                            file_prop["trunk_status"] = file_status_trunk
                            file_prop["target"] = target_dir
                            file_prop["target_status"] = status_parser(
                                target_dir+"\\"+file_name)
                            if os.path.exists(target_dir+file_name):
                                sync_status = "已同步"
                            file_prop["sync_status"] = sync_status
                            file_prop["log"] = log_content

                            changes[file_name] = file_prop
                        for file in files:
                            file_name = os.path.join(
                                root, file).replace(trunk_dir+"\\", "")
                            file_prop = {}
                            file_prop["trunk"] = trunk_dir
                            file_prop["trunk_status"] = file_status_trunk
                            file_prop["target"] = target_dir
                            file_prop["target_status"] = status_parser(
                                target_dir+"\\"+file_name)
                            if os.path.exists(target_dir+file_name):
                                sync_status = "已同步"
                            file_prop["sync_status"] = sync_status
                            file_prop["log"] = log_content

                            changes[file_name] = file_prop

        return changes

    @staticmethod
    def status_parser(file_path):
        if not os.path.exists(file_path):
            return "不存在"

        pywc = pysvn.wc_status_kind
        status_parser = pysvn.Client().status

        try:
            status = status_parser(file_path)
        except:
            return "无版本控制"

        text_status = status[0].text_status

        if text_status == pywc.modified:
            return "修改"
        elif text_status == pywc.normal:
            return "正常"
        elif text_status == pywc.unversioned:
            return "无版本控制"
        elif text_status == pywc.missing:
            return "缺少"
        elif text_status == pywc.added:
            return "已增加"
        elif text_status == pywc.deleted:
            return "删除"
        elif text_status == pywc.ignored:
            return "已忽略"
        else:
            return "未分类"

    @staticmethod
    def get_file_md5(file_path):
        if not os.path.exists(file_path):
            return
        if os.path.isdir(file_path):
            return
        f = open(file_path, 'rb')
        md5_obj = hashlib.md5()
        while True:
            d = f.read(8096)
            if not d:
                break
            md5_obj.update(d)
        hash_code = md5_obj.hexdigest()
        f.close()
        md5 = str(hash_code).lower()
        return md5

    @staticmethod
    def get_change_color(change_type):
        if change_type == "修改":
            color = QColor(0, 50, 160)
        elif change_type == "无版本控制":
            color = QColor(0, 0, 0)
        elif change_type == "缺少":
            color = QColor(100, 50, 100)
        elif change_type == "已增加":
            color = QColor(100, 0, 100)
        elif change_type == "删除":
            color = QColor(100, 0, 0)
        elif change_type == "已忽略":
            color = QColor(0, 0, 0)
        elif change_type == "不存在":
            color = QColor(200, 200, 200)
        else:
            color = QColor(0, 0, 0)
        brush = QBrush(color)
        return brush

    @staticmethod
    def sync_changes():
        tab_map = Setting.TableMap
        ui = WindowData.main.ui
        tablist: QTableWidget = ui.changeList

        all_row = tablist.rowCount()

        # changed_files = ""

        for row in range(0, all_row):
            file_name = tablist.item(row, tab_map.file_name)
            trunk_path = tablist.item(row, tab_map.trunk)
            trunk_type = tablist.item(row, tab_map.trunk_status)
            target_path = tablist.item(row, tab_map.target)
            target_type = tablist.item(row, tab_map.target_status)

            if file_name.checkState() != Qt.Checked:
                continue

            if "." in file_name.text():
                act_file_name = file_name.text()
            else:
                act_file_name = file_name.text().lstrip("\\")

            file_path_trunk = trunk_path.text()+"\\"+act_file_name
            # changed_files += "*"+file_path_trunk

            file_path_target = target_path.text()+"\\"+act_file_name
            # changed_files += "*"+file_path_target

            # it's dir
            if os.path.isdir(file_path_trunk):
                if target_type.text() in ["不存在", "缺少", "删除"]:
                    os.makedirs(file_path_target)
            else:
                if trunk_type.text() in ["缺少", "删除"]:
                    if os.path.exists(file_path_target):
                        if os.path.isfile(file_path_target):
                            os.remove(file_path_target)
                        elif os.path.isdir(file_path_target):
                            os.rmdir(file_path_target)
                # elif trunk_type.text() in ["修改", "无版本控制", "已增加"]:
                #     shutil.copy(file_path_trunk, file_path_target)
                else:
                    shutil.copy(file_path_trunk, file_path_target)

        # return changed_files
        # t = SvnPro(changed_files)
        # t.start()


class SvnPro(threading.Thread):
    def __init__(self, work_path):
        super().__init__()
        self.work_path = work_path

    def run(self):
        os.system(
            f'"TortoiseProc" /command:commit /path:{self.work_path} /closeonend:3')


def create_window():

    app = QApplication(sys.argv)
    WindowData.main = WindowModule.Main()
    WindowController.Main()
    WindowData.main.ui.show()
    changes = ScriptManager.find_changes()
    ScriptManager.list_all_changes(changes)
    sys.exit(app.exec())


if __name__ == "__main__":
    Setting()
    create_window()
