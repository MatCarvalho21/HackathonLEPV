import { useState } from 'react';
import { DESTINO_META, DIRECAO, DOMINIOS, HORIZONTE, SITUACAO_META, STATUS, dataDia } from './api.js';

export function Evidencias({ ids = [], legiveis = {} }) {
  if (!ids.length) return null;
  return <span className="pp-evidencias">{ids.map((id) => {
    const e = legiveis[id];
    const tipo = e?.tipo || (id.startsWith('kb:') ? 'fonte' : id.startsWith('ctx:') ? 'relato' : id.startsWith('extra:') ? 'extra' : id.startsWith('reg:') ? 'registro' : 'marco');
    const rot = { marco: 'formulário', relato: 'seu relato', extra: 'resposta extra', fonte: 'fonte', registro: 'registro' }[tipo];
    const dica = e ? `${e.texto}${e.resposta ? ` — resposta: ${e.resposta}` : ''}${e.exemplo ? ` (${e.exemplo})` : ''}` : id;
    return <span key={id} className={`pp-ev pp-ev-${tipo}`} title={dica}>{rot}</span>;
  })}</span>;
}

export function Bolinha({ status }) {
  return <span className="pp-bolinha" style={{ background: STATUS[status]?.cor }} />;
}

export function Semaforo({ dominios, legiveis, compacto = false }) {
  const [aberto, setAberto] = useState(null);
  const d = dominios.find((x) => x.codigo === aberto);
  return <div className={`pp-semaforo ${compacto ? 'compacto' : ''}`}>
    {dominios.map((x) => <button type="button" key={x.codigo} className={`pp-dom ${aberto === x.codigo ? 'aberto' : ''}`}
      style={{ '--c': STATUS[x.status]?.cor }} onClick={() => setAberto(aberto === x.codigo ? null : x.codigo)}>
      <span className="pp-dom-topo"><Bolinha status={x.status} /><b>{DOMINIOS[x.codigo] || x.codigo}</b></span>
      <small>{STATUS[x.status]?.rotulo}</small>
    </button>)}
    {d && <div className="pp-dom-detalhe">
      <h4><Bolinha status={d.status} /> {DOMINIOS[d.codigo]} <small>· {STATUS[d.status]?.rotulo}</small></h4>
      <p>{d.o_que_observamos}</p>
      <p className="pp-just"><b>Por que esta cor:</b> {d.justificativa_status}</p>
      <div className="pp-duas-col">
        <div><h5>Pontos fortes</h5><ul>{d.pontos_fortes.map((e, i) => <li key={i}>{e.texto} <Evidencias ids={e.evidencias} legiveis={legiveis} /></li>)}</ul>{!d.pontos_fortes.length && <small>—</small>}</div>
        <div><h5>Próximos passos</h5><ul>{d.pontos_de_atencao.map((e, i) => <li key={i}>{e.texto} <Evidencias ids={e.evidencias} legiveis={legiveis} /></li>)}</ul>{!d.pontos_de_atencao.length && <small>—</small>}</div>
      </div>
    </div>}
  </div>;
}

export function Gas({ gas, nivelAtual }) {
  const niveis = [['menos_2', -2], ['menos_1', -1], ['zero', 0], ['mais_1', 1], ['mais_2', 2]];
  return <ol className="pp-gas">{niveis.map(([k, n]) => <li key={k} className={`${n === 0 ? 'alvo' : ''} ${nivelAtual === n ? 'atual' : ''}`}>
    <span>{n > 0 ? `+${n}` : n}</span>{gas[k]}</li>)}</ol>;
}

