import sys
import os
import fitz  # PyMuPDF
import ezdxf
import math
import matplotlib.pyplot as plt
from matplotlib.path import Path
import matplotlib.patches as patches

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

        main_layout = QVBoxLayout()
        self.tabs = QTabWidget()
        
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        
        self.setup_pdf_to_dxf_tab()
        self.setup_dxf_to_pdf_tab()
        
        self.tabs.addTab(self.tab1, "PDF 转 DXF (毫米/智能点)")
        self.tabs.addTab(self.tab2, "DXF 转 PDF (精准纸样生成)")
        
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

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
                            num_segments = max(5, min(30, int(chord_len / 5.0)))
                            
                            sampled_points = []
                            for i in range(num_segments + 1):
                                t = i / num_segments
                                x = (1-t)**3 * p1.x + 3*(1-t)**2 * t * p2.x + 3*(1-t) * t**2 * p3.x + t**3 * p4.x
                                y = (1-t)**3 * p1.y + 3*(1-t)**2 * t * p2.y + 3*(1-t) * t**2 * p3.y + t**3 * p4.y
                                sampled_points.append(((x + offset_x) * PT_TO_MM, (height - y) * PT_TO_MM))
                            msp.add_lwpolyline(sampled_points)

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

    # ==== 核心算法2：DXF 转 PDF（💡 彻底重构：底层几何坐标清洗映射法） ====
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
            # 1. 直接读取 DXF 数据
            doc = ezdxf.readfile(dxf_path)
            msp = doc.modelspace()

            # 2. 建立最高保真度的纯白画布
            fig, ax = plt.subplots(figsize=(12, 12), facecolor='#FFFFFF')
            ax.set_facecolor('#FFFFFF')
            ax.set_axis_off()

            # 3. 极其稳定的底层几何数据提取并绘制
            # 我们直接跳过 ezdxf 渲染器，直接抓取线条节点坐标，用纯黑色(black)+极细线(lw=0.4)亲自动手画
            for entity in msp:
                dxftype = entity.dxftype()
                
                # 处理普通单条直线
                if dxftype == 'LINE':
                    start = entity.dxf.start
                    end = entity.dxf.end
                    ax.plot([start.x, end.x], [start.y, end.y], color='black', linewidth=0.4, linestyle='-')
                    
                # 处理多段线 / 折线 / 裁片外轮廓
                elif dxftype in ('LWPOLYLINE', 'POLYLINE'):
                    points = []
                    for vertex in entity.vertices():
                        points.append((vertex[0], vertex[1]))
                    if points:
                        x_coords, y_coords = zip(*points)
                        # 💡 如果多段线是闭合的，让它自动闭合
                        if entity.closed:
                            x_coords = list(x_coords) + [x_coords[0]]
                            y_coords = list(y_coords) + [y_coords[0]]
                        # 🔒 强力封死：绝对只有线（color='black', lw=0.4），坚决不画任何点点！
                        ax.plot(x_coords, y_coords, color='black', linewidth=0.4, linestyle='-')

                # 处理圆或小圆孔
                elif dxftype == 'CIRCLE':
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    circle_patch = patches.Circle((center.x, center.y), radius, edgecolor='black', facecolor='none', linewidth=0.4)
                    ax.add_patch(circle_patch)

                # 处理圆弧
                elif dxftype == 'ARC':
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    start_angle = math.radians(entity.dxf.start_angle)
                    end_angle = math.radians(entity.dxf.end_angle)
                    # 细分圆弧
                    num_segments = 30
                    if end_angle < start_angle:
                        end_angle += 2 * math.pi
                    arc_x = []
                    arc_y = []
                    for i in range(num_segments + 1):
                        angle = start_angle + (end_angle - start_angle) * (i / num_segments)
                        arc_x.append(center.x + radius * math.cos(angle))
                        arc_y.append(center.y + radius * math.sin(angle))
                    ax.plot(arc_x, arc_y, color='black', linewidth=0.4)

            # 4. 自动缩放自适应裁片大小，防止线条超出画布
            ax.autoscale_view()
            ax.set_aspect('equal', adjustable='box')

            # 5. 秒级直接存储为高清矢量 PDF（由于没有多余计算，速度会极其恐怖）
            fig.savefig(
                pdf_path, 
                format='pdf', 
                bbox_inches='tight', 
                pad_inches=0.1, 
                facecolor='#FFFFFF', 
                edgecolor='none',
                dpi=100  # 纯几何线段不依赖高DPI，100就保证无限放大完全光滑
            )
            plt.close(fig) 

            QMessageBox.information(self, "成功", f"DXF 转 PDF 成功！\n【底层重构完毕】：纯白背景、无圆点、线条丝滑极细、转换极快！\n保存路径：{pdf_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"转换失败：\n{str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = UniversalConverter()
    ex.show()
    sys.exit(app.exec_off()) if hasattr(app, 'exec_off') else sys.exit(app.exec_())
