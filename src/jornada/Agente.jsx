import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, Check, MessageCircle, Sparkles } from 'lucide-react';
import { api, idade } from './api.js';
import { Relatorio } from './Relatorio.jsx';

/** Acompanha o agente ao vivo: eventos, perguntas extras e conclusão. */
export function Agente({ sessaoId, nomeCrianca, onConcluida, onVoltar }) {
  const [s, setS] = useState(null);
  const [erro, setErro] = useState('');
  const [respostas, setRespostas] = useState({});
  const [enviando, setEnviando] = useState(false);
  const fim = useRef(null);

  useEffect(() => {
    let vivo = true, timer;
    async function poll() {
      try {
        const r = await api.sessao(sessaoId);
        if (!vivo) return;
        setS(r);
        if (r.status === 'concluida') { timer = setTimeout(() => onConcluida(r.avaliacao_id), 900); return; }
        if (r.status === 'executando') timer = setTimeout(poll, 1500);
      } catch (e) { if (vivo) setErro(e.message); }
    }
    poll();
    return () => { vivo = false; clearTimeout(timer); };
  }, [sessaoId, enviando]);

  useEffect(() => { fim.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, [s?.eventos?.length]);

  async function enviar(pular = false) {
    setEnviando(true); setErro('');
    try { await api.responder(sessaoId, pular ? {} : respostas); setRespostas({}); }
    catch (e) { setErro(e.message); }
    finally { setEnviando(false); }
  }

  if (!s) return <div className="page-wrap pp"><p>Carregando…</p></div>;
  const ajuste = !!s.avaliacao_anterior_id;
  const titulo = s.status === 'aguardando_responsavel' ? 'Antes de terminar, uma dúvida.'
    : s.status === 'erro' ? 'Algo deu errado.' : s.status === 'concluida' ? 'Pronto!'
      : ajuste ? 'Reescrevendo com o seu comentário…' : `Conhecendo ${nomeCrianca || 'a criança'}…`;
  return <div className="page-wrap pp narrow-page">
    <button className="back-link" onClick={onVoltar}><ArrowLeft size={16} /> Voltar à visão geral</button>
    <section className="panel pp-agente">
      <span className="section-kicker"><Sparkles size={13} /> {ajuste ? 'AJUSTANDO A PROPOSTA' : 'MAPEAMENTO DE PERFIL'}</span>
      <h1>{titulo}</h1>
      {erro && <div className="questionnaire-error">{erro}</div>}
      <ol className="pp-eventos">
        {s.eventos.map((e, i) => <li key={i} className={i === s.eventos.length - 1 && s.status === 'executando' ? 'atual' : ''}>
          <span className="pp-hora">{new Date(e.em).toLocaleTimeString('pt-BR')}</span>{e.texto}</li>)}
        <li ref={fim} className="fim">{s.status === 'executando' && <span className="pp-pontos"><i /><i /><i /></span>}</li>
      </ol>

      {s.status === 'aguardando_responsavel' && <div className="pp-perguntas">
        <p className="pp-motivo"><MessageCircle size={16} /> {s.motivo}</p>
        {s.perguntas.map((p) => <div key={p.id} className="pp-field"><b>{p.pergunta}</b>
          {p.tipo === 'escolha' && p.opcoes?.length
            ? <div className="milestone-options">{p.opcoes.map((o) => <label key={o} className={respostas[p.id] === o ? 'selected' : ''}>
              <input type="radio" name={p.id} checked={respostas[p.id] === o} onChange={() => setRespostas({ ...respostas, [p.id]: o })} />{o}</label>)}</div>
            : <textarea value={respostas[p.id] || ''} onChange={(e) => setRespostas({ ...respostas, [p.id]: e.target.value })} placeholder="Conte com suas palavras. Pode deixar em branco se não souber." />}
        </div>)}
        <div className="form-actions">
          <button className="btn-secondary" disabled={enviando} onClick={() => enviar(true)}>Prefiro não responder</button>
          <button className="btn-primary" disabled={enviando} onClick={() => enviar(false)}>{enviando ? 'Enviando…' : 'Enviar respostas'}</button>
        </div>
      </div>}
      {s.status === 'erro' && <div className="questionnaire-error">{s.erro}</div>}
      {s.status !== 'aguardando_responsavel' && <p className="pp-sub">Costuma levar de 1 a 2 minutos. O agente consulta a base de conhecimento (Caderneta da Criança, OMS, CDC…) e o relatório passa por uma revisão automática antes de chegar até você.</p>}
    </section>
  </div>;
}

/** Proposta de perfil: leitura completa + pedir ajuste ou aprovar. */
export function Proposta({ avaliacaoId, onAjuste, onAprovada, onVoltar, podeDecidir = true }) {
  const [av, setAv] = useState(null);
  const [erro, setErro] = useState('');
  const [comentario, setComentario] = useState('');
  const [ocupado, setOcupado] = useState(false);
  useEffect(() => { setAv(null); api.avaliacao(avaliacaoId).then(setAv).catch((e) => setErro(e.message)); }, [avaliacaoId]);

  async function ajustar() {
    setOcupado(true); setErro('');
    try { const s = await api.ajustar(avaliacaoId, comentario); onAjuste(s.sessao_id); }
    catch (e) { setErro(e.message); setOcupado(false); }
  }
  async function aprovar() {
    setOcupado(true); setErro('');
    try { await api.aprovar(avaliacaoId); onAprovada(); }
    catch (e) { setErro(e.message); setOcupado(false); }
  }

  if (erro && !av) return <div className="page-wrap pp"><div className="questionnaire-error">{erro}</div></div>;
  if (!av) return <div className="page-wrap pp"><p>Carregando…</p></div>;
  const c = av.crianca || {};
  return <div className="page-wrap pp">
    <button className="back-link" onClick={onVoltar}><ArrowLeft size={16} /> Voltar</button>
    <div className="goals-hero"><span className="goal-spark"><Sparkles size={22} /></span><div>
      <span className="section-kicker">PROPOSTA DE PERFIL · {av.avaliacao_anterior_id ? 'VERSÃO AJUSTADA' : 'PRIMEIRA VERSÃO'}</span>
      <h1>Um caminho para {c.apelido}.</h1>
      <p>{idade(c.idade_meses)} · Construído pelo agente a partir das observações da família. Revise e ajuste antes de acompanhar.</p></div></div>
    {av.comentario_responsavel && <div className="demo-warning"><MessageCircle size={18} /><span><b>Ajustado a partir do seu comentário</b><small>“{av.comentario_responsavel}”</small></span></div>}
    {av.status !== 'proposta' && <div className="demo-warning"><span><b>Esta versão está {av.status}.</b></span></div>}
    <Relatorio av={av} />
    {av.status === 'proposta' && podeDecidir && <section className="pp-bloco pp-decisao">
      <span className="section-kicker">SUA VEZ</span>
      <h3>Este retrato faz sentido para você?</h3>
      <p>Você conhece a criança melhor do que ninguém. Corrija algo que não está certo ou diga o que prefere priorizar.</p>
      <textarea value={comentario} onChange={(e) => setComentario(e.target.value)}
        placeholder='Ex.: "Ela já fala o próprio nome sempre" ou "Quero focar primeiro no sono"' />
      {erro && <div className="questionnaire-error">{erro}</div>}
      <div className="form-actions">
        <button className="btn-secondary" disabled={ocupado || comentario.trim().length < 3} onClick={ajustar}>Pedir ajuste</button>
        <button className="btn-primary" disabled={ocupado} onClick={aprovar}><Check size={16} /> Aprovar e começar o acompanhamento</button>
      </div>
    </section>}
  </div>;
}
