import React, { useEffect, useRef, useState } from 'react';
import { api, idade, ir } from './api.js';
import { Relatorio } from './Relatorio.jsx';
import { Painel } from './Painel.jsx';
import './jornada.css';

function useRota() {
  const [rota, setRota] = useState(window.location.hash.slice(1) || '/');
  useEffect(() => {
    const f = () => setRota(window.location.hash.slice(1) || '/');
    window.addEventListener('hashchange', f);
    return () => window.removeEventListener('hashchange', f);
  }, []);
  return rota.split('/').filter(Boolean);
}

export default function Jornada({ Formulario }) {
  const [tela, id] = useRota();
  if (tela === 'formulario') return <Formulario />;
  if (tela === 'agente') return <Moldura><Agente sessaoId={id} /></Moldura>;
  if (tela === 'proposta') return <Moldura><Proposta avaliacaoId={id} /></Moldura>;
  if (tela === 'painel') return <Painel formularioId={id} />;
  return <Moldura><Inicio /></Moldura>;
}

export function Moldura({ children, largura }) {
  return <div className="jornada">
    <header className="topo"><a href="#/" className="brand"><span className="logo">✳</span> Primeiros Passos</a><span className="tag">Conhecer • Acolher • Acompanhar</span></header>
    <main className={`j-main ${largura ? 'largo' : ''}`}>{children}</main>
    <footer>Protótipo de hackathon · dados fictícios · não substitui avaliação profissional.</footer>
  </div>;
}

function Inicio() {
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState('');
  async function demo() {
    setOcupado(true); setErro('');
    try {
      const f = await api.formularioDemo();
      const s = await api.iniciarAgente(f.id, true);
      ir(`/agente/${s.sessao_id}`);
    } catch (e) { setErro(e.message); setOcupado(false); }
  }
  return <section className="inicio">
    <span className="eyebrow">UM OLHAR PARA CADA CRIANÇA</span>
    <h1>Todo caminho começa com escuta.</h1>
    <p>A família conta como a criança aprende, se comunica e participa. Um agente de IA organiza essas informações num mapa de perfil, com metas e dicas, que você revisa antes de aprovar.</p>
    {erro && <div className="error">{erro}</div>}
    <div className="cartoes">
      <button className="cartao principal" disabled={ocupado} onClick={demo}>
        <span className="eyebrow">DEMONSTRAÇÃO</span>
        <b>{ocupado ? 'Enviando formulário…' : 'Usar o formulário da Lia, já preenchido →'}</b>
        <small>Lia, 3 anos e 2 meses. A mãe quer ajudar a fala e diminuir as crises nas trocas de atividade. O agente vai fazer perguntas extras antes do relatório.</small>
      </button>
      <a className="cartao" href="#/formulario">
        <span className="eyebrow">DO ZERO</span>
        <b>Preencher o formulário completo →</b>
        <small>As 14 áreas, uma de cada vez. No final, gere o mapeamento.</small>
      </a>
    </div>
  </section>;
}

