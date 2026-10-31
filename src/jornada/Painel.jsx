import { useEffect, useState } from 'react';
import { ArrowLeft, CircleCheck, ClipboardList, Download, FileText, RefreshCw, School, Sparkles, UserPlus } from 'lucide-react';
import { api, dataCurta, dataDia, DOMINIOS, HORIZONTE, idade, mesesDesde, rotuloFuncao } from './api.js';
import { Canal } from './Canal.jsx';
import { Dica, Evolucao, EvolucaoVersoes, Fontes, Meta, Semaforo } from './Relatorio.jsx';
import { Chat } from './Chat.jsx';
import { IconeResultado, IconeTipo } from './icones.jsx';

const ABAS = [
  ['geral', 'Visão geral'], ['metas', 'Metas'], ['dicas', 'Dicas e estratégias'], ['registrar', 'Novo registro'],
  ['linha', 'Linha do tempo'], ['chat', 'Assistente (IA)'], ['canal', 'Canal da equipe'], ['historico', 'Perfil e versões'],
];

export const TIPOS = {
  saude: { rotulo: 'Saúde' },
  atividade: { rotulo: 'Atividade' },
  comportamento: { rotulo: 'Comportamento' },
  conquista: { rotulo: 'Conquista' },
  observacao: { rotulo: 'Observação' },
  checkin_meta: { rotulo: 'Progresso de meta' },
  feedback_estrategia: { rotulo: 'Estratégia testada' },
  feedback_perfil: { rotulo: 'Comentário sobre o perfil' },
};
const LOCAIS = [['casa', 'Casa'], ['escola', 'Escola'], ['terapia', 'Terapia'], ['outro', 'Outro']];
const RESULTADOS = [['funcionou', 'Funcionou'], ['parcial', 'Em parte'], ['nao_funcionou', 'Não funcionou']];
const fmtNivel = (n) => (n > 0 ? `+${n}` : `${n}`);

export function resumoRegistro(x, metas = []) {
  const d = x.dados || {};
  if (x.tipo === 'comportamento') return [d.antecedente, d.comportamento, d.consequencia].filter(Boolean).join(' → ') + (x.texto ? ` — ${x.texto}` : '');
  if (x.tipo === 'checkin_meta') {
    const m = metas.find((mm) => mm.id === x.meta_id);
    return `Meta “${m ? `${m.texto.slice(0, 70)}…` : x.meta_id}”: nível ${fmtNivel(d.nivel_gas)}${x.texto ? ` — ${x.texto}` : ''}`;
  }
  if (x.tipo === 'feedback_estrategia') return `“${x.estrategia}”: ${RESULTADOS.find(([v]) => v === x.resultado)?.[1]}${x.texto ? ` — ${x.texto}` : ''}`;
  if (x.tipo === 'saude') return `${d.categoria || 'Saúde'}${d.profissional ? ` (${d.profissional})` : ''}: ${x.texto || ''}`;
  if (x.tipo === 'observacao' && d.activity) return `${d.activity}: ${x.texto}`;
  return x.texto;
}

