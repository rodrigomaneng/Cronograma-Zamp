#!/usr/bin/env python3
"""contar_registros.py — imprime o numero de registros (let T = N) do index.html.
Uso: python scripts/contar_registros.py [index.html]  (default: index.html na raiz)"""
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
alvo = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "index.html")
try:
    html = open(alvo, encoding="utf-8").read()
    m = re.search(r"let T = (\d+)", html)
    print(m.group(1) if m else "?")
except Exception:
    print("?")
