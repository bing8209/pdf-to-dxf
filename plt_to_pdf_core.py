import sys
import os
import re
import fitz  # PyMuPDF 核心矢量引擎

def perfect_plt_to_pdf(plt_path):
    if not os.path.exists(plt_path):
        print(f"【错误】找不到输入的 PLT 文件: {plt_path}")
        return False

    print(f"【开始解析】正在读取 ET CAD 导出的 PLT 文件: {os.path.basename(plt_path)}")
    
    with open(plt_path, 'r', encoding='utf-8', errors='ignore') as f:
        plt_content = f.read()

    # 提取所有的 HPGL 标准工业指令
    commands = re.findall(r'([A-Z]{2})([^;]*)', plt_content)
    
    # -------------------------------------------------------------
    # 步骤 1：全图坐标扫描，精准锁定物理限界（Bounding Box），确保 100% 不丢片
    # -------------------------------------------------------------
    max_x, max_y = -9999999, -9999999
    min_x, min_y = 9999999, 9999999
    
    for cmd, args in commands:
        if cmd in ('PU', 'PD') and args.strip():
            coords = re.findall(r'(-?\d+),(-?\d+)', args)
            for x_str, y_str in coords:
                x, y = int(x_str), int(y_str)
                if x > max_x: max_x = x
                if y > max_y: max_y = y
                if x < min_x: min_x = x
                if y < min_y: min_y = y

    if max_x == -9999999:
        print("【错误】该 PLT 文件内未检测到任何有效的裁片几何轨迹坐标！")
        return False

    # 服装绘图仪标准单位：1 mm = 40 个 PLT 单位
    PLT_TO_PT = 72.0 / 1016.0  # 转换为 PDF 画布的标准 Point 点
    
    width_units = max_x - min_x
    height_units = max_y - min_y
    
    # 增加 20mm (约 56 point) 的工业安全留白，防止任何边缘裁片被贴边切掉
    padding = 56  
    pdf_width = width_units * PLT_TO_PT + padding * 2
    pdf_height = height_units * PT_TO_PT + padding * 2

    print(f"【尺寸量算】排料图实际物理门幅: {width_units/40:.1f}mm 宽, {height_units/40:.1f}mm 长。")
    print(f"【画布自适应】已为您自动定制 {pdf_width/72*25.4:.1f}mm x {pdf_height/72*25.4:.1f}mm 的无损 PDF 画布。")

    # -------------------------------------------------------------
    # 步骤 2：创建全新 PDF 矢量硬核绘制
    # -------------------------------------------------------------
    doc = fitz.open()
    page = doc.new_page(width=pdf_width, height=pdf_height)
    shape = page.new_shape()
    
    print("【矢量重构】正在将高密度纸样骨架无损映射至 PDF 矩阵...")
    for cmd, args in commands:
        if cmd in ('PU', 'PD'):
            coords = re.findall(r'(-?\d+),(-?\d+)', args)
            for idx, (x_str, y_str) in enumerate(coords):
                # 转换坐标，并作 Y 轴镜像（因为 PLT 坐标系与 PDF 坐标系上下颠倒）
                pdf_x = (int(x_str) - min_x) * PLT_TO_PT + padding
                pdf_y = pdf_height - ((int(y_str) - min_y) * PLT_TO_PT + padding)
                
                if idx == 0 and cmd == 'PU':
                    shape.move_to(fitz.Point(pdf_x, pdf_y))
                else:
                    shape.line_to(fitz.Point(pdf_x, pdf_y))

    # 锁定高保真工业级规范：纯黑线（0,0,0），线宽极细（0.25 point = 约 0.08mm），杜绝花颜色
    shape.finish(color=(0, 0, 0), width=0.25, close_path=False)
    shape.commit()
    
    # 导出最终的无损 PDF
    pdf_path = os.path.splitext(plt_path)[0] + ".pdf"
    doc.save(pdf_path)
    doc.close()
    
    print(f"【转换成功】完美矢量 PDF 已生成！保存路径：\n--> {pdf_path}\n")
    return True

if __name__ == '__main__':
    if len(sys.argv) > 1:
        perfect_plt_to_pdf(sys.argv[1])
    else:
        print("提示：请拖拽一个 ET 导出的 .plt 文件到本脚本上，或者在命令行传入参数运行。")
