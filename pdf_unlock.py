"""Remove PDF encryption and flatten signature appearances without rasterizing pages."""
from io import BytesIO
import math
import re

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    IndirectObject,
    NameObject,
    NullObject,
    StreamObject,
)

MAX_PDF_BYTES = 50 * 1024 * 1024


class PdfUnlockError(ValueError):
    def __init__(self, message: str, code: str = "pdf_error"):
        super().__init__(message)
        self.code = code


def field_type(field):
    seen = set()
    while field is not None:
        field = field.get_object()
        if id(field) in seen:
            raise PdfUnlockError("PDF 表单结构损坏，无法处理。")
        seen.add(id(field))
        if "/FT" in field:
            return field["/FT"]
        field = field.get("/Parent")
    return None


def flatten_signature(writer, page, annotation, index):
    # Invisible/hidden signature widgets have no visible appearance to preserve.
    flags = int(annotation.get("/F", 0))
    rect = [float(v) for v in annotation.get("/Rect", [0, 0, 0, 0])]
    left, right = sorted((rect[0], rect[2]))
    bottom, top = sorted((rect[1], rect[3]))
    if flags & (1 | 2 | 32) or right == left or top == bottom:
        return False
    appearance = annotation.get("/AP")
    normal = appearance.get_object().get("/N") if appearance else None
    normal = normal.get_object() if normal is not None else None
    if isinstance(normal, DictionaryObject) and not isinstance(normal, StreamObject):
        normal = normal.get(annotation.get("/AS"))
        normal = normal.get_object() if normal is not None else None
    if not isinstance(normal, StreamObject):
        raise PdfUnlockError("有签章缺少可用的外观，无法保证保留完整签章。请先用 PDF 阅读器重新保存该文件。")
    box = [float(v) for v in normal["/BBox"]]
    a, b, c, d, e, f = [float(v) for v in normal.get("/Matrix", [1, 0, 0, 1, 0, 0])]
    corners = [(a*x+c*y+e, b*x+d*y+f) for x in (box[0], box[2]) for y in (box[1], box[3])]
    x0, x1 = min(x for x, y in corners), max(x for x, y in corners)
    y0, y1 = min(y for x, y in corners), max(y for x, y in corners)
    if x1 == x0 or y1 == y0 or not all(math.isfinite(v) for v in (*rect, *box, a, b, c, d, e, f)):
        raise PdfUnlockError("签章外观的尺寸无效，无法保留该签章。")
    sx, sy = (right-left)/(x1-x0), (top-bottom)/(y1-y0)
    tx, ty = left-sx*x0, bottom-sy*y0
    # Copy resource dictionaries so inherited/shared resources remain independent.
    resources = DictionaryObject(page.get("/Resources", DictionaryObject()).get_object())
    xobjects = DictionaryObject(resources.get("/XObject", DictionaryObject()).get_object())
    name = NameObject(f"/UnlockedSignature{index}")
    while name in xobjects:
        name = NameObject(str(name) + "_")
    xobjects[name] = writer._add_object(normal)
    resources[NameObject("/XObject")] = xobjects
    page[NameObject("/Resources")] = resources
    # Keep the original page content streams intact. Decoding and replacing
    # them can silently drop page artwork when pypdf cannot resolve an unusual
    # /Contents structure. PDF pages may have one stream or an array of streams.
    original_contents = page.get("/Contents")
    resolved_contents = (
        original_contents.get_object()
        if isinstance(original_contents, IndirectObject)
        else original_contents
    )
    if isinstance(resolved_contents, ArrayObject):
        contents = ArrayObject(resolved_contents)
    elif resolved_contents is None or isinstance(resolved_contents, NullObject):
        contents = ArrayObject()
    else:
        original_ref = original_contents
        if not isinstance(original_ref, IndirectObject) and isinstance(resolved_contents, StreamObject):
            original_ref = writer._add_object(resolved_contents)
        contents = ArrayObject([original_ref])

    stream = DecodedStreamObject()
    command = f"q\n{left:.8f} {bottom:.8f} {right-left:.8f} {top-bottom:.8f} re W n\n{sx:.8f} 0 0 {sy:.8f} {tx:.8f} {ty:.8f} cm\n{name} Do\nQ\n"
    stream.set_data(command.encode("ascii"))
    contents.append(writer._add_object(stream))
    page[NameObject("/Contents")] = contents
    return True


def prune_signature_fields(fields, seen=None):
    seen = set() if seen is None else seen
    kept = ArrayObject()
    for ref in fields:
        field = ref.get_object()
        if id(field) in seen:
            raise PdfUnlockError("PDF 表单结构损坏，无法处理。")
        seen.add(id(field))
        if field_type(field) == "/Sig":
            continue
        if "/Kids" in field:
            field[NameObject("/Kids")] = prune_signature_fields(field["/Kids"], seen)
        kept.append(ref)
    return kept


def unlock_pdf(data: bytes, password: str = "") -> tuple[bytes, int, int]:
    if not data or b"%PDF-" not in data[:1024]:
        raise PdfUnlockError("请选择有效的 PDF 文件。")
    if len(data) > MAX_PDF_BYTES:
        raise PdfUnlockError("PDF 文件不能超过 50 MB。")
    reader = PdfReader(BytesIO(data))
    if reader.is_encrypted:
        # Preserve permissions-only unlocking even if an unnecessary password was entered.
        decrypted = reader.decrypt(password)
        if not decrypted and password:
            decrypted = reader.decrypt("")
        if not decrypted:
            if password:
                raise PdfUnlockError("密码不正确，请重新输入打开密码或权限密码。", "password_incorrect")
            raise PdfUnlockError("该 PDF 设置了打开密码，请输入密码后重试；无法在不知道密码的情况下直接解密。", "password_required")
    if not reader.pages:
        raise PdfUnlockError("PDF 中没有可处理的页面。")
    writer = PdfWriter(clone_from=reader)
    count = 0
    for page in writer.pages:
        kept = ArrayObject()
        for ref in page.get("/Annots", []):
            annotation = ref.get_object()
            if field_type(annotation) == "/Sig":
                count += int(flatten_signature(writer, page, annotation, count))
            else:
                kept.append(ref)
        if "/Annots" in page:
            page[NameObject("/Annots")] = kept
    form = writer.root_object.get("/AcroForm")
    if form:
        form = form.get_object()
        form[NameObject("/Fields")] = prune_signature_fields(form.get("/Fields", []))
        form.pop(NameObject("/SigFlags"), None)
        if not form["/Fields"]:
            writer.root_object.pop(NameObject("/AcroForm"), None)
    writer.root_object.pop(NameObject("/Perms"), None)
    writer.root_object.pop(NameObject("/DSS"), None)
    writer.compress_identical_objects(remove_duplicates=False, remove_unreferenced=True)
    output = BytesIO()
    writer.write(output)
    return output.getvalue(), len(writer.pages), count


def unlocked_filename(filename: str) -> str:
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f\x7f]', "_", name).strip().strip(".")
    if name.lower().endswith(".pdf"):
        name = name[:-4]
    return f"{name[:150] or 'document'}_已解锁.pdf"
