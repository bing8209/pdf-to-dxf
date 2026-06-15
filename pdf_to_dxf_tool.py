import sys
import os
import math
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
        self.setWindowTitle('PDF 转 DXF 服装矢量转换工具 (毫米+智能布点版)')
        self.resize(550, 300)
        self.setAcceptDrops(True)

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

        main_layout = QVBoxLayout()

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

        input_layout = QHBoxLayout()
        self.lbl_input = QLabel("输入文件:")
        self.txt_input = QLineEdit()
        self.btn_input = QPushButton("浏览...")
        self.btn_input.clicked.connect(self.select_input_file)
        input_layout.addWidget(self.lbl_input)
        input_layout.addWidget(self.txt_input)
        input_layout.addWidget(self.btn_input)
        main_layout.addLayout(input_layout)

        output_layout = QHBoxLayout()
        self.lbl_output = QLabel("导出目录:")
        self.txt_output = QLineEdit()
        self.btn_output = QPushButton("选择...")
        self.btn_output.clicked.connect(self.select_output_dir)
        output_layout.addWidget(self.lbl_output)
        output_layout.addWidget(self.txt_output)
        output_layout.addWidget(self.btn_output)
        main_layout.addLayout(output_layout)

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

    # ==== 核心转换：高精度 mm 映射 + 智能动态布点 + 文本提取 ====
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
            doc = ezdxf.new('R2010')
            doc.header['$MEASUREMENT'] = 1  
            doc.header['$INSUNITS'] = 4     
            msp = doc.modelspace()

            PT_TO_MM = 25.4 / 72.0

            pdf = fitz.open(pdf_path)
            
            for page_num, page in enumerate(pdf):
                rect = page.rect
                height = rect.height
                offset_x = page_num * rect.width * 1.1 
                
                # --- A部分：提取线条与图形 ---
                drawings = page.get_drawings()
                for draw in drawings:
                    for item in draw["items"]:
                        # 绘制直线
                        if item[0] == "l": 
                            p1, p2 = item[1], item[2]
                            msp.add_line(
                                ((p1.x + offset_x) * PT_TO_MM, (height - p1.y) * PT_TO_MM),
                                ((p2.x + offset_x) * PT_TO_MM, (height - p2.y) * PT_TO_MM)
                            )
                        # 绘制矩形
                        elif item[0] == "re": 
                            r = item[1]
                            points = [
                                ((r.x0 + offset_x) * PT_TO_MM, (height - r.y0) * PT_TO_MM),
                                ((r.x1 + offset_x) * PT_TO_MM, (height - r.y0) * PT_TO_MM),
                                ((r.x1 + offset_x) * PT_TO_MM, (height - r.y1) * PT_TO_MM),
                                ((r.x0 + offset_x) * PT_TO_MM, (height - r.y1) * PT_TO_MM),
                                ((r.x0 + offset_x) * PT_TO_MM, (height - r.y0) * PT_TO_MM)
                            ]
                            msp.add_lwpolyline(points)
                        # 绘制贝塞尔曲线（【智能优化点】：动态加点算法）
                        elif item[0] == "c": 
                            p1, p2, p3, p4 = item[1], item[2], item[3], item[4]
                            
                            # 1. 估算贝塞尔曲线的控制弦长（用控制点间的直线距离之和代替真实曲线长度）
                            chord_len = (
                                math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2) +
                                math.sqrt((p3.x - p2.x)**2 + (p3.y - p2.y)**2) +
                                math.sqrt((p4.x - p3.x)**2 + (p4.y - p3.y)**2)
                            ) * PT_TO_MM  # 换算成实际毫米长度
                            
                            # 2. 核心算法：每 3 毫米分配 1 个点，但最少不低于 6 个点，最多不超过 35 个点
                            num_segments = max(6, min(35, int(chord_len / 3.0)))
                            
                            sampled_points = []
                            for i in range(num_segments + 1):
                                t = i / num_segments
                                x = (1-t)**3 * p1.x + 3*(1-t)**2 * t * p2.x + 3*(1-t) * t**2 * p3.x + t**3 * p4.x
                                y = (1-t)**3 * p1.y + 3*(1-t)**2 * t * p2.y + 3*(1-t) * t**2 * p3.y + t**3 * p4.y
                                sampled_points.append(((x + offset_x) * PT_TO_MM, (height - y) * PT_TO_MM))
                            msp.add_lwpolyline(sampled_points)

                # --- B部分：提取文字 ---
                text_blocks = page.get_text("blocks")
                for block in text_blocks:
                    lines = block[4].split('\n')
                    start_x = block[0]
                    start_y = block[1]
                    
                    for idx, line_text in enumerate(lines):
                        clean_text = line_text.strip()
                        if not clean_text:
                            continue
                            
                        current_y = start_y + (idx * 14)
                        
                        dxf_text_x = (start_x + offset_x) * PT_TO_MM
                        dxf_text_y = (height - current_y) * PT_TO_MM
                        
                        msp.add_text(
                            clean_text, 
                            dxfattribs={
                                'insert': (dxf_text_x, dxf_text_y),
                                'height': 3.5, 
                                'style': 'STANDARD', 
                                'layer': 'TEXT_LAYER'
                            }
                        )

            if 'STANDARD' in doc.styles:
                standard_style = doc.styles.get('STANDARD')
                standard_style.dxf.font = 'SimSun.ttf' 
            else:
                doc.styles.new('STANDARD', dxfattribs={'font': 'SimSun.ttf'})

            doc.saveas(dxf_path)
            QMessageBox.information(self, "成功", f"转换完成！\n尺寸已校准为毫米(mm)\n线条点数已完成智能精简优化。\n保存路径：{dxf_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"转换失败，错误原因：\n{str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = PDFtoDXFConverter()
    ex.show()
    sys.exit(app.exec_off()) if hasattr(app, 'exec_off') else sys.exit(app.exec_())
