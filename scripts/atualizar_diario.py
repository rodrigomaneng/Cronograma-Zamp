#!/usr/bin/env python3
"""
atualizar_diario.py — Pipeline completo de atualização do Cronograma Zamp.

Executa em sequência:
  1. Localiza o CSV mais recente em csv-exports/
  2. Roda processar_csv.py  → scripts/registros_novo.json
  3. Roda montar_index.py   → index.html

Uso:
  python scripts/atualizar_diario.py [caminho_do_csv]

  Se não passar caminho, usa o CSV mais recente em csv-exports/.

Pré-requisito:
  O CSV exportado do pcmbm.zamp.com.br deve estar salvo em csv-exports/
  antes de rodar este script.

Pós-execução (feito por você):
  Abrir github.com/rodrigomaneng/Cronograma-Zamp, editar index.html,
  colar o novo conteúdo e fazer commit.
"""

import os
import sys
import glob
import subprocess
import datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
CSV_DIR = os.path.join(RAIZ, "csv-exports")


def encontrar_csv_mais_recente():
    padrao = os.path.join(CSV_DIR, "*.csv")
    arquivos = [f for f in glob.glob(padrao)
                if not os.path.basename(f).startswith('COLOQUE')]
    if not arquivos:
        return None
    return max(arquivos, key=os.path.getmtime)


def rodar(script, *args):
    cmd = [sys.executable, os.path.join(AQUI, script)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    return result.returncode


def main():
    agora = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    print(f"=== Atualização Cronograma Zamp — {agora} ===\n")

    # 1. Localizar CSV
    csv_path = sys.argv[1] if len(sys.argv) > 1 else encontrar_csv_mais_recente()
    if not csv_path or not os.path.exists(csv_path):
        print(f"ERRO: Nenhum CSV encontrado em {CSV_DIR}/")
        print("      Exporte o CSV do pcmbm.zamp.com.br e salve em csv-exports/")
        sys.exit(1)

    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(csv_path))
    print(f"CSV: {os.path.basename(csv_path)}  (modificado {mtime.strftime('%d/%m %H:%M')})\n")

    # 2. Processar CSV → registros_novo.json
    print("--- Step 1: processar CSV ---")
    rc = rodar("processar_csv.py", csv_path)
    if rc != 0:
        print("\nFALHA no processamento do CSV. Abortando.")
        sys.exit(rc)

    # 3. Montar index.html
    print("\n--- Step 2: montar index.html ---")
    rc = rodar("montar_index.py")
    if rc != 0:
        print("\nFALHA ao montar index.html. Abortando.")
        sys.exit(rc)

    index_path = os.path.join(RAIZ, "index.html")
    tamanho = os.path.getsize(index_path) // 1024
    print(f"\n✓ index.html pronto ({tamanho} KB): {index_path}")
    print("\nPróximo passo (manual):")
    print("  github.com/rodrigomaneng/Cronograma-Zamp → editar index.html → commit")


if __name__ == '__main__':
    main()
