import sys
import time
import threading
import re
import json
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                               QMessageBox, QListWidget, QListWidgetItem, QLineEdit,
                               QGroupBox, QComboBox, QSpinBox, QDialog, QDialogButtonBox,
                               QTreeWidget, QTreeWidgetItem, QAbstractItemView, QSplitter,
                               QFrame, QStyleFactory, QScrollArea)
from PySide6.QtCore import Qt, QMimeData, QTimer, Signal, QEvent
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QColor, QFont, QPalette
import keyboard  # 用于全局热键监听

class ActionBlock:
    """动作块类"""
    def __init__(self, action_type, params=None):
        self.action_type = action_type
        self.params = params or {}
    
    def execute(self):
        """执行动作"""
        if self.action_type == "text":
            keyboard.write(self.params.get("text", ""))
        elif self.action_type == "key":
            key = self.params.get("key", "enter")
            keyboard.press_and_release(key)
        elif self.action_type == "wait":
            time.sleep(self.params.get("duration", 1))
        elif self.action_type == "focus":
            # 模拟点击指定位置（需要提前设置）
            pass
    
    def to_dict(self):
        """转换为字典"""
        return {
            "type": self.action_type,
            "params": self.params
        }
    
    @staticmethod
    def from_dict(data):
        """从字典创建"""
        return ActionBlock(data["type"], data.get("params", {}))