export function Painel({ criancaId, sessao, abaInicial = 'geral', onVoltar, onAviso, onVerVersao, onReavaliacao, onAtualizarFormulario, onBaixarResumo, onCompartilhar }) {
  const [p, setP] = useState(null);
  const [aba, setAba] = useState(abaInicial);
  const [erro, setErro] = useState('');
  const carregar = () => api.painel(criancaId).then(setP).catch((e) => setErro(e.message));
  useEffect(() => { carregar(); }, [criancaId]);
  useEffect(() => { setAba(abaInicial); }, [abaInicial]);

  async function registrar(body) {
    await api.registrar(criancaId, body); // o autor vem do login
    onAviso?.(`${TIPOS[body.tipo].rotulo} registrado.`);
    await carregar();
  }

  if (erro) return <div className="page-wrap pp"><div className="questionnaire-error">{erro}</div></div>;
  if (!p) return <div className="page-wrap pp"><p>Carregando…</p></div>;
  const av = p.avaliacao_vigente;
  const c = p.crianca;
  if (!av) return <div className="page-wrap pp"><p>Ainda não há perfil aprovado.</p></div>;
  const r = av.perfil.relatorio;
  const L = av.evidencias_legiveis || {};
  const semana = p.registros.filter((x) => Date.now() - new Date(x.ocorrido_em) < 7 * 864e5).length;
  const meses = mesesDesde(c.data_nascimento) ?? p.perfil_formulario?.idade_meses;
  const professor = p.meu_papel === 'professor'; // acompanhante (papel interno "professor")
  const versao = p.avaliacoes.filter((a) => ['vigente', 'substituida'].includes(a.status)).length;
  const desdeVigente = p.registros.filter((x) => x.ocorrido_em >= av.aceita_em || x.criado_em >= av.aceita_em).length;
  const reav = p.estado.reavaliacao;
  const reavProps = { criancaId, av, reav, desdeVigente, professor, onReavaliacao, onAtualizarFormulario, onAviso };

  return <div className="page-wrap pp pp-painel">
    <button className="back-link" onClick={onVoltar}><ArrowLeft size={16} /> Voltar à visão geral</button>
    <section className="pp-cabecalho">
      <span className="child-avatar large">{c.nome[0]}</span>
      <div><span className="section-kicker">PLANO EM ACOMPANHAMENTO · VERSÃO {versao} · DESDE {dataCurta(av.aceita_em).slice(0, 5)}</span>
        <h1>{c.nome}</h1><p>{meses != null ? idade(meses) : ''}{c.interesses?.length ? ` · gosta de ${c.interesses.join(', ')}` : ''}</p></div>
      <div className="pp-kpis">
        <div><b>{r.metas.length}</b><small>metas ativas</small></div>
        <div><b>{semana}</b><small>registros na semana</small></div>
        <div><b>{p.estrategias.reduce((a, e) => a + e.funcionou, 0)}</b><small>estratégias que funcionaram</small></div>
      </div>
      <div className="pp-cabecalho-acoes">
        <button className="btn-secondary" onClick={onBaixarResumo}><Download size={16} /> Resumo em PDF</button>
        {!professor && <button className="btn-secondary" onClick={onCompartilhar}><UserPlus size={16} /> Compartilhar</button>}
      </div>
    </section>
    {professor && <div className="teacher-banner pp-modo-prof"><div className="banner-symbol"><School size={20} /></div><div><b>Você está como acompanhante</b>
      <p>Você lê o perfil, registra o que observa (atividades, comportamentos, conquistas, observações e estratégias testadas), fala com a família no canal e conversa com o assistente. O perfil, as metas e o progresso das metas ficam com a família, e seus registros entram na próxima reavaliação.</p></div></div>}
    <AvisoReavaliacao {...reavProps} />
    <nav className="journal-tabs pp-abas">{ABAS.map(([k, v]) => <button key={k} type="button" className={aba === k ? 'active' : ''} onClick={() => setAba(k)}>{v}</button>)}</nav>
    {aba === 'geral' && <><Geral r={r} L={L} p={p} av={av} irPara={setAba} professor={professor} /><PedirReavaliacao {...reavProps} /></>}
    {aba === 'metas' && <Metas r={r} L={L} checkins={p.checkins_metas} registrar={registrar} professor={professor} />}
    {aba === 'dicas' && <Dicas r={r} L={L} estrategias={p.estrategias} registrar={registrar} />}
    {aba === 'registrar' && <Registrar r={r} registrar={registrar} professor={professor} />}
    {aba === 'linha' && <Linha registros={p.registros} metas={r.metas} />}
    {aba === 'chat' && <Chat criancaId={criancaId} nomeCrianca={c.nome} sessao={sessao} />}
    {aba === 'canal' && <Canal criancaId={criancaId} nomeCrianca={c.nome} onCompartilhar={professor ? null : onCompartilhar} />}
    {aba === 'historico' && <Historico p={p} av={av} onVerVersao={onVerVersao} reavProps={reavProps} />}
  </div>;
}

