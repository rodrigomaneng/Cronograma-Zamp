#!/usr/bin/env python3
"""
montar_index.py — Costura o array REGISTROS atualizado dentro do index.html.

Fluxo:
  1. Garante uma base do index.html (baixa do GitHub se nao existir local).
  2. Le scripts/registros_novo.json (exportado do site via navegador).
  3. Substitui o bloco `let REGISTROS = [ ... ];` pela nova lista.
  4. Salva index.html pronto para subir no GitHub.

NUNCA recalcula UID. A lista de registros vem pronta da funcao processarCSV
do proprio site (ver scripts/atualizar_via_navegador.md).

Uso:
  python scripts/montar_index.py
"""
import json, os, re, sys, subprocess

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
BASE = os.path.join(RAIZ, "base.html")
SAIDA = os.path.join(RAIZ, "index.html")
REGISTROS_JSON = os.path.join(AQUI, "registros_novo.json")
RAW_URL = "https://raw.githubusercontent.com/rodrigomaneng/Cronograma-Zamp/main/index.html"


def garantir_base():
    if os.path.exists(BASE):
        return
    print("base.html nao encontrado; baixando do GitHub...")
    rc = subprocess.run(["curl", "-s", RAW_URL, "-o", BASE]).returncode
    if rc != 0 or not os.path.exists(BASE) or os.path.getsize(BASE) == 0:
        sys.exit("ERRO: nao consegui baixar base.html. Baixe manualmente:\n  curl -s '%s' -o base.html" % RAW_URL)


def carregar_registros():
    if not os.path.exists(REGISTROS_JSON):
        sys.exit("ERRO: %s nao existe. Exporte JSON.stringify(REGISTROS) do site primeiro "
                 "(ver scripts/atualizar_via_navegador.md)." % REGISTROS_JSON)
    with open(REGISTROS_JSON, encoding="utf-8") as f:
        dados = json.load(f)
    if not isinstance(dados, list) or not dados:
        sys.exit("ERRO: registros_novo.json esta vazio ou nao e uma lista.")
    # validacao basica: cada item precisa de _uid
    sem_uid = [d for d in dados if not d.get("_uid")]
    if sem_uid:
        sys.exit("ERRO: %d registros sem _uid. Abortando para nao quebrar o casamento de estado." % len(sem_uid))
    return dados


def costurar(html, registros):
    payload = json.dumps(registros, ensure_ascii=False, separators=(",", ":"))
    # localizar a ATRIBUICAO `let REGISTROS = [` (a 1a ocorrencia que e seguida de '[')
    m = None
    for cand in re.finditer(r"let\s+REGISTROS\s*=\s*", html):
        if html[cand.end():cand.end() + 1] == "[":
            m = cand
            break
    if not m:
        sys.exit("ERRO: atribuicao 'let REGISTROS = [' nao encontrada no base.html.")
    inicio = m.start()
    open_bracket = html.index("[", m.end() - 1)

    # achar o ] que fecha o array, respeitando colchetes/strings aninhados
    depth = 0
    in_str = False
    quote = ""
    esc = False
    fim_bracket = -1
    i = open_bracket
    while i < len(html):
        ch = html[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == quote:
                in_str = False
        else:
            if ch in ('"', "'"):
                in_str = True
                quote = ch
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    fim_bracket = i
                    break
        i += 1

    if fim_bracket == -1:
        sys.exit("ERRO: fim do array REGISTROS (']') nao encontrado por balanceamento.")

    # apos o ] deve vir um ';' — preserva-lo
    resto = html[fim_bracket + 1:]
    novo_html = html[:inicio] + "let REGISTROS = " + payload + resto
    return novo_html


def marcar_arquivado(r):
    a = dict(r)
    if a.get("status") != "Fora do PCM":
        a["status_pcm_original"] = a.get("status", "")
        df = a.get("desc_full") or a.get("desc") or ""
        a["desc_full"] = df + "\n\n[Card fora do export do PCM — ultimo status: " + a["status_pcm_original"] + "]"
        a["status"] = "Fora do PCM"
    a["arquivado"] = True
    return a


def carregar_arquivados(registros):
    """Modo cumulativo: nenhum card e excluido do site.

    - arquivados.json guarda todos os cards que ja sairam do export do PCM.
    - registros_anterior.json e o export da execucao anterior; cards que
      estavam la e nao vieram no export de hoje sao arquivados agora.
    - Se um card arquivado voltar ao export, a versao nova (do CSV) assume.
    """
    arq_path = os.path.join(AQUI, "arquivados.json")
    ant_path = os.path.join(AQUI, "registros_anterior.json")
    arquivados = []
    if os.path.exists(arq_path):
        with open(arq_path, encoding="utf-8") as f:
            arquivados = json.load(f)
    atuais = {(r.get("chamado"), r.get("bkn")) for r in registros}
    arq_keys = {(a.get("chamado"), a.get("bkn")) for a in arquivados}
    # cards do export anterior que sumiram do export de hoje -> arquivar
    if os.path.exists(ant_path):
        with open(ant_path, encoding="utf-8") as f:
            anteriores = json.load(f)
        novos_arq = [marcar_arquivado(r) for r in anteriores
                     if (r.get("chamado"), r.get("bkn")) not in atuais
                     and (r.get("chamado"), r.get("bkn")) not in arq_keys]
        if novos_arq:
            print("  + %d cards arquivados nesta execucao (sairam do export)" % len(novos_arq))
            arquivados = arquivados + novos_arq
            with open(arq_path, "w", encoding="utf-8") as f:
                json.dump(arquivados, f, ensure_ascii=False)
    # devolver so os que continuam fora do export atual (sem duplicar uid)
    uids = {r["_uid"] for r in registros}
    return [a for a in arquivados
            if (a.get("chamado"), a.get("bkn")) not in atuais
            and a.get("_uid") not in uids]


def salvar_snapshot(registros_export):
    """Guarda o export de hoje para comparacao na proxima execucao."""
    with open(os.path.join(AQUI, "registros_anterior.json"), "w", encoding="utf-8") as f:
        json.dump(registros_export, f, ensure_ascii=False)


def main():
    garantir_base()
    registros = carregar_registros()
    registros_export = list(registros)
    arquivados = carregar_arquivados(registros)
    if arquivados:
        print("  + %d cards preservados (fora do export do PCM)" % len(arquivados))
        registros = registros + arquivados
    salvar_snapshot(registros_export)
    with open(BASE, encoding="utf-8") as f:
        html = f.read()
    novo = costurar(html, registros)
    # atualizar contador hardcoded "let T = NNN" (KPI TOTAL / cabecalho)
    novo = re.sub(r"let T = \d+", "let T = %d" % len(registros), novo)
    # sanidade: o arquivo precisa terminar com </script> (detecta truncamento)
    if "</script>" not in novo[-500:]:
        sys.exit("ERRO: base.html parece truncado (nao termina com </script>). "
                 "Restaure o base.html antes de gerar o index.")
    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write(novo)
    total = sum(r.get("valor", 0) for r in registros)
    print("OK: index.html gerado.")
    print("  registros: %d" % len(registros))
    print("  valor total: R$ %.2f" % total)
    print("  arquivo: %s" % SAIDA)
    print("Proximo passo: subir index.html no GitHub (substituindo o atual).")


if __name__ == "__main__":
    main()
