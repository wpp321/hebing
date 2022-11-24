import ast
import random
import string
import chardet
import os
import sys
from gmssl.sm4 import CryptSM4, SM4_ENCRYPT
import base64


def sm4_encrypt(key, text):
    key = key.encode()
    text = text.encode()
    crypt_sm4 = CryptSM4()
    crypt_sm4.set_key(key, SM4_ENCRYPT)
    encrypt_value = crypt_sm4.crypt_ecb(text)
    return (base64.b64encode(encrypt_value)).decode()


TEMPLATE = '''import sys
import types
from gmssl.sm4 import CryptSM4, SM4_DECRYPT
import base64
def sm4_decrypt(key, text):
    key = key.encode()
    text = base64.b64decode(text)
    crypt_sm4 = CryptSM4()
    crypt_sm4.set_key(key, SM4_DECRYPT)
    encrypt_value = crypt_sm4.crypt_ecb(text)
    return encrypt_value.decode()
KEY="{key}"
modules={modules}
class ModImporter:

    def __init__(self, modules):
        self._modules = modules

    def find_module(self, fullname, path):
        if fullname in self._modules.keys():
            return self
        return None

    def load_module(self, fullname):
        code = self.get_code(fullname)
        ispkg = self.is_package(fullname)
        mod = sys.modules.setdefault(fullname, types.ModuleType(fullname))
        mod.__file__ = __file__
        mod.__loader__ = self
        if ispkg:
            mod.__path__ = []
            mod.__package__ = fullname
        else:
            mod.__package__ = fullname.rpartition('.')[0]
        exec(code, mod.__dict__)
        return mod

    def get_code(self, fullname):
        return sm4_decrypt(KEY,self._modules[fullname]["code"])

    def is_package(self, fullname):
        return self._modules[fullname]["is_package"]
sys.meta_path.append(ModImporter(modules=modules))

{code}
'''

KEY = "".join([random.choice(string.ascii_letters + string.digits) for i in range(32)])


def read_file(path):
    with open(path, "rb") as f:
        data = f.read()
    encoding = chardet.detect(data)["encoding"]
    if encoding is None:
        encoding = "utf=8"
    return str(data, encoding=encoding)


def read_file_encrypt(path):
    return sm4_encrypt(KEY, read_file(path))


def is_root_file(file_name):
    return os.path.dirname(os.path.abspath(file_name)) == os.getcwd()


def parse_import(src: str, imports: set):
    parse_tree = ast.parse(src)
    for node in ast.walk(parse_tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                get_imports(name.name, imports)
        if isinstance(node, ast.ImportFrom):
            get_imports(node.module.split('.')[0], imports)


def get_imports(py_name: str, imports: set):
    if os.path.exists(py_name + ".py"):
        py_name = py_name + ".py"
    if py_name.endswith(".py") or os.path.exists(py_name + ".py"):
        py_name = py_name if py_name.endswith(".py") else py_name
        if is_root_file(py_name):
            imports.add(py_name)
        src = read_file(py_name)
        parse_import(src, imports)
    elif os.path.exists(py_name):
        if is_root_file(py_name):
            imports.add(py_name)
        for item in os.walk(py_name):
            if "__pycache__" not in item[0]:
                for doc in item[2]:
                    if doc.endswith(".py"):
                        src = read_file(os.path.join(item[0], doc))
                        parse_import(src, imports)
    else:
        pass


def merge(in_py, out_py):
    imports_set = set()
    get_imports(in_py, imports_set)
    imports_set.remove(in_py)
    modules = {}
    for m in imports_set:
        if m.endswith(".py"):
            modules[m[:-3]] = {
                "code": read_file_encrypt(m),
                "is_package": False
            }
        else:
            for item in os.walk(m):
                if "__pycache__" not in item[0]:
                    mod = item[0].replace(os.sep, ".")
                    for doc in item[2]:
                        if "__init__.py" == doc:
                            modules[mod] = {
                                "code": read_file_encrypt(os.path.join(item[0], doc)),
                                "is_package": True
                            }
                        if "__init__.py" != doc and doc.endswith(".py"):
                            modules[mod + "." + doc[:-3]] = {
                                "code": read_file_encrypt(os.path.join(item[0], doc)),
                                "is_package": False
                            }
                    if "__init__.py" not in item[2]:
                        modules[mod] = {
                            "code": sm4_encrypt(KEY, ""),
                            "is_package": True
                        }
    code = TEMPLATE.format(key=KEY, modules=str(modules), code=read_file(in_py))
    with open(out_py, "w", encoding="utf-8", newline="") as f:
        f.write(code)


def execute():
    merge(sys.argv[1], sys.argv[2])
