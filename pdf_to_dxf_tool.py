import sys
import os
import fitz  # PyMuPDF
import ezdxf
import math
import subprocess  # 用于在后台默默调用 potrace.exe

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
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QImage  # 引入 QImage 替代 Pillow/OpenCV

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
        self.tab3 = QWidget() # 图片转DXF选项卡
        
        self.setup_pdf_to_dxf_tab()
        self.setup_dxf_to_pdf_tab()
        self.setup_img_to_dxf_tab() 
        
        self.tabs.addTab(self.tab1, "PDF 转 DXF")
        self.tabs.addTab(self.tab2, "DXF 转 PDF")
        self.tabs.addTab(self.tab3, "图片转 DXF (Potrace 引擎)")
        
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

    # ---- 图片转 DXF UI 布局 ----
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
        
        btn_convert = QPushButton("通过 Potrace 提取极致平滑 DXF 线条")
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

    # ---- 原有：几何曲线精简核心算法（道格拉斯-普克） ----
    def _point_line_distance(self, pt, p1, p2):
        x, y = pt[0], pt[1]
        x1, y1 = p1[0], p1[1]
        x2, y2 = p2[0], p2[1]
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return math.sqrt((x - x1) ** 2 + (y - y1) ** 2)
        return abs(dy * x - dx * y + x2 * y1 - y2 * x1) / math.sqrt(dx * dx + dy * dy)

    def _douglas_peucker(self, points, epsilon=0.05):
        if len(points) < 3:
            return points
        dmax = 0
        index = 0
        end = len(points) - 1
        for i in range(1, end):
            d = self._point_line_distance(points[i], points[0], points[end])
            if d > dmax:
                index = i
                dmax = d
        if dmax > epsilon:
            rec1 = self._douglas_peucker(points[:index + 1], epsilon)
            rec2 = self._douglas_peucker(points[index:], epsilon)
            return rec1[:-1] + rec2
        else:
            return [points[0], points[end]]

    # ==== 原有算法1：PDF 转 DXF ====
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
                                if len(current_polyline) > 1:
                                    simplified = self._douglas_peucker(current_polyline, epsilon=0.05)
                                    msp.add_lwpolyline(simplified)
                                current_polyline = [pt1, pt2]
                        elif item[0] == "re": 
                            if len(current_polyline) > 1:
                                simplified = self._douglas_peucker(current_polyline, epsilon=0.05)
                                msp.add_lwpolyline(simplified)
                            current_polyline = []
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
                                if len(current_polyline) > 1:
                                    simplified = self._douglas_peucker(current_polyline, epsilon=0.05)
                                    msp.add_lwpolyline(simplified)
                                current_polyline = sampled_points
                    if len(current_polyline) > 1:
                        simplified = self._douglas_peucker(current_polyline, epsilon=0.05)
                        msp.add_lwpolyline(simplified)

                text_blocks = page.get_text("blocks")
                for block in text_blocks:
                    lines = block[4].split('\n')
                    start_x, start_y = block[0], block[1]
                    for idx, line_text in enumerate(lines):
                        clean_text = line_text.strip()
                        if not clean_text: continue
                        current_y = start_y + (idx * 14)
                        dxf_text_x = (start_x + offset_x) * PT_TO_MM
                        dxf_text_y = (height - current_y) * PT_TO_MM
                        msp.add_text(clean_text, dxfattribs={'insert': (dxf_text_x, dxf_text_y), 'height': 3.5, 'style': 'STANDARD', 'layer': 'TEXT_LAYER'})
            if 'STANDARD' in doc.styles: doc.styles.get('STANDARD').dxf.font = 'SimSun.ttf'
            else: doc.styles.new('STANDARD', dxfattribs={'font': 'SimSun.ttf'})
            doc.saveas(dxf_path)
            QMessageBox.information(self, "成功", f"PDF 转 DXF 成功！\n保存路径：{dxf_path}")
        except Exception as e: QMessageBox.critical(self, "错误", f"转换失败：\n{str(e)}")

    # ==== 原有算法2：DXF 转 PDF ====
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
            src_doc = ezdxf.readfile(dxf_path)
            src_msp = src_doc.modelspace()
            clean_doc = ezdxf.new('R2010')
            clean_doc.header['$MEASUREMENT'] = 1
            clean_doc.header['$INSUNITS'] = 4  
            clean_msp = clean_doc.modelspace()

            def sanitize_and_copy(entity):
                if entity.dxftype() in ('POINT', 'MTEXT', 'TEXT', 'ATTRIB'): return
                try:
                    attrs = {'color': 7, 'lineweight': 0}
                    if entity.dxftype() == 'LINE': clean_msp.add_line(entity.dxf.start, entity.dxf.end, dxfattribs=attrs)
                    elif entity.dxftype() == 'LWPOLYLINE':
                        nl = clean_msp.add_lwpolyline(entity.get_points(), dxfattribs=attrs)
                        nl.closed = entity.closed
                    elif entity.dxftype() == 'POLYLINE':
                        points = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
                        if points:
                            nl = clean_msp.add_lwpolyline(points, dxfattribs=attrs)
                            try: nl.closed = entity.is_closed
                            except: nl.closed = False
                    elif entity.dxftype() == 'CIRCLE': clean_msp.add_circle(entity.dxf.center, entity.dxf.radius, dxfattribs=attrs)
                    elif entity.dxftype() == 'ARC': clean_msp.add_arc(entity.dxf.center, entity.dxf.radius, entity.dxf.start_angle, entity.dxf.end_angle, dxfattribs=attrs)
                except Exception: pass

            for entity in src_msp:
                if entity.dxftype() == 'INSERT':
                    try:
                        for sub_ent in entity.explode(): sanitize_and_copy(sub_ent)
                    except Exception: pass
                else: sanitize_and_copy(entity)

            context = RenderContext(clean_doc)
            backend = pymupdf.PyMuPdfBackend()
            frontend = Frontend(context, backend)
            frontend.draw_layout(clean_msp, finalize=True)
            pdf_bytes = None
            if hasattr(backend, 'doc') and backend.doc: pdf_bytes = backend.doc.tobytes()
            else:
                for method_name in ['get_pdf_bytes', 'get_bytes', 'to_bytes']:
                    if hasattr(backend, method_name):
                        try:
                            pdf_bytes = getattr(backend, method_name)()
                            if pdf_bytes: break
                        except Exception: continue
            if not pdf_bytes: raise AttributeError("无法从当前的后端引擎中捕获到任何 PDF 核心字节流。")
            with open(pdf_path, 'wb') as fp: fp.write(pdf_bytes)
            QMessageBox.information(self, "成功", f"DXF 转 PDF 成功！\n保存路径：{pdf_path}")
        except Exception as e: QMessageBox.critical(self, "错误", f"转换失败：\n{str(e)}")

    # ==== 🔥 新增算法3：利用 Potrace 命令行实现 100% 零依赖图片转 DXF ====
    def convert_img_to_dxf(self):
        img_path = self.txt_img_input.text()
        output_dir = self.txt_img_output.text()

        # 1. 核心安全检查：寻找当前目录下是否存在 potrace.exe
        potrace_exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), "potrace.exe")
        if not os.path.exists(potrace_exe):
            # 扩大搜索范围，检查当前工作目录
            potrace_exe = "potrace.exe"
            
        if not img_path or not os.path.exists(img_path):
            QMessageBox.warning(self, "错误", "请先选择有效的图片文件！")
            return
        if not output_dir or not os.path.exists(output_dir):
            QMessageBox.warning(self, "错误", "请选择有效的导出文件夹！")
            return

        base_name = os.path.splitext(os.path.basename(img_path))[0]
        # Potrace 只能识别无损的 BMP 格式，我们需要先转存一个临时 BMP 
        temp_bmp = os.path.join(output_dir, f"temp_{base_name}.bmp")
        dxf_path = os.path.join(output_dir, f"{base_name}_img.dxf")

        try:
            # 2. 借用 PyQt5 自带的 QImage，完美避开 Pillow 和 OpenCV 来保存 BMP
            qimg = QImage(img_path)
            if qimg.isNull():
                raise ValueError("图片加载失败，请检查格式是否损坏。")
            
            # 将图片转为单色/灰度并保存为标准 BMP 供 potrace 识别
            gray_qimg = qimg.convertToFormat(QImage.Format_Mono)
            gray_qimg.save(temp_bmp, "BMP")

            # 3. 调用后台命令行启动 potrace 转换成标准 DXF
            # -b dxf 代表导出格式为 dxf，-a 1.0 可以控制曲线平滑度
            cmd = [potrace_exe, temp_bmp, "-b", "dxf", "-o", dxf_path, "-a", "1.2"]
            
            # 隐藏 CMD 黑窗口（Windows下友好体验）
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            result = subprocess.run(cmd, startupinfo=startupinfo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # 4. 清理临时的中间 BMP 文件，保持文件夹干净
            if os.path.exists(temp_bmp):
                os.remove(temp_bmp)

            if result.returncode != 0:
                raise RuntimeError(f"Potrace 执行失败。请确保同级目录下有 potrace.exe 文件。\n错误信息：{result.stderr}")

            QMessageBox.information(self, "成功", f"图片矢量轮廓生成成功！\n【Potrace 高级拟合版】：线条平滑，裁片完美衔接！\n保存路径：{dxf_path}")
        except FileNotFoundError:
            QMessageBox.critical(self, "找不到核心组件", "未在程序同级目录下找到【potrace.exe】文件！\n请将该软件放入相同的文件夹中再运行。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"转换失败：\n{str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = UniversalConverter()
    ex.show()
    sys.exit(app.exec_off()) if hasattr(app, 'exec_off') else sys.exit(app.exec_())