/** Banner de reavaliação: em andamento, pronta para revisar ou (responsável) botão para pedir. */
function AvisoReavaliacao({ reav, professor, onReavaliacao }) {
  if (!reav) return null;
  if (reav.etapa === 'analise') return <div className="pp-aviso-reav"><RefreshCw size={18} /><span><b>Reavaliação em andamento</b>
    <small>{reav.status === 'aguardando_responsavel' ? (professor ? 'O agente fez uma pergunta à família.' : 'O agente tem uma pergunta para você.') : 'O agente está comparando o perfil com os registros.'}</small></span>
    {!professor && <button className="btn-primary" onClick={() => onReavaliacao?.({ sessao_id: reav.sessao_id })}>{reav.status === 'aguardando_responsavel' ? 'Responder' : 'Acompanhar'}</button>}</div>;
  return <div className="pp-aviso-reav pronta"><Sparkles size={18} /><span><b>Nova versão do perfil pronta</b>
    <small>{professor ? 'Aguardando a família revisar.' : 'Veja como a criança evoluiu e aprove ou peça ajustes.'}</small></span>
    <button className="btn-primary" onClick={() => onReavaliacao?.({ avaliacao_id: reav.avaliacao_id })}>{professor ? 'Ver (somente leitura)' : 'Revisar'}</button></div>;
}

function PedirReavaliacao({ criancaId, av, reav, desdeVigente, professor, onReavaliacao, onAtualizarFormulario, onAviso }) {
  const [aberto, setAberto] = useState(false);
  const [texto, setTexto] = useState('');
  const [ocupado, setOcupado] = useState(false);
  if (professor || reav) return null;
  const dias = Math.floor((Date.now() - new Date(av.aceita_em)) / 864e5);
  async function pedir() {
    setOcupado(true);
    try { const s = await api.reavaliar(criancaId, { comentario: texto }); onReavaliacao?.({ sessao_id: s.sessao_id }); }
    catch (e) { onAviso?.(e.message); setOcupado(false); }
  }
  return <section className="pp-bloco pp-pedir-reav">
    <span className="section-kicker">REAVALIAÇÃO</span>
    <h3>Hora de rever o perfil?</h3>
    <p>Perfil aprovado há {dias} dia(s), com {desdeVigente} registro(s) desde então. O agente lê o perfil atual e todos os registros (quem fez, quando e o que aconteceu), faz o balanço de cada meta, pode perguntar o que faltar e propõe uma nova versão para você revisar.</p>
    {!aberto ? <button className="btn-primary" onClick={() => setAberto(true)}><RefreshCw size={15} /> Solicitar reavaliação</button> : <>
      <label className="pp-field">Quer contar algo ou sugerir um foco? (opcional)
        <textarea value={texto} maxLength={2000} onChange={(e) => setTexto(e.target.value)} placeholder='Ex.: "A fala melhorou muito. Agora quero focar no sono e na hora de dormir."' /></label>
      <div className="pp-opcoes-reav">
        <button type="button" className="pp-opcao" disabled={ocupado} onClick={() => onAtualizarFormulario?.(texto)}>
          <ClipboardList size={20} /><span><b>Atualizar o formulário e reavaliar</b><small>Recomendado após alguns meses. As respostas anteriores vêm preenchidas: você muda só o que mudou, e as cores das áreas são recalculadas.</small></span></button>
        <button type="button" className="pp-opcao" disabled={ocupado} onClick={pedir}>
          <RefreshCw size={20} /><span><b>{ocupado ? 'Iniciando…' : 'Reavaliar só com os registros'}</b><small>Mais rápido. O agente usa o perfil atual e o que foi registrado no período.</small></span></button>
      </div>
      <button className="btn-text" disabled={ocupado} onClick={() => setAberto(false)}>Cancelar</button></>}
  </section>;
}

