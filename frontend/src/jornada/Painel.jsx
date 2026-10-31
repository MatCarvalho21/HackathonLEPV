import React, { useEffect, useState } from 'react';
import { api, data, DOMINIOS, HORIZONTE, idade } from './api.js';
import { Bolinha, Dica, Evidencias, Fontes, Meta, Semaforo } from './Relatorio.jsx';

const ABAS = [
  ['geral', 'Visão geral'], ['metas', 'Metas'], ['dicas', 'Dicas e estratégias'],
  ['registrar', 'Novo registro'], ['linha', 'Linha do tempo'], ['historico', 'Perfil e versões'],
];

const TIPOS = {
  saude: { rotulo: 'Saúde', icone: '🩺' },
  atividade: { rotulo: 'Atividade', icone: '🧩' },
  comportamento: { rotulo: 'Comportamento', icone: '🌧️' },
  conquista: { rotulo: 'Conquista', icone: '🌟' },
  observacao: { rotulo: 'Observação', icone: '📝' },
  checkin_meta: { rotulo: 'Progresso de meta', icone: '🎯' },
  feedback_estrategia: { rotulo: 'Estratégia testada', icone: '💡' },
  feedback_perfil: { rotulo: 'Comentário sobre o perfil', icone: '💬' },
};
const LOCAIS = [['casa', 'Casa'], ['escola', 'Escola'], ['terapia', 'Terapia'], ['outro', 'Outro']];
const RESULTADOS = [['funcionou', 'Funcionou 👍'], ['parcial', 'Em parte 🤏'], ['nao_funcionou', 'Não funcionou 👎']];

export function Painel({ formularioId }) {
  const [p, setP] = useState(null);
  const [aba, setAba] = useState('geral');
  const [erro, setErro] = useState('');
  const [aviso, setAviso] = useState('');
  const carregar = () => api.painel(formularioId).then(setP).catch((e) => setErro(e.message));
  useEffect(() => { carregar(); }, [formularioId]);

  async function registrar(body) {
    await api.registrar(formularioId, body);
    setAviso(`${TIPOS[body.tipo].icone} ${TIPOS[body.tipo].rotulo} registrado!`);
    setTimeout(() => setAviso(''), 2500);
    await carregar();
  }

  if (erro) return <div className="jornada"><main className="j-main"><div className="error">{erro}</div></main></div>;
  if (!p) return <div className="jornada"><main className="j-main"><p>Carregando…</p></main></div>;
  const av = p.avaliacao_vigente;
  const c = p.crianca;
  if (!av) return <div className="jornada"><main className="j-main"><p>Ainda não há perfil aprovado. <a href="#/">Voltar</a></p></main></div>;
  const r = av.perfil.relatorio;
  const L = av.evidencias_legiveis || {};
  const semana = p.registros.filter((x) => Date.now() - new Date(x.ocorrido_em) < 7 * 864e5).length;

  return <div className="jornada painel">
    <header className="topo"><a href="#/" className="brand"><span className="logo">✳</span> Primeiros Passos</a>
      <span className="tag">Perfil vigente desde {data(av.aceita_em)}</span></header>
    <section className="hero">
      <div className="avatar">{c.apelido[0]}</div>
      <div><h1>{c.apelido}</h1><p>{idade(c.idade_meses)} · acompanhada por {c.vinculo.toLowerCase()}{c.interesses && ` · ama ${c.interesses.toLowerCase()}`}</p></div>
      <div className="kpis">
        <div><b>{r.metas.length}</b><small>metas ativas</small></div>
        <div><b>{semana}</b><small>registros na semana</small></div>
        <div><b>{p.estrategias.reduce((a, e) => a + e.funcionou, 0)}</b><small>estratégias que funcionaram</small></div>
      </div>
    </section>
    <nav className="abas">{ABAS.map(([k, v]) => <button key={k} className={aba === k ? 'ativa' : ''} onClick={() => setAba(k)}>{v}</button>)}</nav>
    {aviso && <div className="toast">{aviso}</div>}
    <main className="j-main largo">
      {aba === 'geral' && <Geral r={r} L={L} p={p} irPara={setAba} />}
      {aba === 'metas' && <Metas r={r} L={L} checkins={p.checkins_metas} registrar={registrar} />}
      {aba === 'dicas' && <Dicas r={r} L={L} estrategias={p.estrategias} registrar={registrar} />}
      {aba === 'registrar' && <Registrar r={r} registrar={registrar} />}
      {aba === 'linha' && <Linha registros={p.registros} r={r} />}
      {aba === 'historico' && <Historico p={p} av={av} />}
    </main>
  </div>;
}