class ActionEditor(QDialog):
    """动作编辑器对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("动作编辑器")
        self.setGeometry(200, 200, 600, 400)
        
        self.actions = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 可用动作列表
        available_group = QGroupBox("可用动作")
        available_layout = QVBoxLayout(available_group)
        
        self.available_list = QTreeWidget()
        self.available_list.setHeaderLabel("动作类型")
        self.available_list.setDragEnabled(True)
        self.available_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.available_list.setStyleSheet("""
            QTreeWidget::item {
                border: 1px solid gray;
                margin: 2px;
                padding: 5px;
                background-color: #f0f0f0;
            }
            QTreeWidget::item:selected {
                background-color: #a0a0ff;
            }
        """)
        
        # 添加可用动作类型
        text_item = QTreeWidgetItem(self.available_list, ["输入文本"])
        text_item.setData(0, Qt.UserRole, "text")
        text_item.setFlags(text_item.flags() | Qt.ItemIsDragEnabled)
        
        key_item = QTreeWidgetItem(self.available_list, ["按键"])
        key_item.setData(0, Qt.UserRole, "key")
        key_item.setFlags(key_item.flags() | Qt.ItemIsDragEnabled)
        
        wait_item = QTreeWidgetItem(self.available_list, ["等待"])
        wait_item.setData(0, Qt.UserRole, "wait")
        wait_item.setFlags(wait_item.flags() | Qt.ItemIsDragEnabled)
        
        self.available_list.expandAll()
        available_layout.addWidget(self.available_list)
        
        # 当前动作序列
        sequence_group = QGroupBox("动作序列")
        sequence_layout = QVBoxLayout(sequence_group)
        
        self.sequence_list = QTreeWidget()
        self.sequence_list.setHeaderLabels(["动作", "参数"])
        self.sequence_list.setAcceptDrops(True)
        self.sequence_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.sequence_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.sequence_list.setStyleSheet("""
            QTreeWidget::item {
                border: 1px solid gray;
                margin: 2px;
                padding: 5px;
                background-color: #f8f8f8;
            }
            QTreeWidget::item:selected {
                background-color: #a0a0ff;
            }
        """)
        self.sequence_list.itemDoubleClicked.connect(self.edit_action)
        
        sequence_layout.addWidget(self.sequence_list)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        self.edit_button = QPushButton("编辑")
        self.edit_button.clicked.connect(self.edit_action)
        self.remove_button = QPushButton("删除")
        self.remove_button.clicked.connect(self.remove_action)
        self.clear_button = QPushButton("清空")
        self.clear_button.clicked.connect(self.clear_actions)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        
        sequence_layout.addLayout(button_layout)
        
        # 使用分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(available_group)
        splitter.addWidget(sequence_group)
        splitter.setSizes([200, 400])
        layout.addWidget(splitter)
        
        # 对话框按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # 设置拖拽
        self.setup_drag_drop()
    
    def setup_drag_drop(self):
        """设置拖拽功能"""
        self.available_list.setDragDropMode(QAbstractItemView.DragOnly)
        self.sequence_list.setDragDropMode(QAbstractItemView.DragDrop)
        self.sequence_list.setDefaultDropAction(Qt.MoveAction)
    
    def edit_action(self):
        """编辑选中的动作"""
        current_item = self.sequence_list.currentItem()
        if not current_item:
            return
        
        action_type = current_item.data(0, Qt.UserRole)
        params = current_item.data(1, Qt.UserRole) or {}
        
        dialog = ActionParamsDialog(action_type, params, self)
        if dialog.exec():
            new_params = dialog.get_params()
            current_item.setData(1, Qt.UserRole, new_params)
            self.update_item_display(current_item, action_type, new_params)
    
    def remove_action(self):
        """删除选中的动作"""
        current_item = self.sequence_list.currentItem()
        if current_item:
            index = self.sequence_list.indexOfTopLevelItem(current_item)
            self.sequence_list.takeTopLevelItem(index)
    
    def clear_actions(self):
        """清空所有动作"""
        self.sequence_list.clear()
    
    def update_item_display(self, item, action_type, params):
        """更新项的显示"""
        if action_type == "text":
            item.setText(0, "输入文本")
            item.setText(1, params.get("text", ""))
        elif action_type == "key":
            item.setText(0, "按键")
            item.setText(1, params.get("key", "enter"))
        elif action_type == "wait":
            item.setText(0, "等待")
            item.setText(1, f"{params.get('duration', 1)}秒")
    
    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.source() == self.available_list:
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """处理拖放事件"""
        if event.source() == self.available_list:
            # 从可用列表拖放到序列列表
            items = self.available_list.selectedItems()
            if items:
                action_type = items[0].data(0, Qt.UserRole)
                self.add_action(action_type)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)
    
    def add_action(self, action_type, params=None):
        """添加新动作"""
        item = QTreeWidgetItem(self.sequence_list)
        item.setData(0, Qt.UserRole, action_type)
        item.setData(1, Qt.UserRole, params or {})
        item.setFlags(item.flags() | Qt.ItemIsDragEnabled)
        self.update_item_display(item, action_type, params or {})
    
    def get_actions(self):
        """获取动作序列"""
        actions = []
        for i in range(self.sequence_list.topLevelItemCount()):
            item = self.sequence_list.topLevelItem(i)
            action_type = item.data(0, Qt.UserRole)
            params = item.data(1, Qt.UserRole) or {}
            actions.append(ActionBlock(action_type, params))
        return actions
    
    def set_actions(self, actions):
        """设置动作序列"""
        self.sequence_list.clear()
        for action in actions:
            self.add_action(action.action_type, action.params)

class ActionParamsDialog(QDialog):
    """动作参数对话框"""
    def __init__(self, action_type, params, parent=None):
        super().__init__(parent)
        self.action_type = action_type
        self.params = params.copy()
        self.capturing_key = False
        
        self.setWindowTitle(f"编辑{action_type}动作参数")
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        if self.action_type == "text":
            self.text_edit = QLineEdit(self.params.get("text", ""))
            layout.addWidget(QLabel("输入文本:"))
            layout.addWidget(self.text_edit)
        elif self.action_type == "key":
            key_layout = QHBoxLayout()
            layout.addWidget(QLabel("按键:"))
            
            self.key_label = QLabel(self.params.get("key", "未设置"))
            self.key_label.setFrameStyle(QFrame.Box)
            self.key_label.setAlignment(Qt.AlignCenter)
            self.key_label.setMinimumHeight(30)
            self.key_label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
            
            self.capture_btn = QPushButton("捕获按键")
            self.capture_btn.clicked.connect(self.start_capture)
            
            key_layout.addWidget(self.key_label)
            key_layout.addWidget(self.capture_btn)
            layout.addLayout(key_layout)
        elif self.action_type == "wait":
            self.wait_spin = QSpinBox()
            self.wait_spin.setRange(1, 60)
            self.wait_spin.setValue(self.params.get("duration", 1))
            self.wait_spin.setSuffix("秒")
            layout.addWidget(QLabel("等待时间:"))
            layout.addWidget(self.wait_spin)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def start_capture(self):
        """开始捕获按键"""
        self.capturing_key = True
        self.key_label.setText("按下任意键...")
        self.key_label.setStyleSheet("border: 2px solid red; background-color: #ffe6e6;")
    
    def keyPressEvent(self, event):
        """按键事件"""
        if self.capturing_key and self.action_type == "key":
            key_name = self.get_key_name(event.key())
            if key_name:
                self.params["key"] = key_name
                self.key_label.setText(key_name)
                self.key_label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
                self.capturing_key = False
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def get_key_name(self, key):
        """获取按键名称"""
        if key >= Qt.Key_A and key <= Qt.Key_Z:
            return chr(key).lower()
        elif key >= Qt.Key_0 and key <= Qt.Key_9:
            return chr(key)
        elif key == Qt.Key_Space:
            return "space"
        elif key == Qt.Key_Enter or key == Qt.Key_Return:
            return "enter"
        elif key == Qt.Key_Tab:
            return "tab"
        elif key == Qt.Key_Escape:
            return "esc"
        elif key == Qt.Key_Backspace:
            return "backspace"
        elif key == Qt.Key_Delete:
            return "delete"
        elif key == Qt.Key_Up:
            return "up"
        elif key == Qt.Key_Down:
            return "down"
        elif key == Qt.Key_Left:
            return "left"
        elif key == Qt.Key_Right:
            return "right"
        elif key == Qt.Key_F1:
            return "f1"
        elif key == Qt.Key_F2:
            return "f2"
        elif key == Qt.Key_F3:
            return "f3"
        elif key == Qt.Key_F4:
            return "f4"
        elif key == Qt.Key_F5:
            return "f5"
        elif key == Qt.Key_F6:
            return "f6"
        elif key == Qt.Key_F7:
            return "f7"
        elif key == Qt.Key_F8:
            return "f8"
        elif key == Qt.Key_F9:
            return "f9"
        elif key == Qt.Key_F10:
            return "f10"
        elif key == Qt.Key_F11:
            return "f11"
        elif key == Qt.Key_F12:
            return "f12"
        return None
    
    def get_params(self):
        """获取参数"""
        if self.action_type == "text":
            return {"text": self.text_edit.text()}
        elif self.action_type == "key":
            return {"key": self.params.get("key", "enter")}
        elif self.action_type == "wait":
            return {"duration": self.wait_spin.value()}
        return {}

class HotkeyCaptureDialog(QDialog):
    """热键捕获对话框"""
    key_captured = Signal(str)
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("请按下您想要设置的快捷键..."))
        
        self.key_label = QLabel("等待按键...")
        self.key_label.setAlignment(Qt.AlignCenter)
        self.key_label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 20px; border: 2px solid gray;")
        layout.addWidget(self.key_label)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def keyPressEvent(self, event):
        """捕获按键事件"""
        key = event.key()
        modifiers = event.modifiers()
        
        # 构建快捷键字符串
        key_str = ""
        if modifiers & Qt.ControlModifier:
            key_str += "ctrl+"
        if modifiers & Qt.AltModifier:
            key_str += "alt+"
        if modifiers & Qt.ShiftModifier:
            key_str += "shift+"
        
        # 获取按键名称
        key_name = self.get_key_name(key)
        if key_name:
            key_str += key_name
            self.key_label.setText(key_str)
            self.key_captured.emit(key_str)
            self.accept()
        else:
            self.key_label.setText("不支持的按键，请重试")
    
    def get_key_name(self, key):
        """获取按键名称"""
        if key >= Qt.Key_A and key <= Qt.Key_Z:
            return chr(key).lower()
        elif key >= Qt.Key_0 and key <= Qt.Key_9:
            return chr(key)
        elif key == Qt.Key_Space:
            return "space"
        elif key == Qt.Key_Enter or key == Qt.Key_Return:
            return "enter"
        elif key == Qt.Key_Tab:
            return "tab"
        elif key == Qt.Key_Escape:
            return "esc"
        elif key == Qt.Key_Backspace:
            return "backspace"
        elif key == Qt.Key_Delete:
            return "delete"
        elif key == Qt.Key_Up:
            return "up"
        elif key == Qt.Key_Down:
            return "down"
        elif key == Qt.Key_Left:
            return "left"
        elif key == Qt.Key_Right:
            return "right"
        elif key == Qt.Key_F1:
            return "f1"
        elif key == Qt.Key_F2:
            return "f2"
        elif key == Qt.Key_F3:
            return "f3"
        elif key == Qt.Key_F4:
            return "f4"
        elif key == Qt.Key_F5:
            return "f5"
        elif key == Qt.Key_F6:
            return "f6"
        elif key == Qt.Key_F7:
            return "f7"
        elif key == Qt.Key_F8:
            return "f8"
        elif key == Qt.Key_F9:
            return "f9"
        elif key == Qt.Key_F10:
            return "f10"
        elif key == Qt.Key_F11:
            return "f11"
        elif key == Qt.Key_F12:
            return "f12"
        return None

class FileSelectDialog(QDialog):
    """文件选择对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择LRC文件")
        self.setGeometry(300, 300, 400, 200)
        self.file_path = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 拖拽区域
        drop_area = QLabel("请将LRC文件拖拽于此")
        drop_area.setAlignment(Qt.AlignCenter)
        drop_area.setStyleSheet("""
            QLabel {
                border: 2px dashed gray;
                border-radius: 10px;
                padding: 40px;
                font-size: 16px;
                background-color: #f8f8f8;
            }
            QLabel:hover {
                background-color: #e8e8ff;
            }
        """)
        drop_area.setAcceptDrops(True)
        drop_area.dragEnterEvent = self.drag_enter_event
        drop_area.dropEvent = self.drop_event
        layout.addWidget(drop_area)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # 手动选择按钮
        manual_btn = QPushButton("手动选择文件")
        manual_btn.clicked.connect(self.manual_select)
        layout.addWidget(manual_btn)
        
        # 按钮区域
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def drag_enter_event(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def drop_event(self, event):
        """拖拽释放事件"""
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith('.lrc'):
                self.file_path = file_path
                self.accept()
    
    def manual_select(self):
        """手动选择文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择LRC文件", "", "LRC文件 (*.lrc);;所有文件 (*.*)"
        )
        if file_path:
            self.file_path = file_path
            self.accept()
    
    def get_file_path(self):
        """获取文件路径"""
        return self.file_path

class LyricAutoFiller(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LRC歌词自动填写工具")
        self.setGeometry(100, 100, 1000, 700)
        
        # 变量初始化
        self.lyrics = []
        self.is_playing = False
        self.start_time = None
        self.current_index = 0
        self.lyric_thread = None
        self.start_hotkey = "f6"
        self.stop_hotkey = "f7"
        self.action_sequence = [
            ActionBlock("text", {"text": ""}),
            ActionBlock("key", {"key": "enter"})
        ]
        
        # 创建UI
        self.init_ui()
        
        # 注册热键
        self.register_hotkeys()
        
        # 启用拖拽
        self.setAcceptDrops(True)
    
    def init_ui(self):
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        layout = QVBoxLayout(central_widget)
        
        # 文件选择区域
        file_layout = QHBoxLayout()
        self.file_label = QLabel("未选择LRC文件")
        self.file_label.setStyleSheet("border: 1px solid gray; padding: 5px;")
        file_button = QPushButton("选择LRC文件")
        file_button.clicked.connect(self.select_lrc_file)
        file_layout.addWidget(self.file_label, 1)
        file_layout.addWidget(file_button)
        layout.addLayout(file_layout)
        
        # 歌词预览区域
        preview_group = QGroupBox("歌词预览")
        preview_layout = QVBoxLayout(preview_group)
        self.lyric_list = QListWidget()
        self.lyric_list.setAlternatingRowColors(True)
        # 设置列表样式
        self.lyric_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                selection-background-color: #4169E1;  /* 蓝色 */
                selection-color: white;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #4169E1;  /* 蓝色 */
                color: white;
            }
            QListWidget::item:hover {
                background-color: #E3E3FF;  /* 浅蓝色 */
            }
        """)
        preview_layout.addWidget(self.lyric_list)
        layout.addWidget(preview_group)
        
        # 控制区域
        control_group = QGroupBox("控制设置")
        control_layout = QVBoxLayout(control_group)
        
        # 热键设置
        hotkey_layout = QHBoxLayout()
        hotkey_layout.addWidget(QLabel("开始热键:"))
        self.start_hotkey_btn = QPushButton(self.start_hotkey.upper())
        self.start_hotkey_btn.clicked.connect(lambda: self.capture_hotkey("start"))
        hotkey_layout.addWidget(self.start_hotkey_btn)
        
        hotkey_layout.addWidget(QLabel("停止热键:"))
        self.stop_hotkey_btn = QPushButton(self.stop_hotkey.upper())
        self.stop_hotkey_btn.clicked.connect(lambda: self.capture_hotkey("stop"))
        hotkey_layout.addWidget(self.stop_hotkey_btn)
        
        hotkey_layout.addStretch()
        control_layout.addLayout(hotkey_layout)
        
        # 动作编辑器按钮
        self.action_editor_btn = QPushButton("编辑动作序列")
        self.action_editor_btn.clicked.connect(self.open_action_editor)
        control_layout.addWidget(self.action_editor_btn)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        self.start_button = QPushButton("开始")
        self.start_button.clicked.connect(self.start_filling)
        self.stop_button = QPushButton("停止")
        self.stop_button.clicked.connect(self.stop_filling)
        self.stop_button.setEnabled(False)
        btn_layout.addWidget(self.start_button)
        btn_layout.addWidget(self.stop_button)
        btn_layout.addStretch()
        control_layout.addLayout(btn_layout)
        
        layout.addWidget(control_group)
        
        # 状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("border: 1px solid gray; padding: 5px;")
        layout.addWidget(self.status_label)
        
        # 提示信息
        info_label = QLabel("提示: 可以拖拽LRC文件到窗口加载。确保目标输入框处于活动状态。")
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info_label)
    
    def capture_hotkey(self, hotkey_type):
        """捕获热键"""
        dialog = HotkeyCaptureDialog(f"设置{hotkey_type}热键", self)
        dialog.key_captured.connect(lambda key: self.set_hotkey(hotkey_type, key))
        dialog.exec()
    
    def set_hotkey(self, hotkey_type, key):
        """设置热键"""
        # 先移除旧的热键
        try:
            if hotkey_type == "start":
                keyboard.remove_hotkey(self.start_hotkey)
                self.start_hotkey = key
                self.start_hotkey_btn.setText(key.upper())
            else:
                keyboard.remove_hotkey(self.stop_hotkey)
                self.stop_hotkey = key
                self.stop_hotkey_btn.setText(key.upper())
        except:
            pass
        
        # 注册新热键
        self.register_hotkeys()
    
    def register_hotkeys(self):
        """注册全局热键"""
        try:
            keyboard.add_hotkey(self.start_hotkey, self.start_filling)
            keyboard.add_hotkey(self.stop_hotkey, self.stop_filling)
        except Exception as e:
            self.show_warning("热键注册失败", f"无法注册热键: {str(e)}")
    
    def show_warning(self, title, message):
        """显示警告消息（非阻塞方式）"""
        QTimer.singleShot(0, lambda: QMessageBox.warning(self, title, message))
    
    def open_action_editor(self):
        """打开动作编辑器"""
        dialog = ActionEditor(self)
        dialog.set_actions(self.action_sequence)
        if dialog.exec():
            self.action_sequence = dialog.get_actions()
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """拖拽释放事件"""
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith('.lrc'):
                self.load_lrc_file(file_path)
    
    def select_lrc_file(self):
        """选择LRC文件"""
        dialog = FileSelectDialog(self)
        if dialog.exec() and dialog.get_file_path():
            self.load_lrc_file(dialog.get_file_path())
    
    def parse_time(self, time_str):
        """解析LRC时间格式 [mm:ss.xx] 或 [mm:ss:xx]"""
        # 使用正则表达式匹配时间格式
        pattern = r'\[(\d+):(\d+)\.(\d+)\]'
        match = re.match(pattern, time_str)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            milliseconds = int(match.group(3))
            return minutes * 60 + seconds + milliseconds / 100.0
        
        # 尝试另一种格式 [mm:ss:xx]
        pattern2 = r'\[(\d+):(\d+):(\d+)\]'
        match = re.match(pattern2, time_str)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            hundredths = int(match.group(3))
            return minutes * 60 + seconds + hundredths / 100.0
        
        return None
    
    def load_lrc_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.readlines()
            
            self.lyrics = []
            for line in content:
                line = line.strip()
                if line and line.startswith('['):
                    # 使用正则表达式分离时间标签和歌词
                    pattern = r'(\[\d+:\d+\.\d+\]|\[\d+:\d+:\d+\])(.*)'
                    match = re.match(pattern, line)
                    
                    if match:
                        time_str = match.group(1)
                        lyric = match.group(2).strip()
                        
                        # 解析时间
                        total_seconds = self.parse_time(time_str)
                        if total_seconds is not None:
                            self.lyrics.append((total_seconds, lyric))
            
            # 按时间排序
            self.lyrics.sort(key=lambda x: x[0])
            
            # 更新UI
            self.file_label.setText(f"已选择: {file_path}")
            self.lyric_list.clear()
            for seconds, lyric in self.lyrics:
                time_str = f"{int(seconds)//60}:{int(seconds)%60:02d}.{int((seconds - int(seconds)) * 100):02d}"
                item = QListWidgetItem(f"[{time_str}] {lyric}")
                self.lyric_list.addItem(item)
            
            self.status_label.setText(f"已加载 {len(self.lyrics)} 条歌词")
            
        except Exception as e:
            self.show_warning("错误", f"无法读取LRC文件: {str(e)}")
    
    def start_filling(self):
        if not self.lyrics:
            self.show_warning("警告", "请先选择LRC文件")
            return
        
        if self.is_playing:
            return
        
        self.is_playing = True
        self.start_time = time.time()
        self.current_index = 0
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("正在自动填写歌词...")
        
        # 启动歌词填写线程
        self.lyric_thread = threading.Thread(target=self.lyric_filling_loop)
        self.lyric_thread.daemon = True
        self.lyric_thread.start()
    
    def stop_filling(self):
        if not self.is_playing:
            return
        
        self.is_playing = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("已停止")
        
        # 清除高亮
        self.highlight_current_lyric(-1)
    
    def lyric_filling_loop(self):
        while self.is_playing and self.current_index < len(self.lyrics):
            current_time = time.time() - self.start_time
            next_lyric_time = self.lyrics[self.current_index][0]
            
            if current_time >= next_lyric_time:
                # 在主线程中更新高亮显示
                self.highlight_current_lyric(self.current_index)
                
                # 执行动作序列
                lyric_text = self.lyrics[self.current_index][1]
                self.execute_action_sequence(lyric_text)
                
                self.current_index += 1
            
            # 短暂休眠以避免CPU过度使用
            time.sleep(0.01)
        
        # 循环结束
        if self.current_index >= len(self.lyrics):
            self.stop_filling()
            self.status_label.setText("所有歌词已填写完成")
    
    def highlight_current_lyric(self, index):
        """高亮显示当前歌词（在主线程中执行）"""
        # 使用QTimer.singleShot确保在主线程中执行UI操作
        QTimer.singleShot(0, lambda: self._highlight_current_lyric(index))
    
    def _highlight_current_lyric(self, index):
        """实际的高亮显示操作（在主线程中执行）"""
        # 清除所有选中
        self.lyric_list.clearSelection()
        
        # 设置当前高亮
        if 0 <= index < self.lyric_list.count():
            item = self.lyric_list.item(index)
            self.lyric_list.setCurrentItem(item)  # 设置当前项
            item.setSelected(True)  # 设置选中状态
            self.lyric_list.scrollToItem(item, QAbstractItemView.PositionAtCenter)  # 滚动到中间位置
    
    def execute_action_sequence(self, lyric_text):
        """执行动作序列"""
        for action in self.action_sequence:
            # 如果是文本动作，使用当前歌词
            if action.action_type == "text":
                # 创建一个临时动作，使用当前歌词
                temp_action = ActionBlock("text", {"text": lyric_text})
                temp_action.execute()
            else:
                action.execute()
    
    def closeEvent(self, event):
        # 程序关闭时停止填写
        self.stop_filling()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LyricAutoFiller()
    window.show()
    sys.exit(app.exec())
