#!/usr/bin/env python3
"""
processar_csv.py — Porta do processarCSV() do site Cronograma Zamp.

Diferença importante do JS original: usa o módulo csv do Python para
parsear corretamente campos com quebras de linha internas (descricao_text
tem newlines em quase todos os registros). O JS nativo faz split('\n') antes
de parsear, o que quebra esses registros; esta versão trata todos os 562+.

Lógica replicada:
  - md5Short     (hash djb2, idêntico ao JS inclusive nos overflows Int32)
  - getClienteFromLoja
  - processarCSV (sort por prioridade de status, geração de UID, dedup)

Saída: scripts/registros_novo.json  (lista de objetos com _uid)

Uso:
  python scripts/processar_csv.py [caminho_do_csv]
  Se o caminho não for informado, usa csv-exports/data_export.csv.

Depois rode montar_index.py para costurar no index.html.
"""

import csv
import ctypes
import io
import json
import os
import sys

AQUI  = os.path.dirname(os.path.abspath(__file__))
RAIZ  = os.path.dirname(AQUI)
SAIDA = os.path.join(AQUI, "registros_novo.json")

DEFAULT_CSV = os.path.join(RAIZ, "csv-exports", "data_export.csv")

STATUS_PRIO = {
    'Validado': 1, 'Aprovado': 2, 'Aguardando Validação': 3,
    'Aguardando aprovação Coord.': 4, 'Aguardando Aprovação Capex': 5,
    'Aguardando Aprovação': 6, 'Negado': 7, 'Validação Negada': 8,
    'Invalidado': 9
}


# ── md5Short ────────────────────────────────────────────────────────────────────
def md5_short(s: str) -> str:
    """
    Porta exata do md5Short JS (djb2):
      let h=5381;
      for(let i=0;i<str.length;i++) h=((h<<5)+h)+str.charCodeAt(i);
      return Math.abs(h).toString(36).padStart(8,'0');

    Em JS o operador << faz ToInt32(h) antes de deslocar, então h pode crescer
    (float64) mas é truncado para Int32 a cada iteração no <<.
    """
    h = 5381
    for ch in s:
        # << em JS: converte h para Int32 antes de deslocar
        h_int32   = ctypes.c_int32(int(h)).value
        h_shifted = ctypes.c_int32(h_int32 << 5).value
        # adição normal (sem overflow de 32 bits)
        h = h_shifted + h + ord(ch)

    result = abs(int(h))
    if result == 0:
        return '00000000'
    chars = '0123456789abcdefghijklmnopqrstuvwxyz'
    out = ''
    n = result
    while n > 0:
        out = chars[n % 36] + out
        n //= 36
    return out.rjust(8, '0')


# ── getClienteFromLoja ──────────────────────────────────────────────────────────
def get_cliente_from_loja(loja: str) -> str:
    u = (loja or '').upper()
    if u.startswith('FS ') or u.startswith('FS-') or u.startswith('FS–') or 'FILIAL BK' in u:
        return 'ZAMP-BK'
    multiplan_tokens = ['SHOP', 'DRIVE', 'ROAD SHOP', 'ILS ', 'ILR ', 'FC ',
                        'NORTH SHOP', 'PARK SHOP', 'MAG ', 'MAXI ', 'MAUA']
    if any(t in u for t in multiplan_tokens):
        return 'MULTIPLAN'
    if 'EXTRA' in u or 'CARREFOUR' in u:
        return 'CARREFOUR'
    if 'ASSAI' in u:
        return 'ASSAI'
    if 'KARIM' in u:
        return 'KARIM'
    return 'OUTROS'