function Geral({ r, L, p, irPara }) {
  return <div className="grade-geral">
    <section className="bloco destaque span2"><span className="eyebrow">RESUMO DO PERFIL</span><p className="resumo">{r.resumo}</p>
      <div className="chips">{r.caracteristicas.map((x) => <span key={x} className="chip">{x}</span>)}</div></section>
    <section className="bloco"><span className="eyebrow">FOCO AGORA</span>
      {r.foco_prioritario.map((f, i) => <div key={i} className="foco"><b>{i + 1}. {DOMINIOS[f.dominio]}</b><p>{f.por_que}</p></div>)}</section>
    <section className="bloco span3"><span className="eyebrow">AS 14 ÁREAS</span><Semaforo dominios={r.dominios} legiveis={L} compacto /></section>
    <section className="bloco span2"><span className="eyebrow">METAS DE CURTO PRAZO</span>
      {r.metas.filter((m) => m.horizonte === 'curto').map((m) => {
        const h = p.checkins_metas[m.id] || [];
        return <div key={m.id} className="mini-meta"><p>{m.texto}</p><Progresso historico={h} /></div>;
      })}
      <button className="link" onClick={() => irPara('metas')}>Registrar progresso →</button></section>
    <section className="bloco"><span className="eyebrow">ÚLTIMOS REGISTROS</span>
      {p.registros.slice(0, 5).map((x) => <p key={x.id} className="mini-reg">{TIPOS[x.tipo].icone} {resumoRegistro(x, r)}<br /><small>{data(x.ocorrido_em)}</small></p>)}
      {!p.registros.length && <p className="sub">Nada ainda. Que tal registrar a primeira conquista?</p>}
      <button className="link" onClick={() => irPara('registrar')}>Novo registro →</button></section>
    {!!r.alertas.length && <section className="bloco alerta span3"><span className="eyebrow">LEMBRETES IMPORTANTES</span>
      {r.alertas.map((a, i) => <p key={i}><b>{a.recomendacao}</b> — {a.texto}</p>)}</section>}
  </div>;
}

function Progresso({ historico }) {
  if (!historico.length) return <small className="sub">Sem registros de progresso ainda.</small>;
  return <div className="progresso">{historico.slice(-10).map((h, i) => <span key={i} title={`${data(h.em)}${h.texto ? ` — ${h.texto}` : ''}`}
    className={`barra n${h.nivel + 2}`} style={{ height: `${(h.nivel + 3) * 7}px` }} />)}
    <small>atual: {fmtNivel(historico.at(-1).nivel)}</small></div>;
}
const fmtNivel = (n) => (n > 0 ? `+${n}` : `${n}`);

function Metas({ r, L, checkins, registrar }) {
  return ['curto', 'medio', 'longo'].map((h) => <section key={h} className="bloco"><h3 className="horizonte">{HORIZONTE[h]}</h3>
    <div className="metas">{r.metas.filter((m) => m.horizonte === h).map((m) => {
      const hist = checkins[m.id] || [];
      return <Meta key={m.id} meta={m} legiveis={L} nivelAtual={hist.at(-1)?.nivel}>
        <Progresso historico={hist} />
        <CheckinMeta meta={m} registrar={registrar} />
      </Meta>;
    })}</div></section>);
}

function CheckinMeta({ meta, registrar }) {
  const [nivel, setNivel] = useState(null);
  const [texto, setTexto] = useState('');
  const [ok, setOk] = useState(false);
  const opcoes = [[-2, meta.gas.menos_2], [-1, meta.gas.menos_1], [0, meta.gas.zero], [1, meta.gas.mais_1], [2, meta.gas.mais_2]];
  async function enviar() {
    await registrar({ tipo: 'checkin_meta', meta_id: meta.id, dados: { nivel_gas: nivel }, texto, dominios: [meta.dominio] });
    setNivel(null); setTexto(''); setOk(true); setTimeout(() => setOk(false), 2000);
  }
  return <div className="checkin"><b>Como está esta semana?</b>
    <div className="niveis">{opcoes.map(([n, desc]) => <button key={n} title={desc} className={nivel === n ? 'sel' : ''} onClick={() => setNivel(n)}>{fmtNivel(n)}</button>)}</div>
    {nivel !== null && <><small>{opcoes.find(([n]) => n === nivel)[1]}</small>
      <input placeholder="Comentário (opcional)" value={texto} onChange={(e) => setTexto(e.target.value)} />
      <button onClick={enviar}>Salvar progresso</button></>}
    {ok && <small className="ok">✓ salvo</small>}
  </div>;
}

