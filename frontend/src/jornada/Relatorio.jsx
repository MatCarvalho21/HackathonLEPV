import React, { useState } from 'react';
import { DOMINIOS, HORIZONTE, STATUS } from './api.js';

export function Evidencias({ ids = [], legiveis = {} }) {
  if (!ids.length) return null;
  return <span className="evidencias">{ids.map((id) => {
    const e = legiveis[id];
    const tipo = e?.tipo || (id.startsWith('kb:') ? 'fonte' : id.startsWith('ctx:') ? 'relato' : id.startsWith('extra:') ? 'extra' : 'marco');
    const rot = { marco: 'formulário', relato: 'seu relato', extra: 'resposta extra', fonte: 'fonte' }[tipo];
    const dica = e ? `${e.texto}${e.resposta ? ` — resposta: ${e.resposta}` : ''}${e.exemplo ? ` (${e.exemplo})` : ''}` : id;
    return <span key={id} className={`ev ev-${tipo}`} title={dica}>{rot}</span>;
  })}</span>;
}

export function Bolinha({ status }) {
  return <span className="bolinha" style={{ background: STATUS[status]?.cor }} />;
}

export function Semaforo({ dominios, legiveis, compacto = false }) {
  const [aberto, setAberto] = useState(null);
  return <div className={`semaforo ${compacto ? 'compacto' : ''}`}>
    {dominios.map((d) => <button key={d.codigo} className={`dom ${aberto === d.codigo ? 'aberto' : ''}`}
      style={{ '--c': STATUS[d.status]?.cor }} onClick={() => setAberto(aberto === d.codigo ? null : d.codigo)}>
      <span className="dom-topo"><Bolinha status={d.status} /><b>{DOMINIOS[d.codigo] || d.codigo}</b></span>
      <small>{STATUS[d.status]?.rotulo}</small>
    </button>)}
    {aberto && (() => {
      const d = dominios.find((x) => x.codigo === aberto);
      return <div className="dom-detalhe">
        <h4><Bolinha status={d.status} /> {DOMINIOS[d.codigo]} <small>· {STATUS[d.status]?.rotulo}</small></h4>
        <p>{d.o_que_observamos}</p>
        <p className="just"><b>Por que esta cor:</b> {d.justificativa_status}</p>
        <div className="duas-col">
          <div><h5>Pontos fortes</h5><ul>{d.pontos_fortes.map((e, i) => <li key={i}>{e.texto} <Evidencias ids={e.evidencias} legiveis={legiveis} /></li>)}</ul>{!d.pontos_fortes.length && <small>—</small>}</div>
          <div><h5>Próximos passos</h5><ul>{d.pontos_de_atencao.map((e, i) => <li key={i}>{e.texto} <Evidencias ids={e.evidencias} legiveis={legiveis} /></li>)}</ul>{!d.pontos_de_atencao.length && <small>—</small>}</div>
        </div>
      </div>;
    })()}
  </div>;
}

export function Gas({ gas, nivelAtual }) {
  const niveis = [['menos_2', -2], ['menos_1', -1], ['zero', 0], ['mais_1', 1], ['mais_2', 2]];
  return <ol className="gas">{niveis.map(([k, n]) => <li key={k} className={`${n === 0 ? 'alvo' : ''} ${nivelAtual === n ? 'atual' : ''}`}>
    <span>{n > 0 ? `+${n}` : n}</span>{gas[k]}</li>)}</ol>;
}

export function Meta({ meta, legiveis, nivelAtual, children }) {
  const [verGas, setVerGas] = useState(false);
  return <article className="meta">
    <div className="meta-topo"><span className="pill">{DOMINIOS[meta.dominio]}</span><span className="pill leve">{meta.prazo_semanas} semanas</span></div>
    <p className="meta-texto">{meta.texto}</p>
    <p className="meta-sub"><b>Como acompanhar:</b> {meta.como_acompanhar}<br /><b>Quem participa:</b> {meta.quem_participa.join(', ')}</p>
    <Evidencias ids={meta.evidencias} legiveis={legiveis} />
    <button className="link" onClick={() => setVerGas(!verGas)}>{verGas ? 'Esconder' : 'Ver'} escala de progresso</button>
    {verGas && <Gas gas={meta.gas} nivelAtual={nivelAtual} />}
    {children}
  </article>;
}

