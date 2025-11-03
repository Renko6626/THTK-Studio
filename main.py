# main.py

import sys
from PyQt6.QtWidgets import QApplication
from app.main_window import MainWindow

if __name__ == '__main__':
    # 1. 每个PyQt应用都需要一个QApplication实例
    app = QApplication(sys.argv)

    # 2. 创建主窗口的实例
    window = MainWindow()

    # 3. 显示窗口
    window.show()

    # 4. 启动应用程序的事件循环
    #    sys.exit()确保了程序可以干净地退
    # 在安全退出时输出退出
    #print("应用程序已安全退出")
    sys.exit(app.exec())