# ── processarCSV ────────────────────────────────────────────────────────────────
def processar_csv(text: str) -> list:
    """
    Porta do processarCSV JS, com correção importante:
    usa csv.reader do Python para tratar campos com newlines internas
    (o JS faz split('\\n') antes de parsear, perdendo ~559/562 registros
    cujo campo descricao_text tem quebras de linha).
    UIDs são idênticos ao JS para os campos relevantes (chamado, bkn, loja, mes).
    """
    reader = csv.reader(io.StringIO(text))
    rows   = list(reader)
    if not rows:
        return []

    headers = [h.strip() for h in rows[0]]

    def col(k):
        try:
            return headers.index(k)
        except ValueError:
            return -1

    def get(row, k):
        i = col(k)
        if i < 0 or i >= len(row):
            return ''
        return row[i].strip()

    raw_rows = []
    for row in rows[1:]:
        loja = get(row, 'loja_text')
        if not loja:
            continue
        equip = get(row, 'ativo_name_text')
        if equip in ('nan', 'NaN'):
            equip = ''
        # JS pega só a primeira linha do desc (mesmo que não haja newlines)
        desc = (get(row, 'descricao_text') or '').split('\n')[0].strip()
        desc_full = (get(row, 'descricao_text') or '').strip()
        obs_orc = (get(row, 'obs_orc_text') or '').strip()
        valor_raw = get(row, 'valor_total_number').replace(',', '.')
        try:
            valor = float(valor_raw)
        except (ValueError, TypeError):
            valor = 0.0
        try:
            valor_ma = float(get(row, 'valor_ma_number').replace(',', '.'))
        except (ValueError, TypeError):
            valor_ma = 0.0
        try:
            valor_mo = float(get(row, 'valor_mo_number').replace(',', '.'))
        except (ValueError, TypeError):
            valor_mo = 0.0

        status_text = get(row, 'status_text')
        raw_rows.append({
            'chamado':   get(row, 'chamado_text'),
            'bkn':       get(row, 'bkn_number'),
            'loja':      loja,
            'mes':       get(row, 'month_text'),
            'status':    status_text,
            'regional':  get(row, 'regional_text'),
            'equip':     equip,
            'desc':      desc,
            'desc_full': desc_full,
            'obs_orc':   obs_orc,
            'valor':     valor,
            'valor_ma':  valor_ma,
            'valor_mo':  valor_mo,
            'created':   get(row, 'Created Date'),
            '_prio':     STATUS_PRIO.get(status_text, 99),
        })

    # Sort por prioridade de status (mesma lógica do JS)
    raw_rows.sort(key=lambda r: r['_prio'])

    # Gerar UIDs (com dedup igual ao JS: seen[uid]++ → uid_1, uid_2 …)
    seen = {}
    novos_por_uid = {}
    for r in raw_rows:
        raw_id = r['chamado'] + '__' + r['bkn'] + '__' + r['loja'][:25] + '__' + r['mes']
        uid = 'c' + md5_short(raw_id)
        if uid in seen:
            seen[uid] += 1
            uid = uid + '_' + str(seen[uid])
        else:
            seen[uid] = 0

        novos_por_uid[uid] = {
            '_uid':     uid,
            'chamado':  r['chamado'],
            'bkn':      r['bkn'],
            'unidade':  r['loja'],
            'desc':     r['desc'],
            'desc_full':r['desc_full'],
            'obs_orc':  r['obs_orc'],
            'status':   r['status'],
            'regional': r['regional'],
            'mes':      r['mes'],
            'equip':    r['equip'],
            'valor':    round(r['valor'] * 100) / 100,
            'valor_ma': round(r['valor_ma'] * 100) / 100,
            'valor_mo': round(r['valor_mo'] * 100) / 100,
            'cliente':  get_cliente_from_loja(r['loja']),
            'created':  r['created'],
        }

    # Sort final por created desc (igual ao JS)
    merged = sorted(novos_por_uid.values(),
                    key=lambda r: r['created'], reverse=True)
    return merged


# ── main ────────────────────────────────────────────────────────────────────────
def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV
    if not os.path.exists(csv_path):
        sys.exit(f"ERRO: CSV não encontrado em {csv_path}")

    print(f"Lendo CSV: {csv_path}")
    with open(csv_path, encoding='utf-8') as f:
        text = f.read()

    registros = processar_csv(text)

    if not registros:
        sys.exit("ERRO: nenhum registro gerado. Verifique o CSV.")

    sem_uid = [r for r in registros if not r.get('_uid')]
    if sem_uid:
        sys.exit(f"ERRO: {len(sem_uid)} registros sem _uid. Abortando.")

    with open(SAIDA, 'w', encoding='utf-8') as f:
        json.dump(registros, f, ensure_ascii=False, separators=(',', ':'))

    total_val = sum(r.get('valor', 0) for r in registros)
    print(f"OK: {len(registros)} registros gerados.")
    print(f"   Valor total: R$ {total_val:,.2f}")
    print(f"   Arquivo: {SAIDA}")
    print("Próximo passo: python scripts/montar_index.py")


if __name__ == '__main__':
    main()
