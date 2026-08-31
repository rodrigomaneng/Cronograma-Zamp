# Cronograma Zamp — modo nuvem (roda sem seu computador)

Este setup faz o cronograma atualizar sozinho **nos servidores do GitHub**, a cada
15 minutos, **sem depender do seu computador, do seu Chrome ou do app do Claude**.
Você pode acessar o site de qualquer lugar (celular inclusive) e ele estará sempre
com no máximo ~15 min de defasagem.

## Como funciona
A cada 15 min o GitHub Actions liga uma máquina temporária que:
1. Faz **login headless no PCM BM** (Playwright) e baixa o mesmo CSV do site.
2. (Opcional) Atualiza o escopo de lojas a partir da planilha Google publicada.
3. Roda o pipeline Python de sempre (`processar_csv` → `montar_index`) e gera o `index.html`.
4. Passa por uma **trava de sanidade** (não publica arquivo truncado ou com contagem absurda).
5. Faz `commit` + `push` do `index.html` **só se algo mudou**, usando o token nativo
   do Actions (não precisa de PAT no dia a dia).

Arquivos principais:
- `.github/workflows/atualizar-cronograma.yml` — o agendador na nuvem.
- `scripts/baixar_csv_pcmbm.py` — login + download do CSV (headless).
- `scripts/verificar_sanidade.py`, `scripts/contar_registros.py` — travas/apoio.
- Estado cumulativo: `scripts/arquivados.json`, `scripts/registros_anterior.json`.

## Setup único (você faz uma vez — dá pra fazer do celular)

### 1. Adicionar as credenciais do PCM como *secrets*
No repositório `rodrigomaneng/Cronograma-Zamp`:
**Settings → Secrets and variables → Actions → New repository secret**, crie dois:
- `PCM_EMAIL` = seu e-mail de login do PCM BM
- `PCM_PASSWORD` = sua senha do PCM BM

> As secrets ficam criptografadas no GitHub; nem eu nem ninguém as vê em texto.
> O script nunca imprime a senha nos logs.

### 2. Tornar a planilha de escopo pública (opcional)
Só se quiser que o escopo (aba "Escopo de Contrato") também atualize sozinho na nuvem:
abra a planilha **BASE GERAL - ZAMP** no Google Sheets → **Compartilhar** →
"Qualquer pessoa com o link" = **Leitor**. Se não fizer isso, o escopo é
simplesmente ignorado (não quebra nada) e continua o último escopo publicado.

### 3. Confirmar que o Actions está ligado
Aba **Actions** do repositório. Se aparecer um aviso pedindo para habilitar workflows,
clique em habilitar. (As permissões de escrita já vêm declaradas dentro do workflow.)

## Validar
Aba **Actions → "Atualizar Cronograma Zamp" → Run workflow** (botão) para rodar na
hora, sem esperar os 15 min. Acompanhe o log:
- verde = publicou (ou "sem mudança", se nada mudou desde o último);
- se o passo "Baixar CSV do PCM BM" falhar com "login falhou", revise `PCM_EMAIL`/`PCM_PASSWORD`.

Site: https://rodrigomaneng.github.io/Cronograma-Zamp/ (atualiza ~5 min após o push).

## Ajustar a frequência
No `.github/workflows/atualizar-cronograma.yml`, linha `cron: "*/15 * * * *"`.
Ex.: `"*/10 * * * *"` (10 min) ou `"*/30 * * * *"` (30 min). Horário em UTC.
Obs.: o agendador do GitHub pode atrasar alguns minutos sob carga — é normal.

## Limitações honestas
- **Não é "tempo real" instantâneo.** O menor intervalo prático é o do agendador
  (minutos), porque sempre é preciso fazer login e baixar o CSV — o PCM não expõe
  os dados direto para uma página pública.
- Se você **trocar a senha do PCM**, atualize a secret `PCM_PASSWORD`.
- Se o PCM passar a exigir CAPTCHA/2FA no login, o login headless para de funcionar.