function Dicas({ r, L, estrategias, registrar }) {
  return <section className="bloco"><span className="eyebrow">DICAS DO SEU PLANO · conte o que funcionou</span>
    <div className="dicas">{r.dicas.map((d, i) => {
      const stats = estrategias.filter((e) => e.estrategia === d.titulo);
      return <Dica key={i} dica={d} legiveis={L}><FeedbackDica dica={d} stats={stats} registrar={registrar} /></Dica>;
    })}</div></section>;
}

function FeedbackDica({ dica, stats, registrar }) {
  const [local, setLocal] = useState('casa');
  const [texto, setTexto] = useState('');
  const tot = stats.reduce((a, s) => ({ f: a.f + s.funcionou, p: a.p + s.parcial, n: a.n + s.nao_funcionou }), { f: 0, p: 0, n: 0 });
  return <div className="feedback">
    {(tot.f + tot.p + tot.n) > 0 && <small>Já testado: 👍 {tot.f} · 🤏 {tot.p} · 👎 {tot.n}</small>}
    <div className="linha-form">
      <select value={local} onChange={(e) => setLocal(e.target.value)}>{LOCAIS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
      <input placeholder="Como foi? (opcional)" value={texto} onChange={(e) => setTexto(e.target.value)} />
    </div>
    <div className="niveis">{RESULTADOS.map(([v, l]) => <button key={v} onClick={async () => {
      await registrar({ tipo: 'feedback_estrategia', estrategia: dica.titulo, resultado: v, local, texto, dominios: [dica.dominio] }); setTexto('');
    }}>{l}</button>)}</div>
  </div>;
}

function Dominios({ valor, onChange }) {
  return <div className="chips sel">{Object.entries(DOMINIOS).map(([k, v]) => <button type="button" key={k} className={`chip ${valor.includes(k) ? 'on' : ''}`}
    onClick={() => onChange(valor.includes(k) ? valor.filter((x) => x !== k) : [...valor, k])}>{v}</button>)}</div>;
}

const VAZIO = { texto: '', dominios: [], local: 'casa', autor: 'responsavel', quando: '', dados: {}, estrategia: '', resultado: '' };

function Registrar({ r, registrar }) {
  const [tipo, setTipo] = useState('conquista');
  const [f, setF] = useState(VAZIO);
  const [erro, setErro] = useState('');
  const set = (k, v) => setF({ ...f, [k]: v });
  const setD = (k, v) => setF({ ...f, dados: { ...f.dados, [k]: v } });
  async function enviar(e) {
    e.preventDefault(); setErro('');
    const body = { tipo, autor: f.autor, texto: f.texto, dominios: f.dominios, local: tipo === 'saude' ? null : f.local, dados: f.dados,
      ocorrido_em: f.quando ? new Date(f.quando).toISOString() : null };
    if (tipo === 'comportamento' && f.estrategia) { body.estrategia = f.estrategia; body.resultado = f.resultado || null; }
    try { await registrar(body); setF(VAZIO); } catch (x) { setErro(x.message); }
  }
  return <section className="bloco registrar">
    <div className="tipos">{['conquista', 'atividade', 'comportamento', 'saude', 'observacao'].map((t) =>
      <button key={t} className={tipo === t ? 'ativa' : ''} onClick={() => { setTipo(t); setF(VAZIO); }}>{TIPOS[t].icone} {TIPOS[t].rotulo}</button>)}</div>
    <form onSubmit={enviar}>
      {tipo === 'conquista' && <><h3>Uma conquista para celebrar 🌟</h3>
        <label className="field">O que ela conseguiu?<textarea required value={f.texto} onChange={(e) => set('texto', e.target.value)} placeholder='Ex.: "Pediu água falando ÁGUA sem eu mostrar"' /></label></>}

      {tipo === 'atividade' && <><h3>Uma atividade que fizeram juntos</h3>
        <label className="field">O que fizeram?<textarea required value={f.texto} onChange={(e) => set('texto', e.target.value)} placeholder="Ex.: brincadeira de dinossauros narrando as ações" /></label>
        <div className="grid">
          <label className="field">Duração (minutos)<input type="number" min="1" value={f.dados.duracao_min || ''} onChange={(e) => setD('duracao_min', Number(e.target.value))} /></label>
          <label className="field">Quanto de ajuda precisou?<select value={f.dados.nivel_ajuda || ''} onChange={(e) => setD('nivel_ajuda', e.target.value)}>
            <option value="">—</option><option value="sem_ajuda">Fez sozinha</option><option value="pouca">Pouca ajuda</option><option value="muita">Muita ajuda</option></select></label>
          <label className="field">Como ela reagiu?<select value={f.dados.engajamento || ''} onChange={(e) => setD('engajamento', e.target.value)}>
            <option value="">—</option><option value="adorou">Adorou</option><option value="ok">Participou</option><option value="recusou">Não quis</option></select></label>
        </div></>}

      {tipo === 'comportamento' && <><h3>Um momento difícil (registro ABC)</h3>
        <p className="sub">Anotar o que veio antes e depois ajuda a encontrar padrões, sem culpa.</p>
        <label className="field">A · O que aconteceu antes?<input required value={f.dados.antecedente || ''} onChange={(e) => setD('antecedente', e.target.value)} placeholder="Ex.: pedi para desligar o tablet" /></label>
        <label className="field">B · O que ela fez?<input required value={f.dados.comportamento || ''} onChange={(e) => setD('comportamento', e.target.value)} placeholder="Ex.: chorou e jogou o tablet no chão" /></label>
        <label className="field">C · O que aconteceu depois?<input value={f.dados.consequencia || ''} onChange={(e) => setD('consequencia', e.target.value)} placeholder="Ex.: dei colo, cantei, acalmou em 10 min" /></label>
        <div className="grid">
          <label className="field">Intensidade (1 a 5)<input type="range" min="1" max="5" value={f.dados.intensidade || 3} onChange={(e) => setD('intensidade', Number(e.target.value))} /><small>{f.dados.intensidade || 3}</small></label>
          <label className="field">Duração (minutos)<input type="number" min="0" value={f.dados.duracao_min ?? ''} onChange={(e) => setD('duracao_min', Number(e.target.value))} /></label>
          <label className="field">Usou alguma dica do plano?<select value={f.estrategia} onChange={(e) => set('estrategia', e.target.value)}>
            <option value="">Nenhuma</option>{r.dicas.map((d) => <option key={d.titulo}>{d.titulo}</option>)}</select></label>
          {f.estrategia && <label className="field">Funcionou?<select required value={f.resultado} onChange={(e) => set('resultado', e.target.value)}>
            <option value="">—</option>{RESULTADOS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>}
        </div>
        <label className="field">Algo mais?<textarea value={f.texto} onChange={(e) => set('texto', e.target.value)} /></label></>}

      {tipo === 'saude' && <><h3>Registro de saúde 🩺</h3>
        <div className="grid">
          <label className="field">Tipo<select required value={f.dados.categoria || ''} onChange={(e) => setD('categoria', e.target.value)}>
            <option value="">Selecione</option>{['Consulta', 'Exame', 'Medicação', 'Vacina', 'Sono', 'Alimentação', 'Terapia', 'Outro'].map((x) => <option key={x}>{x}</option>)}</select></label>
          <label className="field">Profissional / serviço<input value={f.dados.profissional || ''} onChange={(e) => setD('profissional', e.target.value)} placeholder="Ex.: pediatra da UBS, fonoaudióloga" /></label>
        </div>
        <label className="field">O que foi dito ou observado?<textarea required value={f.texto} onChange={(e) => set('texto', e.target.value)} placeholder="Ex.: pediatra encaminhou para fono e audiometria" /></label>
        <label className="field">Próximo retorno<input type="date" value={f.dados.retorno || ''} onChange={(e) => setD('retorno', e.target.value)} /></label>
        <small className="sub">Não envie laudos ou documentos neste protótipo; registre só o resumo.</small></>}

      {tipo === 'observacao' && <><h3>Uma observação</h3>
        <label className="field">O que você percebeu?<textarea required value={f.texto} onChange={(e) => set('texto', e.target.value)} /></label></>}

      {tipo !== 'saude' && <><label className="field">Áreas relacionadas</label><Dominios valor={f.dominios} onChange={(v) => set('dominios', v)} /></>}
      <div className="grid">
        {tipo !== 'saude' && <label className="field">Onde?<select value={f.local} onChange={(e) => set('local', e.target.value)}>{LOCAIS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>}
        <label className="field">Quando?<input type="datetime-local" value={f.quando} onChange={(e) => set('quando', e.target.value)} /><small>Vazio = agora</small></label>
        <label className="field">Quem registra?<select value={f.autor} onChange={(e) => set('autor', e.target.value)}><option value="responsavel">Responsável</option><option value="professor">Professor(a)</option></select></label>
      </div>
      {erro && <div className="error">{erro}</div>}
      <button>Salvar registro</button>
    </form>
  </section>;
}

function resumoRegistro(x, r) {
  if (x.tipo === 'comportamento') return `${x.dados.antecedente} → ${x.dados.comportamento}${x.dados.consequencia ? ` → ${x.dados.consequencia}` : ''}`;
  if (x.tipo === 'checkin_meta') {
    const m = r.metas.find((mm) => mm.id === x.meta_id);
    return `Meta “${m?.texto.slice(0, 70) || x.meta_id}…”: nível ${fmtNivel(x.dados.nivel_gas)}${x.texto ? ` — ${x.texto}` : ''}`;
  }
  if (x.tipo === 'feedback_estrategia') return `“${x.estrategia}”: ${RESULTADOS.find(([v]) => v === x.resultado)?.[1]}${x.texto ? ` — ${x.texto}` : ''}`;
  if (x.tipo === 'saude') return `${x.dados.categoria || 'Saúde'}${x.dados.profissional ? ` (${x.dados.profissional})` : ''}: ${x.texto}`;
  return x.texto;
}

function Linha({ registros, r }) {
  const [filtro, setFiltro] = useState('');
  const lista = filtro ? registros.filter((x) => x.tipo === filtro) : registros;
  return <section className="bloco">
    <div className="tipos">{[['', 'Todos'], ...Object.entries(TIPOS).map(([k, v]) => [k, `${v.icone} ${v.rotulo}`])].map(([k, v]) =>
      <button key={k} className={filtro === k ? 'ativa' : ''} onClick={() => setFiltro(k)}>{v}</button>)}</div>
    {!lista.length && <p className="sub">Nenhum registro ainda.</p>}
    <ol className="timeline">{lista.map((x) => <li key={x.id}>
      <span className="t-icone">{TIPOS[x.tipo].icone}</span>
      <div><b>{TIPOS[x.tipo].rotulo}</b> <small>· {data(x.ocorrido_em)} · {x.autor === 'professor' ? 'professor(a)' : 'responsável'}{x.local ? ` · ${x.local}` : ''}</small>
        <p>{resumoRegistro(x, r)}</p>
        {!!x.dominios.length && <div className="chips">{x.dominios.map((d) => <span key={d} className="chip mini">{DOMINIOS[d]}</span>)}</div>}
      </div></li>)}</ol>
  </section>;
}

function Historico({ p, av }) {
  const rotulo = { proposta: 'Proposta', vigente: 'Vigente', substituida: 'Substituída', descartada: 'Ajustada' };
  return <>
    <section className="bloco"><span className="eyebrow">VERSÕES DO PERFIL</span>
      <ol className="timeline">{p.avaliacoes.map((a, i) => <li key={a.id}><span className="t-icone">{a.status === 'vigente' ? '✅' : '📄'}</span>
        <div><b>Versão {i + 1} · {rotulo[a.status]}</b> <small>· {data(a.criado_em)}</small>
          {a.comentario_responsavel && <p>Pedido de ajuste: “{a.comentario_responsavel}”</p>}
          <a href={`#/proposta/${a.id}`}>ver esta versão</a></div></li>)}</ol></section>
    <section className="bloco"><span className="eyebrow">PRÓXIMOS PASSOS E LIMITES</span>
      <ul>{av.perfil.relatorio.proximos_passos.map((x, i) => <li key={i}>{x}</li>)}</ul>
      <p className="limitacoes">{av.perfil.relatorio.limitacoes}</p>
      <Fontes fontes={av.perfil.fontes} />
      <p className="sub">Gerado por {av.perfil.gerado_por.modelo} ({av.perfil.gerado_por.agente}). Cores das áreas por idade calculadas por regras; texto, metas e dicas pela IA, revisados por validação automática.</p>
    </section>
  </>;
}

export { Bolinha, Evidencias };
