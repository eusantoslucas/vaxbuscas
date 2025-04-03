import sys
import os

# Adicione o caminho do ambiente virtual
INTERP = "/home/seu-usuario/virtualenv/public_html/3.9/bin/python"
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

sys.path.append(os.getcwd())
from app import app as application