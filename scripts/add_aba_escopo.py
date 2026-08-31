#!/usr/bin/env python3
"""
add_aba_escopo.py — Adiciona/atualiza a aba "Escopo de Contrato" no base.html.

Fonte dos dados: scripts/escopo_lojas.json (extraido da aba "ESCOPO LOJAS" da
planilha do Drive). Cada unidade: bkn, nome, regional, endereco, contrato,
escopos, supervisor, cnpj.

- Embute os dados como constante ESCOPO_LOJAS no base.html.
- Insere o botao da aba, a secao HTML e o JS de filtro/busca.
- Idempotente: remove a versao anterior (marcadores) antes de reinserir.

Os dados de escopo sao ESTATICOS. O nº de OS e o valor por unidade sao
calculados em tempo de execucao a partir de REGISTROS (dados do PCM).
"""
import json, os, re, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
BASE = os.path.join(RAIZ, "base.html")
FONTE = os.path.join(AQUI, "escopo_lojas.json")

MARK_INI = "<!-- ==ESCOPO_INI== -->"
MARK_FIM = "<!-- ==ESCOPO_FIM== -->"
JS_INI = "/* ==ESCOPO_JS_INI== */"
JS_FIM = "/* ==ESCOPO_JS_FIM== */"


def carregar_escopo():
    if not os.path.exists(FONTE):
        sys.exit("ERRO: %s nao encontrado. Gere-o a partir da aba ESCOPO LOJAS." % FONTE)
    dados = json.load(open(FONTE, encoding="utf-8"))
    for d in dados:
        d["bkn"] = str(d.get("bkn", "")).strip()
        d["nome"] = (d.get("nome") or "").strip()
        d["regional"] = (d.get("regional") or "").strip()
        d["endereco"] = (d.get("endereco") or "").strip()
        d["contrato"] = (d.get("contrato") or "").strip()
        d["supervisor"] = (d.get("supervisor") or "").strip()
        d["escopos"] = d.get("escopos") or []
    dados.sort(key=lambda x: (x["regional"], x["nome"]))
    return dados


def bloco_html():
    return MARK_INI + """
  <!-- ==ABA 5: ESCOPO DE CONTRATO ==================================== -->
  <div class="tab-secao" id="secao-escopo">
  <div class="esc-wrap">

    <div class="esc-toolbar">
      <input id="escBusca" type="text" placeholder="Buscar por BKN, unidade ou endereco...">
      <div class="msel-wrap" id="wrapEscReg"></div>
      <div class="msel-wrap" id="wrapEscEsc"></div>
      <div class="msel-wrap" id="wrapEscSup"></div>
      <button id="escLimpar">&#x2715; Limpar</button>
      <button class="primary" onclick="escExportar()">&#x2B07; Exportar CSV</button>
    </div>

    <div class="esc-kpis">
      <div class="ind-kpi c1"><div class="lbl">Unidades</div><div class="val" id="kEscTot">--</div><div class="sub" id="kEscTotSub">no contrato</div></div>
      <div class="ind-kpi c3"><div class="lbl">Refrigeracao</div><div class="val" id="kEscRef">--</div><div class="sub">unidades</div></div>
      <div class="ind-kpi c2"><div class="lbl">Climatizacao</div><div class="val" id="kEscClim">--</div><div class="sub">unidades</div></div>
    </div>

    <div class="ind-table-box">
      <div class="ind-table-title">Escopo por Unidade <span id="esc-cnt" style="font-weight:400;color:var(--text3)"></span></div>
      <div class="ind-table-wrap" style="max-height:620px">
        <table class="itbl" id="tEscopo">
          <thead><tr>
            <th data-k="bkn">BKN</th>
            <th data-k="nome">Unidade</th>
            <th data-k="regional">Regional</th>
            <th data-k="escopoTxt">Escopo</th>
            <th data-k="endereco">Endereco</th>
            <th data-k="supervisor">Supervisor</th>
          </tr></thead>
          <tbody></tbody>
        </table>
      </div>
    </div>

  </div>
  </div>
""" + MARK_FIM


def bloco_css():
    return """/* ==ESCOPO_CSS== */
.esc-wrap{margin-top:.2rem}
.esc-toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:.85rem}
.esc-toolbar input[type=text]{flex:1;min-width:220px;padding:8px 12px;border:1px solid var(--border);border-radius:8px;font-size:13px;font-family:var(--sans);background:var(--surface);color:var(--text)}
.esc-toolbar button{padding:8px 14px;border:1px solid var(--border);border-radius:8px;background:var(--surface);color:var(--text2);font-size:12px;font-weight:600;cursor:pointer;font-family:var(--sans)}
.esc-toolbar button:hover{background:var(--surface2)}
.esc-toolbar button.primary{background:var(--blue);color:#fff;border-color:var(--blue)}
.esc-chk{display:flex;align-items:center;gap:5px;font-size:12px;color:var(--text2);cursor:pointer;user-select:none}
.esc-kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:.85rem}
@media(max-width:800px){.esc-kpis{grid-template-columns:1fr 1fr}}
.tag-ref{background:#e3f0ff;color:#1a5fb4;border:1px solid #b6d5f5}
.tag-clim{background:#e9f8ee;color:#1a7a3f;border:1px solid #b6e5c6}
.esc-tag{display:inline-block;padding:2px 9px;border-radius:20px;font-size:10px;font-weight:600;margin-right:4px;white-space:nowrap}
.msel-pop{position:absolute;top:calc(100% + 4px);left:0;background:var(--surface);border:1.5px solid var(--border);border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,.12);z-index:1000;min-width:180px;max-height:280px;overflow-y:auto;padding:6px 0}
.msel-pop label{display:flex;align-items:center;gap:8px;padding:7px 14px;cursor:pointer;font-size:13px;color:var(--text)}
.msel-pop label:hover{background:var(--surface2)}
.msel-pop input[type=checkbox]{width:14px;height:14px;accent-color:#7c5cfc;flex-shrink:0}
/* ==/ESCOPO_CSS== */"""


