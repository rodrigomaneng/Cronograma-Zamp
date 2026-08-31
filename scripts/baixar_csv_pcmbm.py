#!/usr/bin/env python3
"""
baixar_csv_pcmbm.py — Login headless no PCM BM (Bubble) e download do CSV de
orcamentos da Maneng, para rodar 100% na nuvem (GitHub Actions), SEM o Chrome
do Rodrigo e SEM o computador dele ligado.

Reproduz EXATAMENTE o fluxo manual (mesmo CSV, mesma contagem do board):
  1. Abre https://pcmbm.zamp.com.br/ (tela de login Bubble).
  2. Preenche e-mail/senha (vindos das secrets PCM_EMAIL / PCM_PASSWORD) e
     clica em "Entrar".
  3. Vai para /fornecedor e espera o board carregar.
  4. Instala o interceptor de URL.createObjectURL e aciona o botao de download
     (icone fa-arrow-circle-down), com retentativas (o blob leva 1-2 cliques).
  5. Le o blob CSV via Blob.text() e grava em csv-exports/data_export_AAAAMMDD.csv.

Nunca imprime a senha. Uso:
  python scripts/baixar_csv_pcmbm.py [saida.csv]
Requer: pip install playwright && playwright install chromium
"""
import datetime
import os
import sys

from playwright.sync_api import sync_playwright

BASE = "https://pcmbm.zamp.com.br"
EMAIL = (os.environ.get("PCM_EMAIL") or "").strip()
SENHA = (os.environ.get("PCM_PASSWORD") or "").strip()

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
CSV_DIR = os.path.join(RAIZ, "csv-exports")

INTERCEPTOR = """
window._csvReady = false;
window._csvBlob = null;
(function(){
  const orig = URL.createObjectURL;
  URL.createObjectURL = function(b){
    try { if (b && b.type && String(b.type).includes('csv')) { window._csvBlob = b; window._csvReady = true; } } catch(e){}
    return orig.call(URL, b);
  };
})();
"""

CLICAR = """() => {
  const b = [...document.querySelectorAll('.fa-arrow-circle-down')]
    .find(e => e.getBoundingClientRect().width > 0);
  if (b) { b.click(); return true; }
  return false;
}"""


def log(msg):
    print(msg, flush=True)


def main():
    if not EMAIL or not SENHA:
        sys.exit("ERRO: defina as secrets PCM_EMAIL e PCM_PASSWORD.")

    saida = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        CSV_DIR, "data_export_" + datetime.date.today().strftime("%Y%m%d") + ".csv")
    os.makedirs(os.path.dirname(saida), exist_ok=True)

    csv_text = None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        log("Abrindo tela de login...")
        page.goto(BASE + "/", wait_until="networkidle", timeout=60000)

        page.wait_for_selector("input[type=email]", timeout=45000)
        page.fill("input[type=email]", EMAIL)
        page.fill("input[type=password]", SENHA)

        # Botao "Entrar" (Bubble usa classes dinamicas; casar pelo texto e' estavel)
        clicked = False
        for sel in ["button:has-text('Entrar')", "text=Entrar"]:
            try:
                page.click(sel, timeout=8000)
                clicked = True
                break
            except Exception:
                continue
        if not clicked:
            page.keyboard.press("Enter")

        log("Login enviado; aguardando board...")
        # O login redireciona para o board (SPA). Forcamos /fornecedor por garantia.
        try:
            page.wait_for_selector(".fa-arrow-circle-down", timeout=30000)
        except Exception:
            pass
        page.goto(BASE + "/fornecedor", wait_until="networkidle", timeout=60000)

        # Se caiu de volta no login, as credenciais falharam.
        if page.query_selector("input[type=password]") and not page.query_selector(".fa-arrow-circle-down"):
            browser.close()
            sys.exit("ERRO: login falhou (voltou para a tela de senha). Verifique PCM_EMAIL/PCM_PASSWORD.")

        page.wait_for_selector(".fa-arrow-circle-down", timeout=60000)
        page.evaluate(INTERCEPTOR)

        for tentativa in range(1, 6):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.evaluate(CLICAR)
            page.wait_for_timeout(5000)
            if page.evaluate("window._csvReady === true"):
                csv_text = page.evaluate("async () => await window._csvBlob.text()")
                log(f"CSV capturado na tentativa {tentativa}.")
                break
            log(f"tentativa {tentativa}: blob ainda nao pronto, repetindo...")

        browser.close()

    if not csv_text:
        sys.exit("ERRO: CSV nao capturado apos varias tentativas (board pode nao ter carregado).")

    with open(saida, "w", encoding="utf-8", newline="") as f:
        f.write(csv_text)
    linhas = csv_text.count("\n")
    log(f"OK: CSV salvo em {saida} ({linhas} linhas, {len(csv_text)} bytes)")
    if linhas < 50:
        sys.exit(f"ERRO: CSV suspeito (apenas {linhas} linhas). Abortando para nao publicar lixo.")


if __name__ == "__main__":
    main()
