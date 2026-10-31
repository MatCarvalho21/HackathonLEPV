import { useEffect, useRef, useState } from 'react';
import { Bell, CheckCheck, MessagesSquare, Sparkles, Trash2, UserCheck, UserPlus, X } from 'lucide-react';
import { api, tempoAtras } from './api.js';
import { IconeTipo } from './icones.jsx';

const INTERVALO_MS = 20000;

function Icone({ n }) {
  if (n.tipo === 'registro') return <IconeTipo tipo={n.dados?.registro_tipo} size={18} />;
  const I = { canal: MessagesSquare, perfil: Sparkles, convite: UserPlus, acesso: UserCheck }[n.tipo] || Bell;
  return <I size={18} />;
}

/**
 * Sino da barra lateral + painel de notificações.
 * As notificações ficam até a pessoa abrir (vira lida e leva ao lugar certo) ou apagar.
 */
export function Notificacoes({ ativo, onAbrir }) {
  const [aberto, setAberto] = useState(false);
  const [lista, setLista] = useState([]);
  const [naoLidas, setNaoLidas] = useState(0);
  const painel = useRef(null);

  async function carregar() {
    try { const r = await api.notificacoes(); setLista(r.notificacoes); setNaoLidas(r.nao_lidas); } catch { /* sessão expirada trata no App */ }
  }
  useEffect(() => {
    if (!ativo) return undefined;
    carregar();
    const t = setInterval(carregar, INTERVALO_MS);
    return () => clearInterval(t);
  }, [ativo]);
  useEffect(() => { if (aberto) { carregar(); painel.current?.focus(); } }, [aberto]);
  useEffect(() => {
    if (!aberto) return undefined;
    const esc = (e) => e.key === 'Escape' && setAberto(false);
    window.addEventListener('keydown', esc);
    return () => window.removeEventListener('keydown', esc);
  }, [aberto]);

  async function abrir(n) {
    if (!n.lida_em) { const r = await api.lerNotificacao(n.id); setNaoLidas(r.nao_lidas); }
    setAberto(false); onAbrir(n); carregar();
  }
  async function apagar(n) {
    const r = await api.apagarNotificacao(n.id);
    setNaoLidas(r.nao_lidas); setLista((l) => l.filter((x) => x.id !== n.id));
  }
  async function lerTodas() { const r = await api.lerTodas(); setNaoLidas(r.nao_lidas); carregar(); }

  return <>
    <button className={`nav-link pp-sino ${aberto ? 'selected' : ''}`} onClick={() => setAberto((v) => !v)} aria-expanded={aberto}
      aria-label={`Notificações${naoLidas ? `, ${naoLidas} não lidas` : ''}`}>
      <span className="pp-sino-icone"><Bell size={18} />{naoLidas > 0 && <b className="pp-badge">{naoLidas > 99 ? '99+' : naoLidas}</b>}</span> Notificações
    </button>
    {aberto && <div className="pp-notif-fundo" onMouseDown={(e) => e.target === e.currentTarget && setAberto(false)}>
      <aside className="pp-notif" role="dialog" aria-label="Notificações" tabIndex={-1} ref={painel}>
        <header className="pp-notif-topo">
          <div><h2>Notificações</h2><small>{naoLidas ? `${naoLidas} não lida${naoLidas > 1 ? 's' : ''}` : 'Tudo em dia'}</small></div>
          <div className="pp-notif-acoes">
            {naoLidas > 0 && <button className="btn-text" onClick={lerTodas}><CheckCheck size={16} /> Marcar todas como lidas</button>}
            <button className="icon-button" onClick={() => setAberto(false)} aria-label="Fechar"><X size={18} /></button>
          </div>
        </header>
        {!lista.length && <div className="pp-notif-vazio"><Bell size={26} /><p>Nenhuma notificação. Quando alguém da equipe registrar algo ou escrever no canal, aparece aqui.</p></div>}
        <ul className="pp-notif-lista">{lista.map((n) => <li key={n.id} className={n.lida_em ? 'lida' : 'nova'}>
          <button className="pp-notif-item" onClick={() => abrir(n)}>
            <span className={`pp-notif-icone ${n.tipo}`}><Icone n={n} /></span>
            <span className="pp-notif-corpo">
              <b>{n.titulo}</b>
              {n.texto && <span className="pp-notif-texto">“{n.texto}”</span>}
              <small>{n.crianca_nome ? `${n.crianca_nome} · ` : ''}{tempoAtras(n.criado_em)}</small>
            </span>
            {!n.lida_em && <i className="pp-notif-ponto" aria-label="não lida" />}
          </button>
          <button className="pp-notif-apagar" onClick={() => apagar(n)} aria-label="Apagar notificação" title="Apagar"><Trash2 size={16} /></button>
        </li>)}</ul>
      </aside>
    </div>}
  </>;
}
