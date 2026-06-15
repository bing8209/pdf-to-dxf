def convert_dxf_to_pdf(self):
dxf_path = self.txt_dxf_input.text().strip()
output_dir = self.txt_dxf_output.text().strip()

```
if not dxf_path or not os.path.exists(dxf_path):
    QMessageBox.warning(self, "错误", "请先选择有效的 DXF 文件！")
    return

if not output_dir or not os.path.exists(output_dir):
    QMessageBox.warning(self, "错误", "请选择有效的导出目录！")
    return

base_name = os.path.splitext(os.path.basename(dxf_path))[0]
pdf_path = os.path.join(output_dir, f"{base_name}.pdf")

try:
    # --------------------------------------------------
    # 1. 读取原始DXF
    # --------------------------------------------------
    doc = ezdxf.readfile(dxf_path)

    # 强制毫米单位
    doc.header['$MEASUREMENT'] = 1
    doc.header['$INSUNITS'] = 4

    msp = doc.modelspace()

    # --------------------------------------------------
    # 2. 自动修复损坏实体（容错）
    # --------------------------------------------------
    try:
        auditor = doc.audit()
        if auditor.has_errors:
            print("发现DXF错误，已自动修复部分问题")
    except Exception:
        pass

    # --------------------------------------------------
    # 3. 计算真实边界
    # --------------------------------------------------
    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")

    try:
        from ezdxf.bbox import extents

        bbox = extents(msp)

        min_x = bbox.extmin.x
        min_y = bbox.extmin.y
        max_x = bbox.extmax.x
        max_y = bbox.extmax.y

    except Exception:
        pass

    width = max(100, max_x - min_x)
    height = max(100, max_y - min_y)

    # --------------------------------------------------
    # 4. 建立渲染上下文
    # --------------------------------------------------
    context = RenderContext(doc)

    backend = pymupdf.PyMuPdfBackend()

    frontend = Frontend(
        context,
        backend
    )

    # --------------------------------------------------
    # 5. 渲染原始模型空间
    # --------------------------------------------------
    frontend.draw_layout(
        msp,
        finalize=True
    )

    # --------------------------------------------------
    # 6. 输出PDF
    # --------------------------------------------------
    try:
        pdf_bytes = backend.get_bytes(
            page_size=(width, height),
            bg_color="#FFFFFF"
        )
    except TypeError:
        pdf_bytes = backend.get_bytes()

    with open(pdf_path, "wb") as fp:
        fp.write(pdf_bytes)

    QMessageBox.information(
        self,
        "成功",
        f"DXF 转 PDF 成功！\n\n"
        f"保存路径：\n{pdf_path}"
    )

except Exception as e:
    QMessageBox.critical(
        self,
        "错误",
        f"转换失败：\n{str(e)}"
    )
```