function Geral({ r, L, p, av, irPara, professor }) {
  return <div className="pp-grade">
    {av.perfil.reavaliacao && <section className="pp-bloco span3 pp-evolucao"><span className="section-kicker">EVOLUÇÃO DESDE A VERSÃO ANTERIOR · {dataDia(av.perfil.reavaliacao.periodo.de)} → {dataDia(av.perfil.reavaliacao.periodo.ate)}</span>
      <Evolucao av={av} compacto /><button className="pp-link" onClick={() => irPara('historico')}>Ver a evolução completa →</button></section>}
    <section className="pp-bloco destaque span2"><span className="section-kicker">RESUMO DO PERFIL</span><p className="pp-resumo">{r.resumo}</p>
      <div className="pp-chips">{r.caracteristicas.map((x) => <span key={x} className="pp-chip">{x}</span>)}</div></section>
    <section className="pp-bloco span3"><span className="section-kicker">FOCO AGORA</span>
      <div className="pp-focos">{r.foco_prioritario.map((f, i) => <div key={i} className="pp-foco"><b>{i + 1}. {DOMINIOS[f.dominio]}</b><p>{f.por_que}</p></div>)}</div></section>
    <section className="pp-bloco span3"><span className="section-kicker">AS 14 ÁREAS</span><Semaforo dominios={r.dominios} legiveis={L} compacto /></section>
    <section className="pp-bloco"><span className="section-kicker">METAS DE CURTO PRAZO</span>
      {r.metas.filter((m) => m.horizonte === 'curto').map((m) => <div key={m.id} className="pp-mini-meta"><p>{m.texto}</p><Progresso historico={p.checkins_metas[m.id] || []} /></div>)}
      <button className="pp-link" onClick={() => irPara('metas')}>{professor ? 'Ver metas →' : 'Registrar progresso →'}</button></section>
    <section className="pp-bloco"><span className="section-kicker">ÚLTIMOS REGISTROS</span>
      {p.registros.slice(0, 5).map((x) => <p key={x.id} className="pp-mini-reg"><IconeTipo tipo={x.tipo} size={15} className="pp-ic" /> {resumoRegistro(x, r.metas)}<br /><small>{dataCurta(x.ocorrido_em)} · {x.autor_nome}</small></p>)}
      {!p.registros.length && <p className="pp-sub">Nada ainda. Que tal registrar a primeira conquista?</p>}
      <button className="pp-link" onClick={() => irPara('registrar')}>Novo registro →</button>
      <button className="pp-link" onClick={() => irPara('chat')}>Conversar com o assistente →</button></section>
    {!!r.alertas.length && <section className="pp-bloco alerta span3"><span className="section-kicker">LEMBRETES IMPORTANTES</span>
      {r.alertas.map((a, i) => <p key={i}><b>{a.recomendacao}</b> — {a.texto}</p>)}</section>}
  </div>;
}

function Progresso({ historico }) {
  if (!historico.length) return <small className="pp-sub">Sem registros de progresso ainda.</small>;
  return <div className="pp-progresso">{historico.slice(-10).map((h, i) => <span key={i} title={`${dataCurta(h.em)}${h.texto ? ` — ${h.texto}` : ''}`}
    className={`pp-barra n${h.nivel + 2}`} style={{ height: `${(h.nivel + 3) * 7}px` }} />)}
    <small>atual: {fmtNivel(historico.at(-1).nivel)}</small></div>;
}

function Metas({ r, L, checkins, registrar, professor }) {
  return ['curto', 'medio', 'longo'].map((h) => <section key={h} className="pp-bloco"><h3 className="pp-horizonte">{HORIZONTE[h]}</h3>
    <div className="pp-metas">{r.metas.filter((m) => m.horizonte === h).map((m) => {
      const hist = checkins[m.id] || [];
      return <Meta key={m.id} meta={m} legiveis={L} nivelAtual={hist.at(-1)?.nivel}>
        <Progresso historico={hist} />
        {professor ? <small className="pp-sub">O progresso das metas é registrado pela família. Conte o que viu na escola em “Novo registro”.</small>
          : <CheckinMeta meta={m} registrar={registrar} />}
      </Meta>;
    })}</div></section>);
}

function CheckinMeta({ meta, registrar }) {
  const [nivel, setNivel] = useState(null);
  const [texto, setTexto] = useState('');
  const opcoes = [[-2, meta.gas.menos_2], [-1, meta.gas.menos_1], [0, meta.gas.zero], [1, meta.gas.mais_1], [2, meta.gas.mais_2]];
  async function enviar() {
    await registrar({ tipo: 'checkin_meta', meta_id: meta.id, dados: { nivel_gas: nivel }, texto, dominios: [meta.dominio] });
    setNivel(null); setTexto('');
  }
  return <div className="pp-checkin"><b>Como está esta semana?</b>
    <div className="pp-niveis">{opcoes.map(([n, desc]) => <button type="button" key={n} title={desc} className={nivel === n ? 'sel' : ''} onClick={() => setNivel(n)}>{fmtNivel(n)}</button>)}</div>
    {nivel !== null && <><small>{opcoes.find(([n]) => n === nivel)[1]}</small>
      <input placeholder="Comentário (opcional)" value={texto} onChange={(e) => setTexto(e.target.value)} />
      <button className="btn-primary" onClick={enviar}>Salvar progresso</button></>}
  </div>;
}

