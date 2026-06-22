import sys
import os
import fitz  # PyMuPDF
import ezdxf
import math

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
        self.setWindowTitle('服装 CAD 多功能矢量转换工具 (PDF ↔ DXF ↔ 图片)')
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
        self.tabs.addTab(self.tab3, "图片转 DXF (宏观趋势直线拟合版)")
        
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
        
        btn_convert = QPushButton("智能自动补空 · 融合成数十厘米工业流线")
        btn_convert.setStyleSheet("background-color: #a855f7; font-weight: bold; padding: 10px; font-size: 15px;")
        btn_convert.clicked.connect(self.convert_img_to_dxf)
        layout.addWidget(btn_convert)
        self.tab3.setLayout(layout)

    def select_file(self, line_edit, file_filter, dir_edit):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", file_filter)
        if file_path:
            line_edit.setText(file_path)
            if not dir_edit.text(): dir_edit.setText(os.path.dirname(file_path))

    def select_dir(self, line_edit):
        dir_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if dir_path: line_edit.setText(dir_path)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            file_path = event.mimeData().urls()[0].toLocalFile().lower()
            current_tab = self.tabs.currentIndex()
            if current_tab == 0 and file_path.endswith('.pdf'): event.acceptProposedAction()
            elif current_tab == 1 and file_path.endswith('.dxf'): event.acceptProposedAction()
            elif current_tab == 2 and file_path.endswith(('.png', '.jpg', '.jpeg')): event.acceptProposedAction()

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
        if dx == 0 and dy == 0: return math.sqrt((x - x1) ** 2 + (y - y1) ** 2)
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

    def _generate_b_spline(self, points, num_samples_per_segment=15):
        if len(points) < 3: return points
        spline_points = []
        pts = [points[0]] + points + [points[-1]]
        
        for i in range(1, len(pts) - 2):
            p0, p1, p2, p3 = pts[i-1], pts[i], pts[i+1], pts[i+2]
            for j in range(num_samples_per_segment):
                t = j / num_samples_per_segment
                a1 = (-t**3 + 3*t**2 - 3*t + 1) / 6.0
                a2 = (3*t**3 - 6*t**2 + 4) / 6.0
                a3 = (-3*t**3 + 3*t**2 + 3*t + 1) / 6.0
                a4 = t**3 / 6.0
                qx = a1*p0[0] + a2*p1[0] + a3*p2[0] + a4*p3[0]
                qy = a1*p0[1] + a2*p1[1] + a3*p2[1] + a4*p3[1]
                spline_points.append((qx, qy))
                
        spline_points.append(points[-1])
        return spline_points

    def _merge_collinear_lines(self, lines, angle_threshold_deg=5.0, dist_threshold=40.0):
        if not lines: return []
        merged_lines = []
        used = [False] * len(lines)
        
        for i in range(len(lines)):
            if used[i]: continue
            p1, p2 = lines[i]
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            base_angle = math.atan2(dy, dx)
            current_line = [p1, p2]
            used[i] = True
            
            progress = True
            while progress:
                progress = False
                curr_start = current_line[0]
                curr_end = current_line[-1]
                
                for j in range(len(lines)):
                    if used[j]: continue
                    ta, tb = lines[j]
                    
                    tdx, tdy = tb[0] - ta[0], tb[1] - ta[1]
                    target_angle = math.atan2(tdy, tdx)
                    
                    angle_diff = abs(base_angle - target_angle)
                    if angle_diff > math.pi: angle_diff = 2 * math.pi - angle_diff
                    if angle_diff > math.pi / 2: angle_diff = math.pi - angle_diff
                    
                    if angle_diff <= math.radians(angle_threshold_deg):
                        d1 = math.sqrt((curr_end[0]-ta[0])**2 + (curr_end[1]-ta[1])**2)
                        d2 = math.sqrt((curr_end[0]-tb[0])**2 + (curr_end[1]-tb[1])**2)
                        d3 = math.sqrt((curr_start[0]-ta[0])**2 + (curr_start[1]-ta[1])**2)
                        d4 = math.sqrt((curr_start[0]-tb[0])**2 + (curr_start[1]-tb[1])**2)
                        
                        min_d = min(d1, d2, d3, d4)
                        mid_pt = ((ta[0]+tb[0])/2.0, (ta[1]+tb[1])/2.0)
                        side_dist = self._point_line_distance(mid_pt, curr_start, curr_end)
                        
                        if min_d <= dist_threshold and side_dist <= 8.0:
                            all_pts = current_line + [ta, tb]
                            if abs(dx) > abs(dy):
                                all_pts.sort(key=lambda p: p[0])
                            else:
                                all_pts.sort(key=lambda p: p[1])
                            
                            current_line = [all_pts[0], all_pts[-1]]
                            used[j] = True
                            progress = True
                            
            merged_lines.append((current_line[0], current_line[-1]))
        return merged_lines

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

    def convert_img_to_dxf(self):
        img_path = self.txt_img_input.text()
        output_dir = self.txt_img_output.text()

        if not img_path or not os.path.exists(img_path) or not output_dir:
            QMessageBox.warning(self, "错误", "请选择有效的输入和导出目录！")
            return

        base_name = os.path.splitext(os.path.basename(img_path))[0]
        final_dxf_path = os.path.join(output_dir, f"{base_name}_工业长流线单线版.dxf")

        try:
            src_qimg = QImage(img_path)
            if src_qimg.isNull():
                raise ValueError("图像加载失败。")
            gray_img = src_qimg.convertToFormat(QImage.Format_Grayscale8)
            width, height = gray_img.width(), gray_img.height()
            
            skeleton_map = [[False for _ in range(height)] for _ in range(width)]
            for y in range(6, height - 6):
                for x in range(6, width - 6):
                    p_center = qGray(gray_img.pixel(x, y))
                    p_left   = qGray(gray_img.pixel(x - 2, y))
                    p_right  = qGray(gray_img.pixel(x + 2, y))
                    p_up     = qGray(gray_img.pixel(x, y - 2))
                    p_down   = qGray(gray_img.pixel(x, y + 2))

                    if abs(p_right - p_left) > 12 or abs(p_down - p_up) > 12:
                        if p_center <= p_left and p_center <= p_right and p_center < 225:
                            skeleton_map[x][y] = True
                        elif p_center <= p_up and p_center <= p_down and p_center < 225:
                            skeleton_map[x][y] = True

            visited = [[False for _ in range(height)] for _ in range(width)]
            all_tracks = []
            directions = [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (-1,1), (1,-1), (1,1)]

            for y in range(6, height - 6):
                for x in range(6, width - 6):
                    if skeleton_map[x][y] and not visited[x][y]:
                        current_track = []
                        cx, cy = x, y
                        
                        while True:
                            visited[cx][cy] = True
                            current_track.append((float(cx), float(height - cy)))
                            
                            found_next = False
                            for dx, dy in directions:
                                nx, ny = cx + dx, cy + dy
                                if 0 <= nx < width and 0 <= ny < height:
                                    if skeleton_map[nx][ny] and not visited[nx][ny]:
                                        cx, cy = nx, ny
                                        found_next = True
                                        break
                            
                            if not found_next:
                                closest_gap_pt = None
                                min_gap_dist = 999.0
                                for r_y in range(max(6, cy - 15), min(height - 6, cy + 15)):
                                    for r_x in range(max(6, cx - 15), min(width - 6, cx + 15)):
                                        if skeleton_map[r_x][r_y] and not visited[r_x][r_y]:
                                            d = math.sqrt((r_x - cx)**2 + (r_y - cy)**2)
                                            if d < min_gap_dist and d > 2:
                                                min_gap_dist = d
                                                closest_gap_pt = (r_x, r_y)
                                
                                if closest_gap_pt:
                                    cx, cy = closest_gap_pt
                                    found_next = True

                            if not found_next:
                                break
                        
                        if len(current_track) > 15:
                            all_tracks.append(current_track)

            doc = ezdxf.new('R2010')
            doc.header['$MEASUREMENT'], doc.header['$INSUNITS'] = 1, 4
            msp = doc.modelspace()

            raw_straight_lines = []

            for track in all_tracks:
                if len(track) < 3:
                    continue
                
                start_pt = track[0]
                end_pt = track[-1]
                
                # 🚀 工业级趋势过滤：检查整条轨迹上，有多少比例的点“贴近”首尾连线
                inlier_count = 0
                # 放宽包络带厚度到 12 像素，允许扫描杂质和中度粗线条抖动
                tolerance_band = 12.0 
                
                for pt in track:
                    if self._point_line_distance(pt, start_pt, end_pt) <= tolerance_band:
                        inlier_count += 1
                
                # 计算属于该直线趋势的点所占的百分比
                inlier_ratio = inlier_count / len(track)
                
                # 🎯 核心改变：如果一条线上超过 82% 的点都在这个宏观直线带内，强行剥夺其曲线资格！
                if inlier_ratio >= 0.82:
                    raw_straight_lines.append((start_pt, end_pt))
                else:
                    # 确定是真正的弯曲圆弧，执行平滑样条逻辑
                    backbone_pts = self._douglas_peucker(track, epsilon=3.5)
                    if len(backbone_pts) > 2:
                        smooth_cad_line = self._generate_b_spline(backbone_pts, num_samples_per_segment=20)
                        if len(smooth_cad_line) > 1:
                            msp.add_lwpolyline(smooth_cad_line, dxfattribs={'color': 7, 'layer': 'CAD_LONG_SPLINE'})
                    else:
                        msp.add_lwpolyline(backbone_pts, dxfattribs={'color': 7, 'layer': 'CAD_LONG_SPLINE'})

            # 🎯 熔焊清洗阶段：放宽角度到 6.5 度，距离到 55 像素，暴力连接所有碎直段
            fin_straight_lines = self._merge_collinear_lines(raw_straight_lines, angle_threshold_deg=6.5, dist_threshold=55.0)
            
            for s_pt, e_pt in fin_straight_lines:
                msp.add_line(s_pt, e_pt, dxfattribs={'color': 7, 'layer': 'CAD_STRAIGHT_LINE'})

            doc.saveas(final_dxf_path)
            QMessageBox.information(self, "成功", f"图纸输出成功！\n路径：{final_dxf_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"转换失败：\n{str(e)}")

def qGray(rgb): return (qRed(rgb) * 11 + qGreen(rgb) * 16 + qBlue(rgb) * 5) >> 5
def qRed(rgb): return (rgb >> 16) & 0xff
def qGreen(rgb): return (rgb >> 8) & 0xff
def qBlue(rgb): return rgb & 0xff

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = UniversalConverter()
    ex.show()
    sys.exit(app.exec_())
