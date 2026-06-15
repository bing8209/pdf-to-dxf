import sys
import os
import fitz  # PyMuPDF
import ezdxf
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, 
                             QLineEdit, QFileDialog, QVBoxLayout, QHBoxLayout, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDragEnterEvent, QDropEvent

class PDFtoDXFConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        # 设置窗口属性
        self.setWindowTitle('PDF 转 DXF 矢量转换工具')
        self.resize(550, 300)
        self.setAcceptDrops(True) # 开启拖拽接受

        # 样式表，美化界面
        self.setStyleSheet("""
            QWidget {
                font-family: 'Microsoft YaHei', sans-serif;
                font-size: 14px;
                background-color: #f5f5f5;
            }
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QLabel {
                color: #333;
            }
        """)

        # 主布局
        main_layout = QVBoxLayout()

        # 拖拽提示区域
        self.drop_label = QLabel("将 PDF 文件拖拽到此处，或在下方选择文件", self)
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setStyleSheet("""
            border: 2px dashed #0078d7;
            border-radius: 8px;
            background-color: #e6f2ff;
            font-size: 16px;
            color: #0078d7;
            margin: 10px;
        """)
        self.drop_label.setMinimumHeight(100)
        main_layout.addWidget(self.drop_label)

        # 输入文件选择
        input_layout = QHBoxLayout()
        self.lbl_input = QLabel("输入文件:")
        self.txt_input = QLineEdit()
        self.btn_input = QPushButton("浏览...")
        self.btn_input.clicked.connect(self.select_input_file)
        input_layout.addWidget(self.lbl_input)
        input_layout.addWidget(self.txt_input)
        input_layout.addWidget(self.btn_input)
        main_layout.addLayout(input_layout)

        # 输出目录选择
        output_layout = QHBoxLayout()
        self.lbl_output = QLabel("导出目录:")
        self.txt_output = QLineEdit()
        self.btn_output = QPushButton("选择...")
        self.btn_output.clicked.connect(self.select_output_dir)
        output_layout.addWidget(self.lbl_output)
        output_layout.addWidget(self.txt_output)
        output_layout.addWidget(self.btn_output)
        main_layout.addLayout(output_layout)

        # 转换按钮
        self.btn_convert = QPushButton("开始转换", self)
        self.btn_convert.setStyleSheet("""
            background-color: #2ea44f;
            font-weight: bold;
            font-size: 16px;
            padding: 10px;
        """)
        self.btn_convert.clicked.connect(self.convert_file)
        main_layout.addWidget(self.btn_convert)

        self.setLayout(main_layout)

    # ==== 拖拽事件处理 ====
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            # 检查拖入的文件是否是 PDF
            file_path = event.mimeData().urls()[0].toLocalFile()
            if file_path.lower().endswith('.pdf'):
                event.acceptProposedAction()
                self.drop_label.setStyleSheet("""
                    border: 2px dashed #2ea44f;
                    border-radius: 8px;
                    background-color: #e8f5e9;
                    font-size: 16px;
                    color: #2ea44f;
                    margin: 10px;
                """)

    def dragLeaveEvent(self, event):
        # 恢复原样
        self.drop_label.setStyleSheet("""
            border: 2px dashed #0078d7;
            border-radius: 8px;
            background-color: #e6f2ff;
            font-size: 16px;
            color: #0078d7;
            margin: 10px;
        """)

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.txt_input.setText(file_path)
            # 自动设置默认输出目录为文件所在目录
            self.txt_output.setText(os.path.dirname(file_path))
            self.drop_label.setText(f"已载入: {os.path.basename(file_path)}")
            # 恢复样式
            self.dragLeaveEvent(None)

    # ==== 按钮事件处理 ====
    def select_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择 PDF 文件", "", "PDF Files (*.pdf)")
        if file_path:
            self.txt_input.setText(file_path)
            if not self.txt_output.text():
                self.txt_output.setText(os.path.dirname(file_path))

    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择导出文件夹")
        if dir_path:
            self.txt_output.setText(dir_path)

    # ==== 核心转换逻辑 ====
    def convert_file(self):
        pdf_path = self.txt_input.text()
        output_dir = self.txt_output.text()

        if not pdf_path or not os.path.exists(pdf_path):
            QMessageBox.warning(self, "错误", "请先选择有效的 PDF 文件！")
            return
        if not output_dir or not os.path.exists(output_dir):
            QMessageBox.warning(self, "错误", "请选择有效的导出文件夹！")
            return

        # 确定输出文件名
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        dxf_path = os.path.join(output_dir, f"{base_name}.dxf")

        try:
            # 初始化 DXF 文档 (使用 R2010 格式兼容性好)
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()

            # 打开 PDF
            pdf = fitz.open(pdf_path)
            
            # 遍历 PDF 页面
            for page_num, page in enumerate(pdf):
                rect = page.rect
                height = rect.height
                
                # 为了防止多页 PDF 叠加，每页之间做一个水平偏移
                offset_x = page_num * rect.width * 1.1 
                
                # 获取页面上的所有矢量路径
                drawings = page.get_drawings()
                
                for draw in drawings:
                    # 获取颜色（RGB 转 AutoCAD 颜色索引或使用近似值，这里简化为默认色）
                    for item in draw["items"]:
                        # 1. 绘制直线
                        if item[0] == "l": 
                            p1, p2 = item[1], item[2]
                            # PDF y轴向下，DXF y轴向上，需要翻转 Y 坐标
                            msp.add_line(
                                (p1.x + offset_x, height - p1.y),
                                (p2.x + offset_x, height - p2.y)
                            )
                        # 2. 绘制矩形
                        elif item[0] == "re": 
                            r = item[1]
                            points = [
                                (r.x0 + offset_x, height - r.y0),
                                (r.x1 + offset_x, height - r.y0),
                                (r.x1 + offset_x, height - r.y1),
                                (r.x0 + offset_x, height - r.y1),
                                (r.x0 + offset_x, height - r.y0)
                            ]
                            msp.add_lwpolyline(points)
                        # 3. 绘制贝塞尔曲线 (转化为样条曲线 Spline)
                        elif item[0] == "c": 
                            p1, p2, p3, p4 = item[1], item[2], item[3], item[4]
                            pts = [
                                (p.x + offset_x, height - p.y) for p in [p1, p2, p3, p4]
                            ]
                            msp.add_spline(pts)

            # 保存 DXF
            doc.saveas(dxf_path)
            QMessageBox.information(self, "成功", f"转换完成！\n保存路径：{dxf_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"转换失败，错误原因：\n{str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = PDFtoDXFConverter()
    ex.show()
    sys.exit(app.exec_off()) if hasattr(app, 'exec_off') else sys.exit(app.exec_())
