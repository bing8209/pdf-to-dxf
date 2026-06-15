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
        self.setWindowTitle('PDF 转 DXF 服装矢量转换工具 (精准尺寸+防变形版)')
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
            self.txt_output.setText(os.path.dirname(file_path))
            self.drop_label.setText(f"已载入: {os.path.basename(file_path)}")
            self.dragLeaveEvent(None)

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

    # ==== 核心转换与高精度采样逻辑 ====
    def convert_file(self):
        pdf_path = self.txt_input.text()
        output_dir = self.txt_output.text()

        if not pdf_path or not os.path.exists(pdf_path):
            QMessageBox.warning(self, "错误", "请先选择有效的 PDF 文件！")
            return
        if not output_dir or not os.path.exists(output_dir):
            QMessageBox.warning(self, "错误", "请选择有效的导出文件夹！")
            return

        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        dxf_path = os.path.join(output_dir, f"{base_name}.dxf")

        try:
            # 服装 CAD 最习惯读取毫米(mm)或厘米(cm)，这里直接以 cm 为 DXF 基础单位
            doc = ezdxf.new('R2010')
            doc.header['$MEASUREMENT'] = 1  # 1 代表公制 Metric
            doc.header['$INSUNITS'] = 5     # 5 代表厘米 Centimeters (如果软件认毫米，这里改4，下方系数换算相应的即可)
            msp = doc.modelspace()

            # 换算单位系数：将 PDF 的 点(pt) 转换为 厘米(cm)
            # 1 inch = 72 points = 2.54 cm -> 1 pt = 2.54 / 72 ≈ 0.03527778 cm
            PT_TO_CM = 2.54 / 72.0

            pdf = fitz.open(pdf_path)
            
            for page_num, page in enumerate(pdf):
                rect = page.rect
                height = rect.height
                offset_x = page_num * rect.width * 1.1 
                
                drawings = page.get_drawings()
                
                for draw in drawings:
                    for item in draw["items"]:
                        
                        # 1. 绘制直线（应用比例尺）
                        if item[0] == "l": 
                            p1, p2 = item[1], item[2]
                            msp.add_line(
                                ((p1.x + offset_x) * PT_TO_CM, (height - p1.y) * PT_TO_CM),
                                ((p2.x + offset_x) * PT_TO_CM, (height - p2.y) * PT_TO_CM)
                            )
                            
                        # 2. 绘制矩形（应用比例尺）
                        elif item[0] == "re": 
                            r = item[1]
                            points = [
                                ((r.x0 + offset_x) * PT_TO_CM, (height - r.y0) * PT_TO_CM),
                                ((r.x1 + offset_x) * PT_TO_CM, (height - r.y0) * PT_TO_CM),
                                ((r.x1 + offset_x) * PT_TO_CM, (height - r.y1) * PT_TO_CM),
                                ((r.x0 + offset_x) * PT_TO_CM, (height - r.y1) * PT_TO_CM),
                                ((r.x0 + offset_x) * PT_TO_CM, (height - r.y0) * PT_TO_CM)
                            ]
                            msp.add_lwpolyline(points)
                            
                        # 3. 绘制贝塞尔曲线（高精度“增加点”离散化，彻底防变形）
                        elif item[0] == "c": 
                            p1, p2, p3, p4 = item[1], item[2], item[3], item[4]
                            
                            # 这里就是你要的“增加点”！
                            # 通过数学公式将一条贝塞尔曲线均匀拆解为 30 个连续的微小点段（可以根据需要调得更高）
                            num_segments = 30 
                            sampled_points = []
                            
                            for i in range(num_segments + 1):
                                t = i / num_segments
                                # 三次贝塞尔曲线公式
                                x = (1-t)**3 * p1.x + 3*(1-t)**2 * t * p2.x + 3*(1-t) * t**2 * p3.x + t**3 * p4.x
                                y = (1-t)**3 * p1.y + 3*(1-t)**2 * t * p2.y + 3*(1-t) * t**2 * p3.y + t**3 * p4.y
                                
                                # 转换坐标系并乘以比例尺
                                dxf_x = (x + offset_x) * PT_TO_CM
                                dxf_y = (height - y) * PT_TO_CM
                                sampled_points.append((dxf_x, dxf_y))
                            
                            # 用轻量级多段线把这 30 个点连起来，服装 CAD 读取时就是一条极为平滑的弧线
                            msp.add_lwpolyline(sampled_points)

            doc.saveas(dxf_path)
            QMessageBox.information(self, "成功", f"转换完成！\n尺寸已自动校准为厘米(cm)\n保存路径：{dxf_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"转换失败，错误原因：\n{str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = PDFtoDXFConverter()
    ex.show()
    sys.exit(app.exec_off()) if hasattr(app, 'exec_off') else sys.exit(app.exec_())