function Dicas({ r, L, estrategias, registrar }) {
  return <section className="pp-bloco"><span className="section-kicker">DICAS DO PLANO · CONTE O QUE FUNCIONOU</span>
    <div className="pp-dicas">{r.dicas.map((d, i) => <Dica key={i} dica={d} legiveis={L}>
      <FeedbackDica dica={d} stats={estrategias.filter((e) => e.estrategia === d.titulo)} registrar={registrar} /></Dica>)}</div></section>;
}

function FeedbackDica({ dica, stats, registrar }) {
  const [local, setLocal] = useState('casa');
  const [texto, setTexto] = useState('');
  const tot = stats.reduce((a, s) => ({ f: a.f + s.funcionou, p: a.p + s.parcial, n: a.n + s.nao_funcionou }), { f: 0, p: 0, n: 0 });
  return <div className="pp-feedback">
    {(tot.f + tot.p + tot.n) > 0 && <small className="pp-placar-estrategia">Já testado: <span><IconeResultado resultado="funcionou" size={14} /> {tot.f}</span><span><IconeResultado resultado="parcial" size={14} /> {tot.p}</span><span><IconeResultado resultado="nao_funcionou" size={14} /> {tot.n}</span></small>}
    <div className="pp-linha-form">
      <select value={local} onChange={(e) => setLocal(e.target.value)}>{LOCAIS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
      <input placeholder="Como foi? (opcional)" value={texto} onChange={(e) => setTexto(e.target.value)} />
    </div>
    <div className="pp-niveis">{RESULTADOS.map(([v, l]) => <button type="button" key={v} onClick={async () => {
      await registrar({ tipo: 'feedback_estrategia', estrategia: dica.titulo, resultado: v, local, texto, dominios: [dica.dominio] }); setTexto('');
    }}><IconeResultado resultado={v} /> {l}</button>)}</div>
  </div>;
}

function Dominios({ valor, onChange }) {
  return <div className="pp-chips sel">{Object.entries(DOMINIOS).map(([k, v]) => <button type="button" key={k} className={`pp-chip ${valor.includes(k) ? 'on' : ''}`}
    onClick={() => onChange(valor.includes(k) ? valor.filter((x) => x !== k) : [...valor, k])}>{v}</button>)}</div>;
}

const VAZIO = { texto: '', dominios: [], local: 'casa', quando: '', dados: {}, estrategia: '', resultado: '' };

function Registrar({ r, registrar, professor }) {
  const tipos = ['conquista', 'atividade', 'comportamento', 'observacao', ...(professor ? [] : ['saude'])];
  const [tipo, setTipo] = useState('conquista');
  const [f, setF] = useState(VAZIO);
  const [erro, setErro] = useState('');
  const set = (k, v) => setF({ ...f, [k]: v });
  const setD = (k, v) => setF({ ...f, dados: { ...f.dados, [k]: v } });
  async function enviar(e) {
    e.preventDefault(); setErro('');
    const body = { tipo, texto: f.texto, dominios: f.dominios, local: tipo === 'saude' ? null : f.local, dados: f.dados,
      ocorrido_em: f.quando ? new Date(f.quando).toISOString() : null };
    if (tipo === 'comportamento' && f.estrategia) { body.estrategia = f.estrategia; body.resultado = f.resultado || null; }
    try { await registrar(body); setF(VAZIO); } catch (x) { setErro(x.message); }
  }
  return <section className="pp-bloco pp-registrar">
    <div className="journal-tabs">{tipos.map((t) => <button type="button" key={t} className={tipo === t ? 'active' : ''} onClick={() => { setTipo(t); setF(VAZIO); }}><IconeTipo tipo={t} size={16} /> {TIPOS[t].rotulo}</button>)}</div>
    <form onSubmit={enviar}>
      {tipo === 'conquista' && <><h3>Uma conquista para celebrar</h3>
        <label className="pp-field">O que a criança conseguiu?<textarea required value={f.texto} onChange={(e) => set('texto', e.target.value)} placeholder='Ex.: "Pediu água falando ÁGUA sem eu mostrar"' /></label></>}

      {tipo === 'atividade' && <><h3>Uma atividade que fizeram juntos</h3>
        <label className="pp-field">O que fizeram?<textarea required value={f.texto} onChange={(e) => set('texto', e.target.value)} placeholder="Ex.: brincadeira de dinossauros narrando as ações" /></label>
        <div className="pp-grid">
          <label className="pp-field">Duração (minutos)<input type="number" min="1" value={f.dados.duracao_min || ''} onChange={(e) => setD('duracao_min', Number(e.target.value))} /></label>
          <label className="pp-field">Quanto de ajuda precisou?<select value={f.dados.nivel_ajuda || ''} onChange={(e) => setD('nivel_ajuda', e.target.value)}>
            <option value="">—</option><option value="sem_ajuda">Fez sozinha</option><option value="pouca">Pouca ajuda</option><option value="muita">Muita ajuda</option></select></label>
          <label className="pp-field">Como reagiu?<select value={f.dados.engajamento || ''} onChange={(e) => setD('engajamento', e.target.value)}>
            <option value="">—</option><option value="adorou">Adorou</option><option value="ok">Participou</option><option value="recusou">Não quis</option></select></label>
        </div></>}

      {tipo === 'comportamento' && <><h3>Um momento difícil (registro ABC)</h3>
        <p className="pp-sub">Anotar o que veio antes e depois ajuda a encontrar padrões, sem culpa.</p>
        <label className="pp-field">A · O que aconteceu antes?<input required value={f.dados.antecedente || ''} onChange={(e) => setD('antecedente', e.target.value)} placeholder="Ex.: pedi para desligar o tablet" /></label>
        <label className="pp-field">B · O que a criança fez?<input required value={f.dados.comportamento || ''} onChange={(e) => setD('comportamento', e.target.value)} placeholder="Ex.: chorou e jogou o tablet no chão" /></label>
        <label className="pp-field">C · O que aconteceu depois?<input value={f.dados.consequencia || ''} onChange={(e) => setD('consequencia', e.target.value)} placeholder="Ex.: dei colo, cantei, acalmou em 10 min" /></label>
        <div className="pp-grid">
          <label className="pp-field">Intensidade (1 a 5): {f.dados.intensidade || 3}<input type="range" min="1" max="5" value={f.dados.intensidade || 3} onChange={(e) => setD('intensidade', Number(e.target.value))} /></label>
          <label className="pp-field">Duração (minutos)<input type="number" min="0" value={f.dados.duracao_min ?? ''} onChange={(e) => setD('duracao_min', Number(e.target.value))} /></label>
          <label className="pp-field">Usou alguma dica do plano?<select value={f.estrategia} onChange={(e) => set('estrategia', e.target.value)}>
            <option value="">Nenhuma</option>{r.dicas.map((d) => <option key={d.titulo}>{d.titulo}</option>)}</select></label>
          {f.estrategia && <label className="pp-field">Funcionou?<select required value={f.resultado} onChange={(e) => set('resultado', e.target.value)}>
            <option value="">—</option>{RESULTADOS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>}
        </div>
        <label className="pp-field">Algo mais?<textarea value={f.texto} onChange={(e) => set('texto', e.target.value)} /></label></>}

      {tipo === 'saude' && <><h3>Registro de saúde</h3>
        <div className="pp-grid">
          <label className="pp-field">Tipo<select required value={f.dados.categoria || ''} onChange={(e) => setD('categoria', e.target.value)}>
            <option value="">Selecione</option>{['Consulta', 'Exame', 'Medicação', 'Vacina', 'Sono', 'Alimentação', 'Terapia', 'Outro'].map((x) => <option key={x}>{x}</option>)}</select></label>
          <label className="pp-field">Profissional / serviço<input value={f.dados.profissional || ''} onChange={(e) => setD('profissional', e.target.value)} placeholder="Ex.: pediatra da UBS, fonoaudióloga" /></label>
          <label className="pp-field">Próximo retorno<input type="date" value={f.dados.retorno || ''} onChange={(e) => setD('retorno', e.target.value)} /></label>
        </div>
        <label className="pp-field">O que foi dito ou observado?<textarea required value={f.texto} onChange={(e) => set('texto', e.target.value)} placeholder="Ex.: pediatra encaminhou para fono e audiometria" /></label>
        <small className="pp-sub">Não envie laudos ou documentos neste protótipo; registre só o resumo.</small></>}

      {tipo === 'observacao' && <><h3>Uma observação</h3>
        <label className="pp-field">O que você percebeu?<textarea required value={f.texto} onChange={(e) => set('texto', e.target.value)} /></label></>}

      {tipo !== 'saude' && <><span className="pp-field">Áreas relacionadas</span><Dominios valor={f.dominios} onChange={(v) => set('dominios', v)} /></>}
      <div className="pp-grid">
        {tipo !== 'saude' && <label className="pp-field">Onde?<select value={f.local} onChange={(e) => set('local', e.target.value)}>{LOCAIS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>}
        <label className="pp-field">Quando? <small>(vazio = agora)</small><input type="datetime-local" value={f.quando} onChange={(e) => set('quando', e.target.value)} /></label>
      </div>
      {erro && <div className="questionnaire-error">{erro}</div>}
      <button className="btn-primary">Salvar registro</button>
    </form>
  </section>;
}

function Linha({ registros, metas }) {
  const [filtro, setFiltro] = useState('');
  const lista = filtro ? registros.filter((x) => x.tipo === filtro) : registros;
  return <section className="pp-bloco">
    <div className="journal-tabs">{[['', 'Todos'], ...Object.entries(TIPOS).map(([k, v]) => [k, v.rotulo])].map(([k, v]) =>
      <button type="button" key={k} className={filtro === k ? 'active' : ''} onClick={() => setFiltro(k)}>{k && <IconeTipo tipo={k} size={15} />} {v}</button>)}</div>
    {!lista.length && <p className="pp-sub">Nenhum registro ainda.</p>}
    <ol className="pp-timeline">{lista.map((x) => <li key={x.id}>
      <span className="pp-t-icone"><IconeTipo tipo={x.tipo} size={19} /></span>
      <div><b>{TIPOS[x.tipo].rotulo}</b> <small>· {dataCurta(x.ocorrido_em)} · {x.autor_nome} · {rotuloFuncao(x.autor_funcao)}{x.local ? ` · ${x.local}` : ''}</small>
        <p>{resumoRegistro(x, metas)}</p>
        {!!x.dominios.length && <div className="pp-chips">{x.dominios.map((d) => <span key={d} className="pp-chip mini">{DOMINIOS[d]}</span>)}</div>}
      </div></li>)}</ol>
  </section>;
}

function Historico({ p, av, onVerVersao, reavProps }) {
  const rotulo = { proposta: 'Proposta', vigente: 'Vigente', substituida: 'Substituída', descartada: 'Ajustada' };
  const tipo = { inicial: 'avaliação inicial', reavaliacao: 'reavaliação' };
  return <>
    <PedirReavaliacao {...reavProps} />
    <section className="pp-bloco"><span className="section-kicker">EVOLUÇÃO ENTRE AS VERSÕES APROVADAS</span><EvolucaoVersoes avaliacoes={p.avaliacoes} /></section>
    {av.perfil.reavaliacao && <><h2 className="pp-titulo-secao">O que mudou na última reavaliação</h2><Evolucao av={av} /></>}
    <section className="pp-bloco"><span className="section-kicker">VERSÕES DO PERFIL</span>
      <ol className="pp-timeline">{p.avaliacoes.map((a, i) => <li key={a.id}><span className="pp-t-icone">{a.status === 'vigente' ? <CircleCheck size={19} /> : <FileText size={19} />}</span>
        <div><b>Versão {i + 1} · {rotulo[a.status]}</b> <small>· {tipo[a.tipo]} · {dataCurta(a.criado_em)}</small>
          {a.comentario_responsavel && <p>Pedido de ajuste: “{a.comentario_responsavel}”</p>}
          <button className="pp-link" onClick={() => onVerVersao?.(a.id)}>ver esta versão</button></div></li>)}</ol></section>
    <section className="pp-bloco"><span className="section-kicker">PRÓXIMOS PASSOS E LIMITES</span>
      <ul>{av.perfil.relatorio.proximos_passos.map((x, i) => <li key={i}>{x}</li>)}</ul>
      <p className="pp-limitacoes">{av.perfil.relatorio.limitacoes}</p>
      <Fontes fontes={av.perfil.fontes} />
      <p className="pp-sub">Gerado por {av.perfil.gerado_por?.modelo} ({av.perfil.gerado_por?.agente}). Cores das áreas por idade calculadas por regras; texto, metas e dicas pela IA, revisados por validação automática.</p>
    </section>
  </>;
}
