#!/usr/bin/env python3
"""verificar_sanidade.py — trava de seguranca antes de publicar.
Falha (exit 1) se o index.html estiver truncado ou com contagem implausivel.
Uso: python scripts/verificar_sanidade.py [index.html]"""
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
alvo = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "index.html")

html = open(alvo, encoding="utf-8").read()
if "</script>" not in html[-800:]:
    sys.exit("SANIDADE: index.html parece truncado (sem </script> no fim).")
m = re.search(r"let T = (\d+)", html)
n = int(m.group(1)) if m else -1
print("registros (let T):", n)
if not (200 <= n <= 6000):
    sys.exit(f"SANIDADE: contagem fora da faixa esperada (T={n}). Nao publicar.")
print("Sanidade OK.")