export function Meta({ meta, legiveis, nivelAtual, children }) {
  const [verGas, setVerGas] = useState(false);
  return <article className="pp-meta">
    <div className="pp-meta-topo"><span className="pp-pill">{DOMINIOS[meta.dominio]}</span><span className="pp-pill leve">{meta.prazo_semanas} semanas</span></div>
    <p className="pp-meta-texto">{meta.texto}</p>
    <p className="pp-meta-sub"><b>Como acompanhar:</b> {meta.como_acompanhar}<br /><b>Quem participa:</b> {meta.quem_participa.join(', ')}</p>
    <Evidencias ids={meta.evidencias} legiveis={legiveis} />
    <button type="button" className="pp-link" onClick={() => setVerGas(!verGas)}>{verGas ? 'Esconder' : 'Ver'} escala de progresso</button>
    {verGas && <Gas gas={meta.gas} nivelAtual={nivelAtual} />}
    {children}
  </article>;
}

export function Dica({ dica, legiveis, children }) {
  return <article className="pp-dica">
    <span className="pp-pill">{DOMINIOS[dica.dominio]}</span>{dica.usa_interesse_da_crianca && <span className="pp-pill interesse">usa os interesses</span>}
    <h4>{dica.titulo}</h4>
    <p>{dica.por_que_ajuda}</p>
    <ol>{dica.como_fazer.map((p, i) => <li key={i}>{p}</li>)}</ol>
    <small>⏰ {dica.momento_do_dia}</small>
    {!!dica.fontes.length && <div><Evidencias ids={dica.fontes} legiveis={legiveis} /></div>}
    {children}
  </article>;
}

export function Fontes({ fontes = {} }) {
  const lista = Object.entries(fontes);
  if (!lista.length) return null;
  return <details className="pp-fontes"><summary>Fontes consultadas ({lista.length})</summary>
    <ul>{lista.map(([k, f]) => <li key={k}><code>{k}</code> {f.documento} — <i>{f.secao}</i></li>)}</ul></details>;
}

/** Relatório completo (proposta). No painel, as partes são usadas separadamente. */
export function Relatorio({ av }) {
  const r = av.perfil.relatorio;
  const L = av.evidencias_legiveis || {};
  return <div className="pp-relatorio">
    <section className="pp-bloco destaque">
      <span className="section-kicker">RESUMO</span>
      <p className="pp-resumo">{r.resumo}</p>
      <div className="pp-chips">{r.caracteristicas.map((c) => <span key={c} className="pp-chip">{c}</span>)}</div>
    </section>

    <section className="pp-bloco">
      <span className="section-kicker">O QUE JÁ VAI BEM</span>
      <ul className="pp-fortes">{r.pontos_fortes_gerais.map((p, i) => <li key={i}>✦ {p.texto} <Evidencias ids={p.evidencias} legiveis={L} /></li>)}</ul>
    </section>

    {!!r.alertas.length && <section className="pp-bloco alerta">
      <span className="section-kicker">VALE ATENÇÃO</span>
      {r.alertas.map((a, i) => <div key={i} className="pp-alerta-item"><p>{a.texto}</p><p><b>Sugestão:</b> {a.recomendacao}</p></div>)}
    </section>}

    <section className="pp-bloco">
      <span className="section-kicker">AS 14 ÁREAS · CLIQUE PARA VER DETALHES</span>
      <Semaforo dominios={r.dominios} legiveis={L} />
      <p className="pp-legenda">{Object.entries(STATUS).map(([k, v]) => <span key={k}><Bolinha status={k} /> {v.rotulo}</span>)}</p>
    </section>

    <section className="pp-bloco">
      <span className="section-kicker">ONDE FOCAR AGORA</span>
      <div className="pp-focos">{r.foco_prioritario.map((f, i) => <div key={i} className="pp-foco"><b>{i + 1}. {DOMINIOS[f.dominio]}</b><p>{f.por_que}</p></div>)}</div>
    </section>

    <section className="pp-bloco">
      <span className="section-kicker">METAS</span>
      {['curto', 'medio', 'longo'].map((h) => <div key={h}><h3 className="pp-horizonte">{HORIZONTE[h]}</h3>
        <div className="pp-metas">{r.metas.filter((m) => m.horizonte === h).map((m) => <Meta key={m.id} meta={m} legiveis={L} />)}</div></div>)}
    </section>

    <section className="pp-bloco">
      <span className="section-kicker">DICAS PARA O DIA A DIA</span>
      <div className="pp-dicas">{r.dicas.map((d, i) => <Dica key={i} dica={d} legiveis={L} />)}</div>
    </section>

    <section className="pp-bloco">
      <span className="section-kicker">PRÓXIMOS PASSOS</span>
      <ul>{r.proximos_passos.map((p, i) => <li key={i}>{p}</li>)}</ul>
      <p className="pp-limitacoes"><b>Sobre este mapeamento:</b> {r.limitacoes}</p>
      <Fontes fontes={av.perfil.fontes} />
    </section>
  </div>;
}

