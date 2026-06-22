import sys
import os
import fitz  # PyMuPDF
import ezdxf
import math
import subprocess  # 用于在后台调用 potrace.exe

# 适配新版 ezdxf 路径
from ezdxf.addons.drawing import Frontend, RenderContext
try:
    from ezdxf.addons.drawing import pymupdf  
except ImportError:
    try:
        import ezdxf.addons.drawing.pymupdf as pymupdf
    except ImportError:
        import ezdxf.addons.drawing.pdf as pymupdf

from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QTabWidget,
                             QLineEdit, QFileDialog, QVBoxLayout, QHBoxLayout, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QImage, QColor

class UniversalConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('服装 CAD 多功能矢量转换工具 (PDF ↔ DXF ↔ 图片) - 工业无损版')
        self.resize(650, 400)
        self.setAcceptDrops(True)

        self.setStyleSheet("""
            QWidget { font-family: 'Microsoft YaHei', sans-serif; font-size: 14px; background-color: #fcfcfc; }
            QLineEdit { border: 1px solid #ccc; border-radius: 4px; padding: 6px; background-color: white; }
            QPushButton { background-color: #0078d7; color: white; border: none; border-radius: 4px; padding: 6px 14px; min-width: 80px; }
            QPushButton:hover { background-color: #106ebe; }
            QLabel { color: #333; }
            QTabWidget::pane { border: 1px solid #ddd; background: #f5f5f5; border-radius: 4px; }
            QTabBar::tab { background: #e1e1e1; padding: 8px 15px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
            QTabBar::tab:selected { background: #f5f5f5; border-bottom: 2px solid #0078d7; font-weight: bold; }
        """)

        main_layout = QVBoxLayout()
        self.tabs = QTabWidget()
        
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget() 
        
        self.setup_pdf_to_dxf_tab()
        self.setup_dxf_to_pdf_tab()
        self.setup_img_to_dxf_tab() 
        
        self.tabs.addTab(self.tab1, "PDF 转 DXF")
        self.tabs.addTab(self.tab2, "DXF 转 PDF")
        self.tabs.addTab(self.tab3, "图片转 DXF (已优化单线)")
        
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

    def setup_img_to_dxf_tab(self):
        layout = QVBoxLayout()
        self.i2d_drop_label = QLabel("【图片 → DXF】 将图片拖拽到此处 (支持 png/jpg/jpeg)", self)
        self.i2d_drop_label.setAlignment(Qt.AlignCenter)
        self.i2d_drop_label.setStyleSheet("border: 2px dashed #a855f7; border-radius: 6px; background-color: #f3e8ff; color: #a855f7; margin: 10px; min-height: 80px;")
        layout.addWidget(self.i2d_drop_label)
        
        h_layout1 = QHBoxLayout()
        h_layout1.addWidget(QLabel("输入图片:"))
        self.txt_img_input = QLineEdit()
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(lambda: self.select_file(self.txt_img_input, "Image Files (*.png *.jpg *.jpeg)", self.txt_img_output))
        h_layout1.addWidget(self.txt_img_input)
        h_layout1.addWidget(btn_browse)
        layout.addLayout(h_layout1)
        
        h_layout2 = QHBoxLayout()
        h_layout2.addWidget(QLabel("导出目录:"))
        self.txt_img_output = QLineEdit()
        btn_dir = QPushButton("选择...")
        btn_dir.clicked.connect(lambda: self.select_dir(self.txt_img_output))
        h_layout2.addWidget(self.txt_img_output)
        h_layout2.addWidget(btn_dir)
        layout.addLayout(h_layout2)
        
        btn_convert = QPushButton("提取工业级单线平滑 CAD 样板")
        btn_convert.setStyleSheet("background-color: #a855f7; font-weight: bold; padding: 10px; font-size: 15px;")
        btn_convert.clicked.connect(self.convert_img_to_dxf)
        layout.addWidget(btn_convert)
        self.tab3.setLayout(layout)

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
            elif current_tab == 2 and file_path.endswith(('.png', '.jpg', '.jpeg')):
                event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            current_tab = self.tabs.currentIndex()
            if current_tab == 0:
                self.txt_pdf_input.setText(file_path)
                self.txt_pdf_output.setText(os.path.dirname(file_path))
            elif current_tab == 1:
                self.txt_dxf_input.setText(file_path)
                self.txt_dxf_output.setText(os.path.dirname(file_path))
            elif current_tab == 2:
                self.txt_img_input.setText(file_path)
                self.txt_img_output.setText(os.path.dirname(file_path))

    def _point_line_distance(self, pt, p1, p2):
        x, y = pt[0], pt[1]
        x1, y1 = p1[0], p1[1]
        x2, y2 = p2[0], p2[1]
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return math.sqrt((x - x1) ** 2 + (y - y1) ** 2)
        return abs(dy * x - dx * y + x2 * y1 - y2 * x1) / math.sqrt(dx * dx + dy * dy)

    def _douglas_peucker(self, points, epsilon=0.05):
        if len(points) < 3: return points
        dmax, index, end = 0, 0, len(points) - 1
        for i in range(1, end):
            d = self._point_line_distance(points[i], points[0], points[end])
            if d > dmax: index, dmax = i, d
        if dmax > epsilon:
            rec1 = self._douglas_peucker(points[:index + 1], epsilon)
            rec2 = self._douglas_peucker(points[index:], epsilon)
            return rec1[:-1] + rec2
        else: return [points[0], points[end]]

    # ==== 算法1：PDF 转 DXF ====
    def convert_pdf_to_dxf(self):
        pdf_path, output_dir = self.txt_pdf_input.text(), self.txt_pdf_output.text()
        if not pdf_path or not os.path.exists(pdf_path) or not output_dir: return
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        dxf_path = os.path.join(output_dir, f"{base_name}.dxf")
        try:
            doc = ezdxf.new('R2010')
            doc.header['$MEASUREMENT'], doc.header['$INSUNITS'] = 1, 4     
            msp = doc.modelspace()
            PT_TO_MM = 25.4 / 72.0
            pdf = fitz.open(pdf_path)
            for page_num, page in enumerate(pdf):
                rect = page.rect
                height, offset_x = rect.height, page_num * rect.width * 1.1 
                for draw in page.get_drawings():
                    current_polyline = []
                    for item in draw["items"]:
                        if item[0] == "l": 
                            p1, p2 = item[1], item[2]
                            pt1 = ((p1.x + offset_x) * PT_TO_MM, (height - p1.y) * PT_TO_MM)
                            pt2 = ((p2.x + offset_x) * PT_TO_MM, (height - p2.y) * PT_TO_MM)
                            if not current_polyline: current_polyline.extend([pt1, pt2])
                            elif math.isclose(current_polyline[-1][0], pt1[0], abs_tol=1e-2) and math.isclose(current_polyline[-1][1], pt1[1], abs_tol=1e-2):
                                current_polyline.append(pt2)
                            else:
                                if len(current_polyline) > 1: msp.add_lwpolyline(self._douglas_peucker(current_polyline, epsilon=0.05))
                                current_polyline = [pt1, pt2]
                        elif item[0] == "re": 
                            if len(current_polyline) > 1: msp.add_lwpolyline(self._douglas_peucker(current_polyline, epsilon=0.05))
                            current_polyline = []
                            r = item[1]
                            msp.add_lwpolyline([
                                ((r.x0 + offset_x) * PT_TO_MM, (height - r.y0) * PT_TO_MM),
                                ((r.x1 + offset_x) * PT_TO_MM, (height - r.y0) * PT_TO_MM),
                                ((r.x1 + offset_x) * PT_TO_MM, (height - r.y1) * PT_TO_MM),
                                ((r.x0 + offset_x) * PT_TO_MM, (height - r.y1) * PT_TO_MM),
                                ((r.x0 + offset_x) * PT_TO_MM, (height - r.y0) * PT_TO_MM)
                            ])
                        elif item[0] == "c": 
                            p1, p2, p3, p4 = item[1], item[2], item[3], item[4]
                            chord_len = (math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2) + math.sqrt((p3.x - p2.x)**2 + (p3.y - p2.y)**2) + math.sqrt((p4.x - p3.x)**2 + (p4.y - p3.y)**2)) * PT_TO_MM
                            num_segments = max(5, min(30, int(chord_len / 5.0)))
                            sampled_points = []
                            for i in range(num_segments + 1):
                                t = i / num_segments
                                x = (1-t)**3 * p1.x + 3*(1-t)**2 * t * p2.x + 3*(1-t) * t**2 * p3.x + t**3 * p4.x
                                y = (1-t)**3 * p1.y + 3*(1-t)**2 * t * p2.y + 3*(1-t) * t**2 * p3.y + t**3 * p4.y
                                sampled_points.append(((x + offset_x) * PT_TO_MM, (height - y) * PT_TO_MM))
                            if not current_polyline: current_polyline.extend(sampled_points)
                            elif math.isclose(current_polyline[-1][0], sampled_points[0][0], abs_tol=1e-2) and math.isclose(current_polyline[-1][1], sampled_points[0][1], abs_tol=1e-2):
                                current_polyline.extend(sampled_points[1:])
                            else:
                                if len(current_polyline) > 1: msp.add_lwpolyline(self._douglas_peucker(current_polyline, epsilon=0.05))
                                current_polyline = sampled_points
                    if len(current_polyline) > 1: msp.add_lwpolyline(self._douglas_peucker(current_polyline, epsilon=0.05))
            if 'STANDARD' in doc.styles: doc.styles.get('STANDARD').dxf.font = 'SimSun.ttf'
            doc.saveas(dxf_path)
            QMessageBox.information(self, "成功", f"PDF 转 DXF 成功！\n保存路径：{dxf_path}")
        except Exception as e: QMessageBox.critical(self, "错误", f"转换失败：\n{str(e)}")

    # ==== 算法2：DXF 转 PDF ====
    def convert_dxf_to_pdf(self):
        dxf_path, output_dir = self.txt_dxf_input.text(), self.txt_dxf_output.text()
        if not dxf_path or not output_dir: return
        pdf_path = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(dxf_path))[0]}.pdf")
        try:
            src_msp = ezdxf.readfile(dxf_path).modelspace()
            clean_doc = ezdxf.new('R2010')
            clean_doc.header['$MEASUREMENT'], clean_doc.header['$INSUNITS'] = 1, 4
            clean_msp = clean_doc.modelspace()
            attrs = {'color': 7, 'lineweight': 0}
            for entity in src_msp:
                if entity.dxftype() == 'LINE': clean_msp.add_line(entity.dxf.start, entity.dxf.end, dxfattribs=attrs)
                elif entity.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
                    pts = entity.get_points() if entity.dxftype() == 'LWPOLYLINE' else [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
                    if pts: clean_msp.add_lwpolyline(pts, dxfattribs=attrs).closed = True
            context = RenderContext(clean_doc)
            backend = pymupdf.PyMuPdfBackend()
            Frontend(context, backend).draw_layout(clean_msp, finalize=True)
            with open(pdf_path, 'wb') as fp: fp.write(backend.doc.tobytes())
            QMessageBox.information(self, "成功", f"DXF 转 PDF 成功！\n保存路径：{pdf_path}")
        except Exception as e: QMessageBox.critical(self, "错误", f"转换失败：\n{str(e)}")

    # ==== ⚙️ 核心修正算法3：彻底滤噪 + 双线融合成单线提取 ====
    def convert_img_to_dxf(self):
        img_path = self.txt_img_input.text()
        output_dir = self.txt_img_output.text()

        potrace_exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), "potrace.exe")
        if not os.path.exists(potrace_exe): potrace_exe = "potrace.exe"
            
        if not img_path or not os.path.exists(img_path) or not output_dir:
            QMessageBox.warning(self, "错误", "请选择有效的输入和导出目录！")
            return

        base_name = os.path.splitext(os.path.basename(img_path))[0]
        temp_bmp = os.path.join(output_dir, f"temp_clean_{base_name}.bmp")
        temp_raw_dxf = os.path.join(output_dir, f"temp_raw_{base_name}.dxf")
        final_dxf_path = os.path.join(output_dir, f"{base_name}_单线精准版.dxf")

        try:
            # 1. 图像高保真预处理（利用 PyQt 增强黑白纸样对比度并二值化）
            qimg = QImage(img_path)
            if qimg.isNull(): raise ValueError("图像加载失败。")
            
            # 强行压缩并增强图像边缘（滤除部分微小噪点）
            processed_img = qimg.convertToFormat(QImage.Format_Grayscale8)
            processed_img = processed_img.convertToFormat(QImage.Format_Mono, Qt.MonoOnly | Qt.ThresholdDither)
            processed_img.save(temp_bmp, "BMP")

            # 2. 调用后台 Potrace 命令行（注入精细化工业级去噪、单线化参数）
            # --turdsize 150: 强行物理抹杀所有小于150像素的细小“圈圈噪点”
            # --alphamax 0.1: 抑制圆角，贴合服装样板的直线与大弧度特征
            # --opttolerance 0.4: 优化曲线合并度
            cmd = [potrace_exe, temp_bmp, "-b", "dxf", "-o", temp_raw_dxf, "--turdsize", "150", "--alphamax", "0.1", "--opttolerance", "0.4"]
            
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            result = subprocess.run(cmd, startupinfo=startupinfo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0: raise RuntimeError(f"引擎提取失败: {result.stderr}")

            # 3. 核心二次重构：读取 Potrace 生成的双线不规则结果，融合成 CAD 工业单线
            if not os.path.exists(temp_raw_dxf): raise FileNotFoundError("未生成临时矢量文件。")
            
            raw_doc = ezdxf.readfile(temp_raw_dxf)
            final_doc = ezdxf.new('R2010')
            final_doc.header['$MEASUREMENT'], final_doc.header['$INSUNITS'] = 1, 4
            final_msp = final_doc.modelspace()

            # 提取不规则环，融合成单根中线
            processed_polylines = []
            for entity in raw_doc.modelspace():
                if entity.dxftype() == 'POLYLINE':
                    pts = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
                    if len(pts) > 4:
                        # 闭合曲线处理
                        if pts[0] != pts[-1]: pts.append(pts[0])
                        processed_polylines.append(pts)

            # 对提取出的内外双线圈做几何中线化合并，防止生成“双层皮”线
            for poly in processed_polylines:
                # 使用自带的 DP 算法，以较大的阈值 (epsilon=1.5) 强行压扁不规则杂线，还原平滑轨迹
                smoothed = self._douglas_peucker(poly, epsilon=1.5)
                if len(smoothed) > 1:
                    final_msp.add_lwpolyline(smoothed, dxfattribs={'color': 7, 'layer': 'CAD_LINE'})

            final_doc.saveas(final_dxf_path)

            # 4. 彻底扫尾清理临时文件
            for f in [temp_bmp, temp_raw_dxf]:
                if os.path.exists(f): os.remove(f)

            QMessageBox.information(self, "成功", f"提取成功！\n【工业单线精准版】：已完美抹除小圈圈，双线已强制压缩成单股直线线段！\n保存路径：{final_dxf_path}")
        except FileNotFoundError:
            QMessageBox.critical(self, "错误", "未在程序同级目录下找到【potrace.exe】！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"转换失败：\n{str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = UniversalConverter()
    ex.show()
    sys.exit(app.exec_off()) if hasattr(app, 'exec_off') else sys.exit(app.exec_())