function Agente({ sessaoId }) {
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
        if (r.status === 'concluida') { setTimeout(() => ir(`/proposta/${r.avaliacao_id}`), 900); return; }
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

  if (!s) return <p>Carregando…</p>;
  const ajuste = !!s.avaliacao_anterior_id;
  return <section className="agente">
    <span className="eyebrow">{ajuste ? 'AJUSTANDO A PROPOSTA' : 'MAPEAMENTO DE PERFIL'}</span>
    <h2>{s.status === 'aguardando_responsavel' ? 'Antes de terminar, uma dúvida' : s.status === 'erro' ? 'Algo deu errado' : s.status === 'concluida' ? 'Pronto!' : ajuste ? 'Reescrevendo com o seu comentário…' : 'Conhecendo a criança…'}</h2>
    {erro && <div className="error">{erro}</div>}
    <ol className="eventos">
      {s.eventos.map((e, i) => <li key={i} className={i === s.eventos.length - 1 && s.status === 'executando' ? 'atual' : ''}>
        <span className="hora">{new Date(e.em).toLocaleTimeString('pt-BR')}</span>{e.texto}</li>)}
      <li ref={fim} className="fim">{s.status === 'executando' && <span className="pontos"><i /><i /><i /></span>}</li>
    </ol>

    {s.status === 'aguardando_responsavel' && <div className="perguntas">
      <p className="motivo">💬 {s.motivo}</p>
      {s.perguntas.map((p) => <label key={p.id} className="field">{p.pergunta}
        {p.tipo === 'escolha' && p.opcoes?.length
          ? <div className="options">{p.opcoes.map((o) => <label key={o} className={respostas[p.id] === o ? 'selected' : ''}>
            <input type="radio" name={p.id} checked={respostas[p.id] === o} onChange={() => setRespostas({ ...respostas, [p.id]: o })} />{o}</label>)}</div>
          : <textarea value={respostas[p.id] || ''} onChange={(e) => setRespostas({ ...respostas, [p.id]: e.target.value })} placeholder="Conte com suas palavras. Pode deixar em branco se não souber." />}
      </label>)}
      <div className="actions">
        <button className="secondary" disabled={enviando} onClick={() => enviar(true)}>Prefiro não responder</button>
        <button disabled={enviando} onClick={() => enviar(false)}>{enviando ? 'Enviando…' : 'Enviar respostas →'}</button>
      </div>
    </div>}
    {s.status === 'erro' && <div className="error">{s.erro}</div>}
    {s.status !== 'aguardando_responsavel' && <p className="sub">Isso costuma levar de 1 a 2 minutos. O agente consulta a base de conhecimento (Caderneta da Criança, OMS, CDC…) e o relatório passa por uma revisão automática antes de chegar até você.</p>}
  </section>;
}

function Proposta({ avaliacaoId }) {
  const [av, setAv] = useState(null);
  const [erro, setErro] = useState('');
  const [comentario, setComentario] = useState('');
  const [ocupado, setOcupado] = useState(false);
  useEffect(() => { setAv(null); api.avaliacao(avaliacaoId).then(setAv).catch((e) => setErro(e.message)); }, [avaliacaoId]);

  async function ajustar() {
    setOcupado(true); setErro('');
    try { const s = await api.ajustar(avaliacaoId, comentario); ir(`/agente/${s.sessao_id}`); }
    catch (e) { setErro(e.message); setOcupado(false); }
  }
  async function aprovar() {
    setOcupado(true); setErro('');
    try { const r = await api.aprovar(avaliacaoId); ir(`/painel/${r.formulario_id}`); }
    catch (e) { setErro(e.message); setOcupado(false); }
  }

  if (erro && !av) return <div className="error">{erro}</div>;
  if (!av) return <p>Carregando…</p>;
  const c = av.crianca || {};
  const versao = av.avaliacao_anterior_id ? 'Versão ajustada' : 'Primeira versão';
  return <section>
    <span className="eyebrow">PROPOSTA DE PERFIL · {versao.toUpperCase()}</span>
    <h2>O mapa de {c.apelido}, {idade(c.idade_meses)}</h2>
    {av.comentario_responsavel && <p className="notice">Ajustado a partir do seu comentário: “{av.comentario_responsavel}”</p>}
    {av.status !== 'proposta' && <p className="notice">Esta versão está <b>{av.status}</b>.</p>}
    <Relatorio av={av} />
    {av.status === 'proposta' && <section className="bloco decisao">
      <span className="eyebrow">SUA VEZ</span>
      <h3>Este retrato faz sentido para você?</h3>
      <p>Você conhece a criança melhor do que ninguém. Corrija algo que não está certo ou diga o que prefere priorizar.</p>
      <textarea value={comentario} onChange={(e) => setComentario(e.target.value)}
        placeholder='Ex.: "Ela já fala o próprio nome sempre" ou "Quero focar primeiro no sono"' />
      {erro && <div className="error">{erro}</div>}
      <div className="actions">
        <button className="secondary" disabled={ocupado || comentario.trim().length < 3} onClick={ajustar}>Pedir ajuste</button>
        <button disabled={ocupado} onClick={aprovar}>Aprovar e começar o acompanhamento ✓</button>
      </div>
    </section>}
  </section>;
}
