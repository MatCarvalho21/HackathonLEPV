import { useEffect, useState } from 'react';
import { ArrowLeft, Check, Mail, ShieldCheck, Trash2, UserPlus } from 'lucide-react';
import { api, dataCurta, FUNCOES } from './api.js';

/** Responsável escolhe quem acompanha a criança: convida por e-mail, vê quem tem acesso e revoga. */
export function Compartilhar({ crianca, onVoltar, onAviso }) {
  const [lista, setLista] = useState([]);
  const [email, setEmail] = useState('');
  const [funcao, setFuncao] = useState('professor');
  const [erro, setErro] = useState('');
  const [ocupado, setOcupado] = useState(false);
  const carregar = () => api.compartilhamentos(crianca.id).then(setLista).catch((e) => setErro(e.message));
  useEffect(() => { carregar(); }, [crianca.id]);

  async function convidar(e) {
    e.preventDefault(); setErro(''); setOcupado(true);
    try {
      await api.compartilhar(crianca.id, email, funcao);
      setEmail(''); onAviso?.('Convite enviado. A pessoa vê o convite ao entrar na conta dela.'); carregar();
    } catch (x) { setErro(x.message); }
    finally { setOcupado(false); }
  }
  async function revogar(c) {
    if (!window.confirm(`Remover o acesso de ${c.acompanhante_nome || c.email} ao perfil de ${crianca.nome}?`)) return;
    try { await api.revogar(c.id); onAviso?.('Acesso removido.'); carregar(); } catch (x) { setErro(x.message); }
  }

  const ativos = lista.filter((c) => c.status === 'ativo');
  const pendentes = lista.filter((c) => c.status === 'pendente');
  return <div className="page-wrap pp narrow-page">
    <button className="back-link" onClick={onVoltar}><ArrowLeft size={16} /> Voltar</button>
    <div className="goals-hero"><span className="goal-spark"><UserPlus size={22} /></span><div>
      <span className="section-kicker">COMPARTILHAR O PERFIL</span>
      <h1>Quem acompanha {crianca.nome}?</h1>
      <p>Convide professores, pedagogos, médicos, terapeutas e familiares. Cada pessoa precisa ter uma conta de acompanhante com o e-mail convidado e aceitar o convite.</p></div></div>

    <section className="pp-bloco">
      <span className="section-kicker">NOVO CONVITE</span>
      <form className="pp-convite" onSubmit={convidar}>
        <label className="pp-field">E-mail da pessoa<input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="nome@escola.com"
          pattern="[^@\s]+@[^@\s]+\.[^@\s]+" title="Use o formato nome@dominio.com" /></label>
        <label className="pp-field">Função<select value={funcao} onChange={(e) => setFuncao(e.target.value)}>
          {Object.entries(FUNCOES).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
        <button className="btn-primary" disabled={ocupado}><Mail size={16} /> {ocupado ? 'Enviando…' : 'Convidar'}</button>
      </form>
      {erro && <div className="questionnaire-error">{erro}</div>}
    </section>

    <section className="pp-bloco">
      <span className="section-kicker">COM ACESSO ({ativos.length})</span>
      {!ativos.length && <p className="pp-sub">Ninguém além de você ainda.</p>}
      <ul className="pp-acessos">{ativos.map((c) => <li key={c.id}>
        <span className="pp-membro professor"><i>{(c.acompanhante_nome || c.email).slice(0, 1).toUpperCase()}</i></span>
        <span><b>{c.acompanhante_nome || c.email}</b><small>{c.funcao_rotulo} · {c.email} · desde {dataCurta(c.respondido_em || c.criado_em).slice(0, 5)}</small></span>
        <button className="btn-secondary" onClick={() => revogar(c)}><Trash2 size={15} /> Remover</button></li>)}</ul>
      {!!pendentes.length && <><span className="section-kicker pp-espaco">AGUARDANDO ACEITE ({pendentes.length})</span>
        <ul className="pp-acessos">{pendentes.map((c) => <li key={c.id}>
          <span className="pp-membro pendente"><i>?</i></span>
          <span><b>{c.email}</b><small>{c.funcao_rotulo} · convidado em {dataCurta(c.criado_em).slice(0, 5)}</small></span>
          <button className="btn-secondary" onClick={() => revogar(c)}><Trash2 size={15} /> Cancelar</button></li>)}</ul></>}
    </section>

    <section className="pp-bloco pp-permissoes">
      <span className="section-kicker"><ShieldCheck size={13} /> O QUE CADA UM PODE FAZER</span>
      <div className="pp-duas-col">
        <div><h4>Acompanhantes</h4><ul className="pp-check">
          <li><Check size={14} /> Ler o perfil, as metas e as dicas</li>
          <li><Check size={14} /> Registrar atividades, comportamentos, conquistas, observações e estratégias testadas</li>
          <li><Check size={14} /> Conversar no canal da criança e com o assistente</li>
          <li><Check size={14} /> Baixar o resumo em PDF</li></ul></div>
        <div><h4>Só você, responsável</h4><ul className="pp-check">
          <li><Check size={14} /> Preencher o formulário e aprovar o perfil</li>
          <li><Check size={14} /> Registrar o progresso das metas e a saúde</li>
          <li><Check size={14} /> Pedir reavaliação</li>
          <li><Check size={14} /> Decidir quem tem acesso</li></ul></div>
      </div>
    </section>
  </div>;
}