const fmt = (n) => (n > 0 ? `+${n}` : `${n}`);

/** Barrinhas com a sequência de níveis GAS (-2 a +2) registrados para uma meta. */
export function NiveisGas({ niveis = [] }) {
  if (!niveis.length) return <small className="pp-sub">nenhum registro de progresso</small>;
  return <span className="pp-progresso">{niveis.slice(-10).map((n, i) => <span key={i} title={`nível ${fmt(n)}`}
    className={`pp-barra n${n + 2}`} style={{ height: `${(n + 3) * 6}px` }} />)}<small>{fmt(niveis[0])} → {fmt(niveis.at(-1))}</small></span>;
}

/** O que mudou desde a avaliação anterior: dados calculados em código + narrativa do agente. */
export function Evolucao({ av, compacto = false }) {
  const cmp = av.perfil.reavaliacao;
  const ev = av.perfil.relatorio.evolucao;
  if (!cmp || !ev) return null;
  const L = av.evidencias_legiveis || {};
  const narrativa = Object.fromEntries((ev.areas || []).map((a) => [a.codigo, a]));
  const mudaram = cmp.areas.filter((a) => a.direcao !== 'igual');
  const conta = (d) => cmp.areas.filter((a) => a.direcao === d).length;
  const balanco = Object.fromEntries((ev.metas_anteriores || []).map((b) => [b.meta_id, b]));
  const r = cmp.registros;

  if (compacto) return <div className="pp-evo-compacta">
    <p className="pp-resumo">{ev.resumo}</p>
    <div className="pp-evo-placar">
      <span className="sobe">↑ {conta('melhorou')} área(s) avançaram</span>
      <span className="igual">= {conta('igual')} estáveis</span>
      {conta('piorou') > 0 && <span className="desce">↓ {conta('piorou')} pedem mais atenção</span>}
      <span>🎯 {cmp.metas.filter((m) => balanco[m.id]?.situacao === 'alcancada').length} de {cmp.metas.length} metas alcançadas</span>
    </div>
  </div>;

  return <div className="pp-relatorio">
    <section className="pp-bloco destaque pp-evolucao">
      <span className="section-kicker">COMO FOI O CAMINHO · {dataDia(cmp.periodo.de)} → {dataDia(cmp.periodo.ate)} ({cmp.periodo.dias} dias)</span>
      <p className="pp-resumo">{ev.resumo}</p>
      <div className="pp-kpis pp-evo-kpis">
        <div><b>{r.total}</b><small>registros no período</small></div>
        <div><b>{r.por_responsavel}</b><small>da família</small></div>
        <div><b>{r.por_professor}</b><small>dos acompanhantes</small></div>
        <div><b>{conta('melhorou')}</b><small>áreas avançaram</small></div>
      </div>
    </section>

    {!!ev.conquistas?.length && <section className="pp-bloco">
      <span className="section-kicker">CONQUISTAS DO PERÍODO</span>
      <ul className="pp-fortes">{ev.conquistas.map((c, i) => <li key={i}>🌟 {c.texto} <Evidencias ids={c.evidencias} legiveis={L} /></li>)}</ul>
    </section>}

    <section className="pp-bloco">
      <span className="section-kicker">AS 14 ÁREAS · ANTES → AGORA</span>
      <div className="pp-comparativo">{cmp.areas.map((a) => {
        const d = DIRECAO[a.direcao];
        return <div key={a.codigo} className={`pp-comp-linha ${a.direcao !== 'igual' ? 'mudou' : ''}`}>
          <span className="pp-comp-nome">{DOMINIOS[a.codigo]}</span>
          <span className="pp-comp-cores"><Bolinha status={a.antes} /><i>→</i><Bolinha status={a.depois} /></span>
          <span className={`pp-dir ${d.classe}`}>{d.seta} {d.rotulo}</span>
          {narrativa[a.codigo] && <p>{narrativa[a.codigo].o_que_mudou} <Evidencias ids={narrativa[a.codigo].evidencias} legiveis={L} /></p>}
        </div>;
      })}</div>
      {!mudaram.length && <p className="pp-sub">Nenhuma área mudou de cor: o retrato se manteve, e o detalhe está nas metas e conquistas.</p>}
    </section>

    <section className="pp-bloco">
      <span className="section-kicker">METAS DA VERSÃO ANTERIOR</span>
      <div className="pp-metas">{cmp.metas.map((m) => {
        const b = balanco[m.id] || {};
        return <article key={m.id} className={`pp-meta pp-balanco ${b.situacao || ''}`}>
          <div className="pp-meta-topo"><span className="pp-pill">{DOMINIOS[m.dominio]}</span><span className="pp-pill leve">{HORIZONTE[m.horizonte]}</span></div>
          <p className="pp-meta-texto">{m.texto}</p>
          <NiveisGas niveis={m.niveis} />
          <p className="pp-meta-sub"><b>{SITUACAO_META[b.situacao] || '—'}</b>{b.destino ? ` · meta ${DESTINO_META[b.destino]}` : ''}<br />{b.comentario}</p>
          <Evidencias ids={b.evidencias} legiveis={L} />
        </article>;
      })}</div>
    </section>

    {(!!ev.o_que_funcionou?.length || !!ev.o_que_nao_funcionou?.length) && <section className="pp-bloco pp-duas-col">
      <div><span className="section-kicker">O QUE FUNCIONOU 👍</span><ul>{(ev.o_que_funcionou || []).map((x, i) => <li key={i}>{x}</li>)}</ul></div>
      <div><span className="section-kicker">O QUE VALE REVER 🔄</span><ul>{(ev.o_que_nao_funcionou || []).map((x, i) => <li key={i}>{x}</li>)}</ul></div>
    </section>}
    {cmp.pedido && <p className="pp-sub">Seu pedido ao solicitar a reavaliação: “{cmp.pedido}”</p>}
  </div>;
}

/** Linha do tempo das cores por área em todas as versões aprovadas do perfil. */
export function EvolucaoVersoes({ avaliacoes }) {
  const aprovadas = avaliacoes.filter((a) => ['vigente', 'substituida'].includes(a.status));
  if (aprovadas.length < 2) return <p className="pp-sub">A evolução entre versões aparece a partir da segunda avaliação aprovada. Peça uma reavaliação quando tiver alguns registros.</p>;
  return <div className="pp-matriz-wrap"><table className="pp-matriz">
    <thead><tr><th>Área</th>{aprovadas.map((a, i) => <th key={a.id}>V{i + 1}<small>{dataDia(a.aceita_em || a.criado_em)}</small></th>)}</tr></thead>
    <tbody>{Object.entries(DOMINIOS).map(([cod, nome]) => <tr key={cod}><td>{nome}</td>
      {aprovadas.map((a, i) => {
        const st = a.niveis?.[cod];
        const mudou = i > 0 && aprovadas[i - 1].niveis?.[cod] !== st;
        return <td key={a.id} className={mudou ? 'mudou' : ''} title={STATUS[st]?.rotulo}><Bolinha status={st} /></td>;
      })}</tr>)}</tbody>
  </table></div>;
}
