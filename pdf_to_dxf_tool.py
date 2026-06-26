import sys
import os
import fitz  # PyMuPDF
import ezdxf
import math
import cv2  
import numpy as np

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
from PyQt5.QtGui import QDragEnterEvent, QDropEvent

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
        self.tabs.addTab(self.tab3, "图片转 DXF (高精无锯齿版)")
        
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
        
        btn_convert = QPushButton("工业级滤波清洗 · 导出 ET 高清无锯齿完整轮廓")
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
                                if len(current_polyline) > 1: msp.add_lwpolyline(current_polyline)
                                current_polyline = [pt1, pt2]
                        elif item[0] == "re": 
                            if len(current_polyline) > 1: msp.add_lwpolyline(current_polyline)
                            current_polyline = []
                            r = item[1]
                            msp.add_lwpolyline([
                                ((r.x0 + offset_x) * PT_TO_MM, (height - r.y0) * PT_TO_MM),
                                ((r.x1 + offset_x) * PT_TO_MM, (height - r.y0) * PT_TO_MM),
                                ((r.x1 + offset_x) * PT_TO_MM, (height - r.y1) * PT_TO_MM),
                                ((r.x0 + offset_x) * PT_TO_MM, (height - r.y1) * PT_TO_MM),
                                ((r.x0 + offset_x) * PT_TO_MM, (height - r.y0) * PT_TO_MM)
                            ])
                    if len(current_polyline) > 1: msp.add_lwpolyline(current_polyline)
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

    # 🎯 工业级高清抗锯齿、智能防丢线转换核心
    def convert_img_to_dxf(self):
        img_path = self.txt_img_input.text()
        output_dir = self.txt_img_output.text()

        if not img_path or not os.path.exists(img_path) or not output_dir:
            QMessageBox.warning(self, "错误", "请选择有效的输入图片和导出目录！")
            return

        base_name = os.path.splitext(os.path.basename(img_path))[0]
        final_dxf_path = os.path.join(output_dir, f"{base_name}_高精光滑轮廓.dxf")

        try:
            # 1. 读取图像
            src_img = cv2.imread(img_path)
            if src_img is None:
                raise ValueError("图像加载失败，请检查路径是否包含中文字符或文件损坏。")
            
            # 转为灰度
            gray = cv2.cvtColor(src_img, cv2.COLOR_BGR2GRAY)
            height, width = gray.shape

            # 2. 【消灭锯齿核心 1】双层复合滤波器清洗像素级毛刺
            # 中值滤波去除孤立的扫描噪点碎点
            median = cv2.medianBlur(gray, 3)
            # 高斯模糊平滑多维边缘
            blurred = cv2.GaussianBlur(median, (5, 5), 0)

            # 3. 自适应大津法二值化
            _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            # 4. 【防止丢线核心 2】形态学“闭运算”智能缝合断线
            # 创建一个 3x3 的圆形核心，自动将图片中微小的断裂处、虚线处物理熔焊连接
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            binary_cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

            # 5. 高精轮廓提取
            # CHAIN_APPROX_NONE 保存全部轮廓像素点，防止任何细微弯曲丢失
            contours, _ = cv2.findContours(binary_cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

            # 6. 初始化 DXF
            doc = ezdxf.new('R2010')
            doc.header['$MEASUREMENT'], doc.header['$INSUNITS'] = 1, 4  # 公制毫米
            msp = doc.modelspace()

            converted_count = 0
            for contour in contours:
                # 过滤极小的环境噪点（周长小于 15 像素的不算裁片）
                if len(contour) < 15:
                    continue
                
                # 提取轮廓点并翻转 Y 轴匹配 ET CAD 坐标系
                raw_points = contour.reshape(-1, 2).astype(float)
                cad_points = [(pt[0], float(height) - pt[1]) for pt in raw_points]

                # 7. 【消灭锯齿核心 3】OpenCV 自带的高精 DP 曲线拟合（完美替代手写算法）
                # cv2.approxPolyDP 专门用于将密密麻麻的锯齿点集拟合为平滑的矢量几何图形
                # epsilon 是拟合精度。0.6 - 1.2 是服装制版的黄金比例：既能干掉锯齿，又能极高复原圆弧
                epsilon = 0.8
                # 注意：OpenCV 的拟合要求输入 numpy 数组，且格式正确
                contour_arr = np.array(cad_points, dtype=np.float32).reshape(-1, 1, 2)
                approx_contour = cv2.approxPolyDP(contour_arr, epsilon, closed=True)
                
                # 转回标准的 Python 坐标元组列表
                smooth_points = [(float(pt[0][0]), float(pt[0][1])) for pt in approx_contour]

                # 8. 确保绝对闭合 ──> 导入 ET 软件直接可用
                if len(smooth_points) > 2:
                    if smooth_points[0] != smooth_points[-1]:
                        smooth_points.append(smooth_points[0])
                    
                    # 写入 DXF 的标准多段线
                    msp.add_lwpolyline(smooth_points, dxfattribs={
                        'color': 7, 
                        'layer': 'ET_SMOOTH_CONTOUR'
                    })
                    converted_count += 1

            # 保存
            doc.saveas(final_dxf_path)
            QMessageBox.information(self, "成功", f"高精矢量转换成功！\n成功生成光滑闭合裁片线: {converted_count} 条\n路径：{final_dxf_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"矢量化失败：\n{str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = UniversalConverter()
    ex.show()
    sys.exit(app.exec_())