def bloco_js(dados):
    payload = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
    js = JS_INI + """
// ======================================================================
// ABA ESCOPO DE CONTRATO — consulta rapida de unidades
// ESCOPO_LOJAS: dados estaticos (aba ESCOPO LOJAS do Drive).
// OS/Valor: calculados de REGISTROS em tempo de execucao.
// ======================================================================
const ESCOPO_LOJAS = __PAYLOAD__;
(function(){
  var sortEsc={k:'nome',dir:1};

  var LINHAS=ESCOPO_LOJAS.map(function(l){
    return {bkn:l.bkn,nome:l.nome,regional:l.regional,endereco:l.endereco||'',
            supervisor:l.supervisor||'',escopos:l.escopos||[],
            escopoTxt:(l.escopos||[]).join(', ')};
  });

  function makeMsel(wrapId,label,vals,state){
    var wrap=document.getElementById(wrapId); if(!wrap)return;
    var btn=document.createElement('button');
    btn.className='msel-btn'; btn.type='button';
    var pop=document.createElement('div'); pop.className='msel-pop'; pop.style.display='none';
    function render(){
      var n=Object.values(state).filter(Boolean).length;
      btn.textContent=label+(n?(' ('+n+')'):'')+' \u25be';
    }
    vals.forEach(function(v){
      var lb=document.createElement('label');
      lb.innerHTML='<input type="checkbox"> '+v;
      lb.querySelector('input').addEventListener('change',function(e){state[v]=e.target.checked;render();aplicar();});
      pop.appendChild(lb);
    });
    btn.addEventListener('click',function(e){e.stopPropagation();pop.style.display=pop.style.display==='none'?'block':'none';});
    document.addEventListener('click',function(){pop.style.display='none';});
    pop.addEventListener('click',function(e){e.stopPropagation();});
    wrap.appendChild(btn); wrap.appendChild(pop); render();
  }

  var fReg={},fEsc={},fSup={};
  var regs=[...new Set(LINHAS.map(l=>l.regional))].filter(Boolean).sort();
  var escs=[...new Set(LINHAS.flatMap(l=>l.escopos))].filter(Boolean).sort();
  var sups=[...new Set(LINHAS.map(l=>l.supervisor))].filter(Boolean).sort();

  function filtrar(){
    var q=(document.getElementById('escBusca').value||'').trim().toLowerCase();
    var nReg=Object.values(fReg).filter(Boolean).length;
    var nEsc=Object.values(fEsc).filter(Boolean).length;
    var nSup=Object.values(fSup).filter(Boolean).length;
    return LINHAS.filter(function(l){
      if(q&&!((l.bkn+' '+l.nome+' '+l.endereco).toLowerCase().includes(q)))return false;
      if(nReg&&!fReg[l.regional])return false;
      if(nEsc&&!l.escopos.some(e=>fEsc[e]))return false;
      if(nSup&&!fSup[l.supervisor])return false;
      return true;
    });
  }

  function aplicar(){
    var arr=filtrar();
    var s=sortEsc;
    arr.sort(function(a,b){
      var x=(''+a[s.k]).toLowerCase(),y=(''+b[s.k]).toLowerCase();
      return (x<y?-1:x>y?1:0)*s.dir;
    });
    document.getElementById('kEscTot').textContent=arr.length;
    document.getElementById('kEscRef').textContent=arr.filter(l=>l.escopos.includes('Refrigera\u00e7\u00e3o')).length;
    document.getElementById('kEscClim').textContent=arr.filter(l=>l.escopos.includes('Climatiza\u00e7\u00e3o')).length;
    document.getElementById('kEscTotSub').textContent='de '+LINHAS.length+' no contrato';
    document.getElementById('esc-cnt').textContent='('+arr.length+' unidades)';
    var tb=document.querySelector('#tEscopo tbody');
    tb.innerHTML=arr.map(function(l){
      var tags=l.escopos.map(function(e){
        var c=e==='Refrigera\u00e7\u00e3o'?'tag-ref':'tag-clim';
        return '<span class="esc-tag '+c+'">'+e+'</span>';
      }).join('')||'<span style="color:var(--text3)">\u2014</span>';
      return '<tr>'+
        '<td style="font-variant-numeric:tabular-nums">'+l.bkn+'</td>'+
        '<td style="max-width:230px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="'+l.nome+'">'+l.nome+'</td>'+
        '<td>'+(l.regional||'\u2014')+'</td>'+
        '<td>'+tags+'</td>'+
        '<td style="max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="'+l.endereco.replace(/"/g,'&quot;')+'">'+(l.endereco||'\u2014')+'</td>'+
        '<td>'+(l.supervisor||'\u2014')+'</td>'+
      '</tr>';
    }).join('');
  }
  window._escAplicar=aplicar;

  window.escExportar=function(){
    var arr=filtrar();
    var head=['BKN','Unidade','Regional','Escopo','Endereco','Supervisor'];
    var linhas=[head].concat(arr.map(l=>[l.bkn,l.nome,l.regional,l.escopoTxt,l.endereco,l.supervisor]));
    var csv=linhas.map(r=>r.map(c=>'"'+String(c).replace(/"/g,'""')+'"').join(';')).join('\\n');
    var blob=new Blob(['\\ufeff'+csv],{type:'text/csv;charset=utf-8'});
    var a=document.createElement('a');a.href=URL.createObjectURL(blob);
    a.download='escopo_contrato_zamp.csv';a.click();
  };

  function init(){
    if(!document.getElementById('tEscopo'))return;
    makeMsel('wrapEscReg','Regional',regs,fReg);
    makeMsel('wrapEscEsc','Escopo',escs,fEsc);
    makeMsel('wrapEscSup','Supervisor',sups,fSup);
    document.getElementById('escBusca').addEventListener('input',aplicar);
    document.getElementById('escLimpar').addEventListener('click',function(){
      document.getElementById('escBusca').value='';
      [fReg,fEsc,fSup].forEach(function(o){Object.keys(o).forEach(k=>delete o[k]);});
      document.querySelectorAll('#wrapEscReg input,#wrapEscEsc input,#wrapEscSup input').forEach(i=>i.checked=false);
      document.querySelectorAll('#wrapEscReg .msel-btn,#wrapEscEsc .msel-btn,#wrapEscSup .msel-btn').forEach(function(b){
        b.textContent=b.textContent.replace(/\\s\\(\\d+\\)/,'');
      });
      aplicar();
    });
    document.querySelectorAll('#tEscopo thead th').forEach(function(th){
      th.style.cursor='pointer';
      th.addEventListener('click',function(){
        var k=th.getAttribute('data-k'); if(!k)return;
        if(sortEsc.k===k)sortEsc.dir*=-1; else{sortEsc.k=k;sortEsc.dir=1;}
        aplicar();
      });
    });
    aplicar();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);
  else init();
})();
""" + JS_FIM
    return js.replace("__PAYLOAD__", payload)


