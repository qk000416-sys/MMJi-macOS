import sys,io,subprocess,json,hashlib,os
from pathlib import Path
resources=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(resources))
from pypdf import PdfWriter,PdfReader
from pypdf.generic import NameObject,DictionaryObject,ArrayObject,NumberObject,DecodedStreamObject,TextStringObject
python=resources/'Python.framework/Versions/3.13/bin/python3.13'
import tempfile
_temp = tempfile.TemporaryDirectory(prefix='mm-tests-')
folder=Path(_temp.name)
for algorithm,password in [('AES-256',''),('AES-256','test-open'),('RC4-128',''),(None,'')]:
 w=PdfWriter();w.add_blank_page(200,300)
 if algorithm:w.encrypt(password,owner_password='test-owner',algorithm=algorithm)
 p=folder/((algorithm or 'plain')+('-password' if password else '')+'.pdf');w.write(p)
 before=hashlib.sha256(p.read_bytes()).hexdigest()
 if password:
  r=subprocess.run([str(python),str(resources/'worker.py'),str(p.resolve())],input=json.dumps({'password':'wrong'}),text=True,capture_output=True)
  assert r.returncode==1 and 'password_incorrect' in r.stdout,(r.stdout,r.stderr)
  assert before==hashlib.sha256(p.read_bytes()).hexdigest()
 r=subprocess.run([str(python),str(resources/'worker.py'),str(p.resolve())],input=json.dumps({'password':password}),text=True,capture_output=True)
 assert r.returncode==0,(r.stdout,r.stderr)
 reader=PdfReader(p);assert not reader.is_encrypted and len(reader.pages)==1
 print('PASS',p.name,'wrong password keeps original' if password else '')
w=PdfWriter();page=w.add_blank_page(200,300)
ap=DecodedStreamObject();ap.set_data(b'1 0 0 rg 0 0 80 30 re f');ap.update({NameObject('/Type'):NameObject('/XObject'),NameObject('/Subtype'):NameObject('/Form'),NameObject('/BBox'):ArrayObject([NumberObject(x) for x in [0,0,80,30]])})
sig=DictionaryObject({NameObject('/Type'):NameObject('/Annot'),NameObject('/Subtype'):NameObject('/Widget'),NameObject('/FT'):NameObject('/Sig'),NameObject('/T'):TextStringObject('TestSignature'),NameObject('/Rect'):ArrayObject([NumberObject(x) for x in [10,10,90,40]]),NameObject('/AP'):DictionaryObject({NameObject('/N'):w._add_object(ap)})})
ref=w._add_object(sig);page[NameObject('/Annots')]=ArrayObject([ref]);w.root_object[NameObject('/AcroForm')]=DictionaryObject({NameObject('/Fields'):ArrayObject([ref])})
p=folder/'signature.pdf';w.write(p)
r=subprocess.run([str(python),str(resources/'worker.py'),str(p.resolve())],input='{}',text=True,capture_output=True)
assert r.returncode==0,(r.stdout,r.stderr)
pdf=PdfReader(p);assert '/AcroForm' not in pdf.trailer['/Root'];assert '/UnlockedSignature0' in pdf.pages[0]['/Resources']['/XObject']
print('PASS signature appearance preserved in page content')
print('All worker tests passed on',os.uname().machine)
# Metadata-only updates must not be mistaken for content edits.
import worker
real_unlock = worker.unlock_pdf
p = folder/'metadata-change.pdf'
w = PdfWriter(); w.add_blank_page(100,100); w.write(p)
def metadata_update(data, password):
    subprocess.run(['xattr','-w','com.example.mm-test','value',str(p)],check=True)
    return real_unlock(data,password)
worker.unlock_pdf = metadata_update
worker.replace_pdf(p)
assert not PdfReader(p).is_encrypted
print('PASS metadata-only update is accepted')
p = folder/'content-change.pdf'; w.write(p)
changed = None
def content_update(data,password):
    global changed
    changed = data + b'\n% concurrent editor\n'; p.write_bytes(changed)
    return real_unlock(data,password)
worker.unlock_pdf = content_update
try:
    worker.replace_pdf(p)
except ValueError as exc:
    assert '发生变化' in str(exc)
else:
    raise AssertionError('Concurrent content edit should be rejected')
assert p.read_bytes() == changed
worker.unlock_pdf = real_unlock
print('PASS concurrent content edit is preserved')
