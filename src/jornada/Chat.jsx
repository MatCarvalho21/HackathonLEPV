import { Fragment, useEffect, useRef, useState } from 'react';
import { MessageCircle, Plus, Send, Sparkles } from 'lucide-react';
import { api, dataCurta } from './api.js';

/** Markdown mínimo: parágrafos, listas (- / 1.) e **negrito**. Sem HTML do modelo. */
function Markdown({ texto }) {
  const negrito = (linha) => linha.split(/(\*\*[^*]+\*\*)/g).map((p, i) =>
    p.startsWith('**') && p.endsWith('**') ? <b key={i}>{p.slice(2, -2)}</b> : <Fragment key={i}>{p}</Fragment>);
  const blocos = [];
  let lista = null;
  for (const bruta of texto.split('\n')) {
    const l = bruta.trim();
    const item = l.match(/^([-*•]|\d+[.)])\s+(.*)/);
    if (item) {
      const ordenada = /\d/.test(item[1]);
      if (!lista || lista.ordenada !== ordenada) { lista = { ordenada, itens: [] }; blocos.push(lista); }
      lista.itens.push(item[2]);
    } else {
      lista = null;
      if (l) blocos.push(l.replace(/^#+\s*/, ''));
    }
  }
  return blocos.map((b, i) => typeof b === 'string' ? <p key={i}>{negrito(b)}</p>
    : b.ordenada ? <ol key={i}>{b.itens.map((t, j) => <li key={j}>{negrito(t)}</li>)}</ol>
      : <ul key={i}>{b.itens.map((t, j) => <li key={j}>{negrito(t)}</li>)}</ul>);
}

const SUGESTOES = (nome) => [
  `Como posso ajudar ${nome} nas trocas de atividade?`,
  'O que funcionou melhor nas últimas semanas?',
  `Que brincadeira posso fazer hoje para estimular a fala de ${nome}?`,
  'Como foi a evolução das metas de curto prazo?',
];

export function Chat({ criancaId, nomeCrianca, sessao }) {
  const [conversas, setConversas] = useState([]);
  const [atual, setAtual] = useState(null);
  const [msgs, setMsgs] = useState([]);
  const [texto, setTexto] = useState('');
  const [pensando, setPensando] = useState(false);
  const [erro, setErro] = useState('');
  const fim = useRef(null);

  useEffect(() => {
    api.conversas(criancaId).then((cs) => { setConversas(cs); if (cs[0]) setAtual(cs[0].id); }).catch((e) => setErro(e.message));
  }, [criancaId]);
  useEffect(() => {
    if (!atual) { setMsgs([]); return; }
    api.mensagens(atual).then(setMsgs).catch((e) => setErro(e.message));
  }, [atual]);
  useEffect(() => { fim.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, [msgs.length, pensando]);

  async function enviar(t = texto) {
    const conteudo = t.trim();
    if (!conteudo || pensando) return;
    setErro(''); setTexto(''); setPensando(true);
    setMsgs((m) => [...m, { id: 'tmp', papel: 'usuario', conteudo, criado_em: new Date().toISOString() }]);
    try {
      const r = await api.conversar(criancaId, { texto: conteudo, conversa_id: atual, autor: sessao.papel, autor_id: sessao.id });
      setMsgs((m) => [...m.filter((x) => x.id !== 'tmp'), r.mensagem_usuario, r.mensagem_assistente]);
      if (!atual) {
        setAtual(r.conversa.id);
        setConversas((cs) => [{ ...r.conversa, mensagens: 2 }, ...cs]);
      }
    } catch (e) {
      setErro(e.message); setTexto(conteudo);
      setMsgs((m) => m.filter((x) => x.id !== 'tmp'));
    } finally { setPensando(false); }
  }

  return <div className="pp-chat">
    <aside className="pp-chat-lista">
      <button className="btn-secondary full-button" onClick={() => { setAtual(null); setMsgs([]); }}><Plus size={15} /> Nova conversa</button>
      {conversas.map((c) => <button key={c.id} className={`pp-chat-item ${c.id === atual ? 'ativa' : ''}`} onClick={() => setAtual(c.id)}>
        <b>{c.titulo || 'Conversa'}</b><small>{dataCurta(c.ultima || c.criado_em)}</small></button>)}
    </aside>
    <section className="pp-chat-janela panel">
      <header className="pp-chat-topo"><span className="pp-chat-avatar"><Sparkles size={17} /></span>
        <div><b>Assistente de {nomeCrianca}</b><small>Conhece o perfil aprovado, as metas e os últimos registros. Consulta a base oficial quando precisa.</small></div></header>
      <div className="pp-chat-msgs">
        {!msgs.length && !pensando && <div className="pp-chat-vazio"><MessageCircle size={26} />
          <p>Pergunte qualquer coisa sobre o dia a dia de {nomeCrianca}.</p>
          <div className="pp-chat-sugestoes">{SUGESTOES(nomeCrianca).map((s) => <button key={s} onClick={() => enviar(s)}>{s}</button>)}</div></div>}
        {msgs.map((m) => <div key={m.id} className={`pp-msg ${m.papel}`}>
          <div className="pp-balao">{m.papel === 'assistente' ? <Markdown texto={m.conteudo} /> : m.conteudo}</div>
          {m.papel === 'assistente' && (m.sugestoes?.fontes?.length > 0 || m.sugestoes?.ferramentas?.length > 0) && <div className="pp-msg-meta">
            {m.sugestoes.ferramentas.filter((f) => f.startsWith('registros')).length > 0 && <span className="pp-ev pp-ev-relato" title={m.sugestoes.ferramentas.join(' · ')}>consultou registros</span>}
            {m.sugestoes.fontes.map((f) => <span key={f.id} className="pp-ev pp-ev-fonte" title={f.secao}>{f.documento.replace(/\.pdf$/, '').replace(/_/g, ' ').slice(0, 42)}</span>)}
          </div>}
          <small className="pp-msg-hora">{dataCurta(m.criado_em)}</small>
        </div>)}
        {pensando && <div className="pp-msg assistente"><div className="pp-balao"><span className="pp-pontos"><i /><i /><i /></span></div></div>}
        <div ref={fim} />
      </div>
      {erro && <div className="questionnaire-error">{erro}</div>}
      <form className="pp-chat-entrada" onSubmit={(e) => { e.preventDefault(); enviar(); }}>
        <textarea rows={2} value={texto} placeholder={`Escreva sua dúvida sobre ${nomeCrianca}…`} onChange={(e) => setTexto(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); enviar(); } }} />
        <button className="btn-primary" disabled={pensando || !texto.trim()}><Send size={15} /></button>
      </form>
      <small className="pp-sub">O assistente não substitui profissionais de saúde ou educação. Em situação de risco, procure um serviço de saúde.</small>
    </section>
  </div>;
}
