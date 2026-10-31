import { useEffect, useRef, useState } from 'react';
import { MessagesSquare, Send, Users } from 'lucide-react';
import { api, dataCurta } from './api.js';

const INTERVALO_MS = 6000;
/** "Dr. Rafael Lima" → "Dr. Rafael"; "Carla Mendes" → "Carla". */
const primeiroNome = (n) => n.split(' ').slice(0, /^(Dr|Dra|Prof|Profa)\.$/.test(n.split(' ')[0]) ? 2 : 1).join(' ');

/** Canal direto da criança: o responsável e os acompanhantes conversam entre si (pessoas, não a IA). */
export function Canal({ criancaId, nomeCrianca, onCompartilhar }) {
  const [msgs, setMsgs] = useState([]);
  const [equipe, setEquipe] = useState([]);
  const [texto, setTexto] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState('');
  const ultima = useRef(null);
  const fim = useRef(null);

  useEffect(() => {
    let vivo = true, timer;
    ultima.current = null;
    setMsgs([]);
    async function buscar() {
      try {
        const r = await api.canal(criancaId, ultima.current);
        if (!vivo) return;
        setEquipe(r.equipe);
        if (r.mensagens.length) {
          ultima.current = r.mensagens.at(-1).criado_em;
          setMsgs((m) => [...m, ...r.mensagens.filter((x) => !m.some((y) => y.id === x.id))]);
        }
        setErro('');
      } catch (e) { if (vivo) setErro(e.message); }
      if (vivo) timer = setTimeout(buscar, INTERVALO_MS);
    }
    buscar();
    return () => { vivo = false; clearTimeout(timer); };
  }, [criancaId]);
  useEffect(() => { fim.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, [msgs.length]);

  async function enviar() {
    const t = texto.trim();
    if (!t || enviando) return;
    setEnviando(true); setErro('');
    try {
      const m = await api.escreverCanal(criancaId, t);
      ultima.current = m.criado_em;
      setMsgs((x) => [...x, m]); setTexto('');
    } catch (e) { setErro(e.message); }
    finally { setEnviando(false); }
  }

  const sozinho = equipe.length < 2;
  return <div className="pp-canal">
    <section className="pp-bloco pp-canal-topo">
      <span className="pp-canal-icone"><MessagesSquare size={20} /></span>
      <div><h3>Canal de {nomeCrianca}</h3>
        <p className="pp-sub">Mensagens entre a família e quem acompanha {nomeCrianca}. Todos com acesso ao perfil leem. Para dúvidas sobre o desenvolvimento, use o “Assistente (IA)”.</p></div>
      <div className="pp-equipe">{equipe.map((e) => <span key={`${e.papel}-${e.id}`} className={`pp-membro ${e.papel}`} title={e.funcao_rotulo}>
        <i>{e.nome.replace(/^(Dr|Dra|Prof|Profa)\.\s*/, '').slice(0, 1)}</i>{primeiroNome(e.nome)}<small>{e.funcao_rotulo}</small></span>)}</div>
    </section>

    <section className="pp-bloco pp-canal-janela">
      <div className="pp-canal-msgs">
        {!msgs.length && <div className="pp-chat-vazio"><Users size={26} />
          <p>{sozinho ? `Ainda não há ninguém além de você no canal. Compartilhe o perfil de ${nomeCrianca} com quem acompanha a criança.` : 'Nenhuma mensagem ainda. Que tal começar?'}</p>
          {sozinho && onCompartilhar && <button className="btn-secondary" onClick={onCompartilhar}>Compartilhar o perfil</button>}</div>}
        {msgs.map((m) => <div key={m.id} className={`pp-canal-msg ${m.minha ? 'minha' : ''}`}>
          {!m.minha && <span className="pp-canal-autor"><b>{m.autor_nome}</b> · {m.funcao_rotulo}</span>}
          <div className="pp-canal-balao">{m.texto}</div>
          <small>{dataCurta(m.criado_em)}</small>
        </div>)}
        <div ref={fim} />
      </div>
      {erro && <div className="questionnaire-error">{erro}</div>}
      <form className="pp-chat-entrada" onSubmit={(e) => { e.preventDefault(); enviar(); }}>
        <textarea rows={2} value={texto} maxLength={4000} placeholder="Escreva para a equipe… (Enter envia, Shift+Enter quebra a linha)"
          onChange={(e) => setTexto(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); enviar(); } }} />
        <button className="btn-primary" disabled={enviando || !texto.trim()} aria-label="Enviar"><Send size={16} /></button>
      </form>
    </section>
  </div>;
}
