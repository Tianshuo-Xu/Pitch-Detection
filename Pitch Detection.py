from math import floor
import sys
from PyQt5.QtCore import QThread, pyqtSignal, QObject, Qt
from PyQt5.QtGui import QFont, QPalette, QBrush, QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, \
    QLineEdit, QDialog, QLabel, QFormLayout
import numpy as np
from aubio import pitch as pc
import pyaudio

# initialise pyaudio
p = pyaudio.PyAudio()
note_name = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']   # note name
# open stream
buffer_size = 1024
pyaudio_format = pyaudio.paFloat32
n_channels = 2
samplerate = 48000
stream = p.open(format=pyaudio_format,
                channels=n_channels,
                rate=samplerate,
                input=True,
                frames_per_buffer=buffer_size)

# setup pitch
tolerance = 0.6
win_s = 4096    # fft size
hop_s = buffer_size*2    # hop size
pitch_o = pc("default", win_s, hop_s, samplerate)
pitch_o.set_unit("midi")
pitch_o.set_tolerance(tolerance)


# -----------------ui--------------------
class BackendThread(QObject):
    # 通过类成员对象定义信号
    update_name = pyqtSignal(str)
    update_dis = pyqtSignal(list)

    # 处理业务逻辑
    def run(self):
        flag = 1    # 0:perfect, -1:left, 1:right
        global set_return
        set_return = 'C0'
        return_list = [0, 0]
        while True:
            data = stream.read(buffer_size, exception_on_overflow=False)
            signal = np.fromstring(data, dtype=np.float32)
            pitch = pitch_o(signal)[0]
            perfect_pitch = floor(pitch)
            if perfect_pitch:  # 如果音高不为0：
                dis = pitch - perfect_pitch  # 不准度
                if dis > 0.5:
                    dis = 1 - dis
                    flag = -1
                    perfect_pitch += 1  # 四舍五入
                else:
                    flag = 1
                dis = int(dis * 100)
                if dis < 20:
                    flag = 0
                dis = int(dis / 10)
                name = perfect_pitch % 12  # 音名
                num = int(perfect_pitch / 12)     # 八度号

                set_return = note_name[name]+str(num)
                return_list = [flag, dis]

            self.update_name.emit(set_return)
            self.update_dis.emit(return_list)


class Window(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.setWindowTitle('Pitch Detection')

        self.palette_p = QPalette()     # 设置三种状态下对应的背景图片
        self.palette_p.setBrush(self.backgroundRole(), QBrush(QPixmap('green.png')))
        self.palette_l = QPalette()
        self.palette_l.setBrush(self.backgroundRole(), QBrush(QPixmap('blue.png')))
        self.palette_r = QPalette()
        self.palette_r.setBrush(self.backgroundRole(), QBrush(QPixmap('orange.png')))

        self.setPalette(self.palette_p)
        self.setAutoFillBackground(True)    # 自动填充

        self.resize(700, 430)
        self.input = QLineEdit(self)
        self.input.setAlignment(Qt.AlignCenter)
        self.input.setReadOnly(True)    # 设置为只读
        self.input.setFont(QFont("Arial", 125))
        self.input.setStyleSheet("background:transparent;border-width:0;border-style:outset")
        self.input.setGeometry(230, 100, 240, 240)

        self.dis_l = QLineEdit(self)
        self.dis_l.setAlignment(Qt.AlignRight)
        self.dis_l.setReadOnly(True)
        self.dis_l.setFont(QFont('Arial', 100))
        self.dis_l.setGeometry(30, 120, 200, 200)
        self.dis_l.setStyleSheet("background:transparent;border-width:0;border-style:outset")

        self.dis_r = QLineEdit(self)
        self.dis_r.setAlignment(Qt.AlignLeft)
        self.dis_r.setReadOnly(True)
        self.dis_r.setFont(QFont('Arial', 100))
        self.dis_r.setGeometry(470, 120, 200, 200)
        self.dis_r.setStyleSheet("background:transparent;border-width:0;border-style:outset")

        self.print_info = QLineEdit("Copyright © 2019 Tianshuo Xu. All rights reserved.", self)
        self.print_info.setReadOnly(True)
        self.print_info.setFont(QFont('Arial', 13))
        self.print_info.setAlignment(Qt.AlignRight)
        self.print_info.setGeometry(100, 400, 600, 30)
        self.print_info.setStyleSheet("background:transparent;border-width:0;border-style:outset")

        self.quit_but = QPushButton("Exit", self)
        self.quit_but.move(1, 1)
        self.quit_but.clicked.connect(self.quit)

        self.thread = QThread()
        # 创建线程
        self.backend = BackendThread()
        self.init_ui()

    def init_ui(self):
        # 连接信号
        self.backend.update_name.connect(self.handle_display)
        self.backend.update_dis.connect(self.display_distance)
        self.backend.moveToThread(self.thread)
        # 开始线程
        self.thread.started.connect(self.backend.run)
        self.thread.start()

    # 将当前时间输出到文本框
    def handle_display(self, data):
        self.input.setText(data)

    def display_distance(self, data_list):
        card = 'I ' * (data_list[1]-1)
        card = ' '+card
        if data_list[0] == 1:
            self.dis_r.setText(card)
            self.dis_l.setText('')
            self.setPalette(self.palette_r)
        elif data_list[0] == -1:
            self.dis_l.setText(card)
            self.dis_r.setText('')
            self.setPalette(self.palette_l)
        else:
            self.dis_r.setText('')
            self.dis_l.setText('')
            self.setPalette(self.palette_p)

    def quit(self):
        stream.stop_stream()
        stream.close()
        p.terminate()
        self.close()
        app.quit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec_())