def limpar_antigo(html):
    html = re.sub(re.escape(MARK_INI) + r".*?" + re.escape(MARK_FIM), "", html, flags=re.S)
    html = re.sub(re.escape(JS_INI) + r".*?" + re.escape(JS_FIM), "", html, flags=re.S)
    html = re.sub(r"/\* ==ESCOPO_CSS== \*/.*?/\* ==/ESCOPO_CSS== \*/", "", html, flags=re.S)
    html = re.sub(r"\s*<button class=\"tab-btn\" onclick=\"mudarAba\('escopo',this\)\">[^<]*</button>", "", html)
    return html


def main():
    dados = carregar_escopo()
    print("Escopo carregado: %d unidades" % len(dados))
    html = open(BASE, encoding="utf-8").read()
    html = limpar_antigo(html)

    alvo_btn = "<button class=\"tab-btn\" onclick=\"mudarAba('indicadores',this)\">\U0001F4CA Indicadores</button>"
    if alvo_btn not in html:
        sys.exit("ERRO: botao 'Indicadores' nao encontrado para ancorar a nova aba.")
    novo_btn = alvo_btn + "\n    <button class=\"tab-btn\" onclick=\"mudarAba('escopo',this)\">\U0001F4CB Escopo de Contrato</button>"
    html = html.replace(alvo_btn, novo_btn, 1)

    fim_style = html.find("</style>")
    if fim_style == -1:
        sys.exit("ERRO: </style> nao encontrado.")
    html = html[:fim_style] + bloco_css() + "\n" + html[fim_style:]

    alvo_main = "</div><!-- /main -->"
    if alvo_main not in html:
        sys.exit("ERRO: marcador '</div><!-- /main -->' nao encontrado.")
    html = html.replace(alvo_main, bloco_html() + "\n\n" + alvo_main, 1)

    idx = html.rfind("</script>")
    if idx == -1:
        sys.exit("ERRO: </script> nao encontrado.")
    html = html[:idx] + "\n" + bloco_js(dados) + "\n" + html[idx:]

    open(BASE, "w", encoding="utf-8").write(html)
    print("OK: base.html atualizado com a aba 'Escopo de Contrato' (%d unidades)." % len(dados))


if __name__ == "__main__":
    main()
