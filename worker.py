"""Validate the complete output before atomically replacing the selected PDF."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import io
import ctypes
import json
import os
import stat
import tempfile
from pypdf import PdfReader
from pdf_unlock import unlock_pdf, PdfUnlockError, MAX_PDF_BYTES


def replace_pdf(path, password=''):
    path = Path(path)
    if path.is_symlink() or path.suffix.lower() != '.pdf':
        raise ValueError('请选择 PDF 原文件，不支持符号链接。')
    with path.open('rb') as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_PDF_BYTES:
            raise ValueError('请选择不超过 50 MB 的 PDF 文件。')
        original = source.read(MAX_PDF_BYTES + 1)
    output, pages, _ = unlock_pdf(original, password)
    check = PdfReader(io.BytesIO(output))
    if check.is_encrypted or len(check.pages) != pages or '/Perms' in check.trailer['/Root']:
        raise ValueError('处理结果校验失败，原文件未被替换。')
    temporary = None
    try:
        fd, temporary = tempfile.mkstemp(prefix='.pdf-unlock-', suffix='.tmp', dir=path.parent)
        with os.fdopen(fd, 'wb') as target:
            target.write(output)
            target.flush()
            os.fsync(target.fileno())
            os.fchmod(target.fileno(), stat.S_IMODE(before.st_mode))
        # Preserve Finder tags and other extended attributes where possible.
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.copyfile(os.fsencode(path), os.fsencode(temporary), None, 1 << 2) != 0:
            raise OSError(ctypes.get_errno(), "无法保留文件属性，已取消替换。")
        current = path.lstat()
        # macOS can update access/provenance xattrs while the app reads a file.
        # ctime includes those metadata changes; verify the actual bytes instead.
        if (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) or path.read_bytes() != original:
            raise ValueError('文件在处理期间发生变化，已取消替换，请重试。')
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            os.unlink(temporary)


if __name__ == '__main__':
    try:
        password = json.load(sys.stdin).get('password', '')
        replace_pdf(sys.argv[1], password)
        print(json.dumps({'ok': True}))
    except Exception as exc:
        print(json.dumps({'error': str(exc), 'code': getattr(exc, 'code', 'error')}, ensure_ascii=False))
        sys.exit(1)