export function Dica({ dica, legiveis, children }) {
  return <article className="dica">
    <span className="pill">{DOMINIOS[dica.dominio]}</span>{dica.usa_interesse_da_crianca && <span className="pill interesse">usa os interesses</span>}
    <h4>{dica.titulo}</h4>
    <p>{dica.por_que_ajuda}</p>
    <ol>{dica.como_fazer.map((p, i) => <li key={i}>{p}</li>)}</ol>
    <small>⏰ {dica.momento_do_dia}</small>
    {!!dica.fontes.length && <div><Evidencias ids={dica.fontes} legiveis={legiveis} /></div>}
    {children}
  </article>;
}

/** Relatório completo (proposta). No painel, as partes são usadas separadamente. */
export function Relatorio({ av }) {
  const r = av.perfil.relatorio;
  const L = av.evidencias_legiveis || {};
  return <div className="relatorio">
    <section className="bloco destaque">
      <span className="eyebrow">RESUMO</span>
      <p className="resumo">{r.resumo}</p>
      <div className="chips">{r.caracteristicas.map((c) => <span key={c} className="chip">{c}</span>)}</div>
    </section>

    <section className="bloco">
      <span className="eyebrow">O QUE JÁ VAI BEM</span>
      <ul className="fortes">{r.pontos_fortes_gerais.map((p, i) => <li key={i}>✦ {p.texto} <Evidencias ids={p.evidencias} legiveis={L} /></li>)}</ul>
    </section>

    {!!r.alertas.length && <section className="bloco alerta">
      <span className="eyebrow">VALE ATENÇÃO</span>
      {r.alertas.map((a, i) => <div key={i} className="alerta-item"><p>{a.texto}</p><p><b>Sugestão:</b> {a.recomendacao}</p></div>)}
    </section>}

    <section className="bloco">
      <span className="eyebrow">AS 14 ÁREAS · clique para ver detalhes</span>
      <Semaforo dominios={r.dominios} legiveis={L} />
      <p className="legenda">{Object.entries(STATUS).map(([k, v]) => <span key={k}><Bolinha status={k} /> {v.rotulo}</span>)}</p>
    </section>

    <section className="bloco">
      <span className="eyebrow">ONDE FOCAR AGORA</span>
      <div className="focos">{r.foco_prioritario.map((f, i) => <div key={i} className="foco"><b>{i + 1}. {DOMINIOS[f.dominio]}</b><p>{f.por_que}</p></div>)}</div>
    </section>

    <section className="bloco">
      <span className="eyebrow">METAS</span>
      {['curto', 'medio', 'longo'].map((h) => <div key={h}><h3 className="horizonte">{HORIZONTE[h]}</h3>
        <div className="metas">{r.metas.filter((m) => m.horizonte === h).map((m) => <Meta key={m.id} meta={m} legiveis={L} />)}</div></div>)}
    </section>

    <section className="bloco">
      <span className="eyebrow">DICAS PARA O DIA A DIA</span>
      <div className="dicas">{r.dicas.map((d, i) => <Dica key={i} dica={d} legiveis={L} />)}</div>
    </section>

    <section className="bloco">
      <span className="eyebrow">PRÓXIMOS PASSOS</span>
      <ul>{r.proximos_passos.map((p, i) => <li key={i}>{p}</li>)}</ul>
      <p className="limitacoes"><b>Sobre este mapeamento:</b> {r.limitacoes}</p>
      <Fontes fontes={av.perfil.fontes} />
    </section>
  </div>;
}

export function Fontes({ fontes = {} }) {
  const lista = Object.entries(fontes);
  if (!lista.length) return null;
  return <details className="fontes"><summary>Fontes consultadas ({lista.length})</summary>
    <ul>{lista.map(([k, f]) => <li key={k}><code>{k}</code> {f.documento} — <i>{f.secao}</i></li>)}</ul></details>;
}
