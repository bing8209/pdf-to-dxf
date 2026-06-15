import sys
import os
import math
import fitz  # PyMuPDF
import ezdxf
# 引入 DXF 渲染模块
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt

from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QTabWidget,
                             QLineEdit, QFileDialog, QVBoxLayout, QHBoxLayout, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDragEnterEvent, QDropEvent

class UniversalConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('服装 CAD 双向矢量转换工具 (PDF ↔ DXF)')
        self.resize(600, 350)
        self.setAcceptDrops(True)

        # 样式表美化
        self.setStyleSheet("""
            QWidget {
                font-family: 'Microsoft YaHei', sans-serif;
                font-size: 14px;
                background-color: #fcfcfc;
            }
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 6px;
                background-color: white;
            }
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 14px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QLabel {
                color: #333;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                background: #f5f5f5;
                border-radius: 4px;
            }
            QTabBar::tab {
                background: #e1e1e1;
                padding: 8px 20px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #f5f5f5;
                border-bottom: 2px solid #0078d7;
                font-weight: bold;
            }
        """)

        # 主布局
        main_layout = QVBoxLayout()
        
        # 创建选项卡
        self.tabs = QTabWidget()
        
        # 初始化两个页面
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        
        self.setup_pdf_to_dxf_tab()
        self.setup_dxf_to_pdf_tab()
        
        self.tabs.addTab(self.tab1, "PDF 转 DXF (毫米/智能点)")
        self.tabs.addTab(self.tab2, "DXF 转 PDF (精准纸样生成)")
        
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

    # ---- 页面一：PDF 转 DXF 界面 ----
    def setup_pdf_to_dxf_tab(self):
        layout = QVBoxLayout()
        
        self.p2d_drop_label = QLabel("【PDF → DXF】 将 PDF 拖拽到此处", self)
        self.p2d_drop_label.setAlignment(Qt.AlignCenter)
        self.p2d_drop_label.setStyleSheet("border: 2px dashed #0078d7; border-radius: 6px; background-color: #e6f2ff; color: #0078d7; margin: 10px; min-height: 80px;")
        layout.addWidget(self.p2d_drop_label)
        
        h_layout1 = QHBoxLayout()
        h_layout1.addWidget(QLabel("输入 PDF:"))
        self.txt_pdf_input = QLineEdit()
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(lambda: self.select_file(self.txt_pdf_input, "PDF Files (*.pdf)", self.txt_pdf_output))
        h_layout1.addWidget(self.txt_pdf_input)
        h_layout1.addWidget(btn_browse)
        layout.addLayout(h_layout1)
        
        h_layout2 = QHBoxLayout()
        h_layout2.addWidget(QLabel("导出目录:"))
        self.txt_pdf_output = QLineEdit()
        btn_dir = QPushButton("选择...")
        btn_dir.clicked.connect(lambda: self.select_dir(self.txt_pdf_output))
        h_layout2.addWidget(self.txt_pdf_output)
        h_layout2.addWidget(btn_dir)
        layout.addLayout(h_layout2)
        
        btn_convert = QPushButton("开始转换成 DXF")
        btn_convert.setStyleSheet("background-color: #2ea44f; font-weight: bold; padding: 10px; font-size: 15px;")
        btn_convert.clicked.connect(self.convert_pdf_to_dxf)
        layout.addWidget(btn_convert)
        
        self.tab1.setLayout(layout)

    # ---- 页面二：DXF 转 PDF 界面 ----
    def setup_dxf_to_pdf_tab(self):
        layout = QVBoxLayout()
        
        self.d2p_drop_label = QLabel("【DXF → PDF】 将 DXF 拖拽到此处", self)
        self.d2p_drop_label.setAlignment(Qt.AlignCenter)
        self.d2p_drop_label.setStyleSheet("border: 2px dashed #2ea44f; border-radius: 6px; background-color: #e8f5e9; color: #2ea44f; margin: 10px; min-height: 80px;")
        layout.addWidget(self.d2p_drop_label)
        
        h_layout1 = QHBoxLayout()
        h_layout1.addWidget(QLabel("输入 DXF:"))
        self.txt_dxf_input = QLineEdit()
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(lambda: self.select_file(self.txt_dxf_input, "DXF Files (*.dxf)", self.txt_dxf_output))
        h_layout1.addWidget(self.txt_dxf_input)
        h_layout1.addWidget(btn_browse)
        layout.addLayout(h_layout1)
        
        h_layout2 = QHBoxLayout()
        h_layout2.addWidget(QLabel("导出目录:"))
        self.txt_dxf_output = QLineEdit()
        btn_dir = QPushButton("选择...")
        btn_dir.clicked.connect(lambda: self.select_dir(self.txt_dxf_output))
        h_layout2.addWidget(self.txt_dxf_output)
        h_layout2.addWidget(btn_dir)
        layout.addLayout(h_layout2)
        
        btn_convert = QPushButton("开始转换成 PDF")
        btn_convert.setStyleSheet("background-color: #0078d7; font-weight: bold; padding: 10px; font-size: 15px;")
        btn_convert.clicked.connect(self.convert_dxf_to_pdf)
        layout.addWidget(btn_convert)
        
        self.tab2.setLayout(layout)

    # ---- 通用界面交互逻辑 ----
    def select_file(self, line_edit, file_filter, dir_edit):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", file_filter)
        if file_path:
            line_edit.setText(file_path)
            if not dir_edit.text():
                dir_edit.setText(os.path.dirname(file_path))

    def select_dir(self, line_edit):
        dir_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if dir_path:
            line_edit.setText(dir_path)

    # ---- 拖拽逻辑支持（自动识别当前处于哪个Tab） ----
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            file_path = event.mimeData().urls()[0].toLocalFile().lower()
            current_tab = self.tabs.currentIndex()
            
            if current_tab == 0 and file_path.endswith('.pdf'):
                event.acceptProposedAction()
            elif current_tab == 1 and file_path.endswith('.dxf'):
                event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            current_tab = self.tabs.currentIndex()
            
            if current_tab == 0:
                self.txt_pdf_input.setText(file_path)
                self.txt_pdf_output.setText(os.path.dirname(file_path))
            else:
                self.txt_dxf_input.setText(file_path)
                self.txt_dxf_output.setText(os.path.dirname(file_path))

    # ==== 核心算法1：PDF 转 DXF ====
    def convert_pdf_to_dxf(self):
        pdf_path = self.txt_pdf_input.text()
        output_dir = self.txt_pdf_output.text()

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
                
                drawings = page.get_drawings()
                for draw in drawings:
                    for item in draw["items"]:
                        if item[0] == "l": 
                            p1, p2 = item[1], item[2]
                            msp.add_line(
                                ((p1.x + offset_x) * PT_TO_MM, (height - p1.y) * PT_TO_MM),
                                ((p2.x + offset_x) * PT_TO_MM, (height - p2.y) * PT_TO_MM)
                            )
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
                        elif item[0] == "c": 
                            p1, p2, p3, p4 = item[1], item[2], item[3], item[4]
                            chord_len = (
                                math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2) +
                                math.sqrt((p3.x - p2.x)**2 + (p3.y - p2.y)**2) +
                                math.sqrt((p4.x - p3.x)**2 + (p4.y - p3.y)**2)
                            ) * PT_TO_MM
                            # 💡 如果你觉得点还是多，可以把下方的 3.0 改成 6.0 甚至 8.0，点就会明显变稀疏
                            num_segments = max(5, min(30, int(chord_len / 5.0)))
                            
                            sampled_points = []
                            for i in range(num_segments + 1):
                                t = i / num_segments
                                x = (1-t)**3 * p1.x + 3*(1-t)**2 * t * p2.x + 3*(1-t) * t**2 * p3.x + t**3 * p4.x
                                y = (1-t)**3 * p1.y + 3*(1-t)**2 * t * p2.y + 3*(1-t) * t**2 * p3.y + t**3 * p4.y
                                sampled_points.append(((x + offset_x) * PT_TO_MM, (height - y) * PT_TO_MM))
                            msp.add_lwpolyline(sampled_points)

                # 提取文字
                text_blocks = page.get_text("blocks")
                for block in text_blocks:
                    lines = block[4].split('\n')
                    start_x = block[0]
                    start_y = block[1]
                    for idx, line_text in enumerate(lines):
                        clean_text = line_text.strip()
                        if not clean_text: continue
                        current_y = start_y + (idx * 14)
                        dxf_text_x = (start_x + offset_x) * PT_TO_MM
                        dxf_text_y = (height - current_y) * PT_TO_MM
                        msp.add_text(clean_text, dxfattribs={'insert': (dxf_text_x, dxf_text_y), 'height': 3.5, 'style': 'STANDARD', 'layer': 'TEXT_LAYER'})

            if 'STANDARD' in doc.styles:
                doc.styles.get('STANDARD').dxf.font = 'SimSun.ttf'
            else:
                doc.styles.new('STANDARD', dxfattribs={'font': 'SimSun.ttf'})

            doc.saveas(dxf_path)
            QMessageBox.information(self, "成功", f"PDF 转 DXF 成功！\n保存路径：{dxf_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"转换失败：\n{str(e)}")

    # ==== 核心算法2：全新加入的 DXF 转 PDF ====
    def convert_dxf_to_pdf(self):
        dxf_path = self.txt_dxf_input.text()
        output_dir = self.txt_dxf_output.text()

        if not dxf_path or not os.path.exists(dxf_path):
            QMessageBox.warning(self, "错误", "请先选择有效的 DXF 文件！")
            return
        if not output_dir or not os.path.exists(output_dir):
            QMessageBox.warning(self, "错误", "请选择有效的导出文件夹！")
            return

        base_name = os.path.splitext(os.path.basename(dxf_path))[0]
        pdf_path = os.path.join(output_dir, f"{base_name}.pdf")

        try:
            # 1. 读取服装 DXF 文件
            doc = ezdxf.readfile(dxf_path)
            msp = doc.modelspace()

            # 2. 创建 Matplotlib 渲染画布
            fig = plt.figure()
            ax = fig.add_axes([0, 0, 1, 1])
            ctx = RenderContext(doc)
            
            # 设置渲染背景为白色，线条为黑色（适合打印纸样）
            ctx.set_current_toggle_state(True)
            backend = MatplotlibBackend(ax)
            
            # 3. 渲染 DXF 实体
            Frontend(ctx, backend).draw_layout(msp, finalize=True)

            # 4. 紧凑布局并保存为高保真 PDF 矢量文件
            fig.savefig(pdf_path, format='pdf', bbox_inches='tight', dpi=300)
            plt.close(fig) # 及时释放内存

            QMessageBox.information(self, "成功", f"DXF 转 PDF 成功！\n已被完美渲染为公制高保真 PDF。\n保存路径：{pdf_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"转换失败：\n{str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = UniversalConverter()
    ex.show()
    sys.exit(app.exec_off()) if hasattr(app, 'exec_off') else sys.exit(app.exec_())
