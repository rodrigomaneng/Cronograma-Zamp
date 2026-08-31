#!/usr/bin/env python3
"""
escopo_from_csv.py — Gera scripts/escopo_lojas.json a partir de um CSV
exportado da aba "ESCOPO DE LOJAS" da planilha BASE GERAL - ZAMP.

Colunas esperadas: QTD, LOJA, BKN, CNPJ, REGIONAL, ENDERECO, CONTRATO_MAP, SUPERVISOR

Uso:
  python scripts/escopo_from_csv.py "/caminho/para/ESCOPO DE LOJAS.csv"

Se nenhum caminho for passado, procura o CSV mais recente cujo nome contenha
"ESCOPO DE LOJAS" na pasta Downloads montada.
"""
import csv, json, os, sys, glob

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, "escopo_lojas.json")

MAP = {
    "FRIO": ["Refrigeração"],
    "AR": ["Climatização"],
    "FRIO/AR": ["Refrigeração", "Climatização"],
    "AR/FRIO": ["Refrigeração", "Climatização"],
}


def achar_csv():
    padroes = [
        "/sessions/*/mnt/Downloads/*ESCOPO DE LOJAS*.csv",
        "/sessions/*/mnt/Downloads/*ESCOPO*LOJAS*.csv",
    ]
    cands = []
    for p in padroes:
        cands += glob.glob(p)
    if not cands:
        sys.exit("ERRO: nenhum CSV de ESCOPO DE LOJAS encontrado em Downloads. "
                 "Passe o caminho como argumento.")
    return max(cands, key=os.path.getmtime)


def main():
    caminho = sys.argv[1] if len(sys.argv) > 1 else achar_csv()
    print("Lendo:", caminho)
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = [r for r in reader]
    if not rows:
        sys.exit("ERRO: CSV vazio.")
    header = [h.strip() for h in rows[0]]
    idx = {h: i for i, h in enumerate(header)}
    obrig = ["LOJA", "BKN", "REGIONAL", "ENDERECO", "CONTRATO_MAP", "SUPERVISOR"]
    faltando = [c for c in obrig if c not in idx]
    if faltando:
        sys.exit("ERRO: colunas ausentes no CSV: %s. Header: %s" % (faltando, header))

    def cel(r, k):
        i = idx.get(k)
        return (r[i].strip() if i is not None and i < len(r) else "")

    out = []
    for r in rows[1:]:
        bkn = cel(r, "BKN")
        nome = cel(r, "LOJA")
        if not bkn and not nome:
            continue
        cmap = cel(r, "CONTRATO_MAP")
        cn = cmap.upper().replace(" ", "")
        out.append({
            "bkn": bkn,
            "nome": nome,
            "regional": cel(r, "REGIONAL"),
            "endereco": cel(r, "ENDERECO"),
            "contrato": cmap,
            "escopos": MAP.get(cn, [cmap] if cmap else []),
            "supervisor": cel(r, "SUPERVISOR"),
            "cnpj": cel(r, "CNPJ"),
        })
    # dedup por bkn (mantem primeiro)
    seen, dedup = set(), []
    for l in out:
        if l["bkn"] and l["bkn"] in seen:
            continue
        seen.add(l["bkn"])
        dedup.append(l)
    dedup.sort(key=lambda x: (x["regional"], x["nome"]))
    json.dump(dedup, open(SAIDA, "w", encoding="utf-8"), ensure_ascii=False)
    print("OK: %d unidades -> %s" % (len(dedup), SAIDA))
    sups = sorted(set(l["supervisor"] for l in dedup if l["supervisor"]))
    print("Supervisores (%d): %s" % (len(sups), ", ".join(sups)))


if __name__ == "__main__":
    main()
