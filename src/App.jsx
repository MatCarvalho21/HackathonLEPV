import { useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft, ArrowRight, Baby, BookOpen, Check, ChevronDown, CircleHelp,
  ClipboardList, Heart, Home, MessageCircle, Plus, School, ShieldCheck,
  Sparkles, Users, X,
} from 'lucide-react';
import {
  ANSWER_LABELS, AREA_PROMPTS, CONDITIONS, DOMAIN_META, buildQuestionnaire,
} from './questionnaire.js';
import { api, lerSessao, salvarSessao } from './jornada/api.js';
import { Agente, Proposta } from './jornada/Agente.jsx';
import { Painel, TIPOS, resumoRegistro } from './jornada/Painel.jsx';
import { Chat } from './jornada/Chat.jsx';
import './jornada/pp.css';

// Os dados ficam no backend (banco local SQLite → futuro Supabase). No navegador fica só a sessão.
function App() {
  const [sessao, setSessao] = useState(lerSessao);
  const [criancas, setCriancas] = useState([]);
  const [screen, setScreen] = useState(() => (lerSessao() ? 'dashboard' : 'home'));
  const [activeId, setActiveId] = useState(null);
  const [sessaoAgente, setSessaoAgente] = useState(null);
  const [avaliacaoVista, setAvaliacaoVista] = useState(null);
  const [abaPainel, setAbaPainel] = useState('geral');
  const [modal, setModal] = useState('');
  const [notice, setNotice] = useState('');
  const [showProfile, setShowProfile] = useState(false);
  const role = sessao?.papel || 'responsavel';

  useEffect(() => {
    if (!notice) return undefined;
    const timer = setTimeout(() => setNotice(''), 3200);
    return () => clearTimeout(timer);
  }, [notice]);

  async function recarregar() {
    if (!sessao) return [];
    try { const cs = await api.criancas(sessao); setCriancas(cs); return cs; }
    catch (e) { setNotice(e.message); if (/não encontrado/i.test(e.message)) sair(); return []; }
  }
  useEffect(() => { recarregar(); }, [sessao?.id]);

  const activeEstado = criancas.find((c) => c.crianca.id === activeId) || criancas[0];
  const activeChild = activeEstado && { ...activeEstado.crianca, name: activeEstado.crianca.nome, birthDate: activeEstado.crianca.data_nascimento, interests: activeEstado.crianca.interesses };

  function entrar(novaSessao, aviso) {
    salvarSessao(novaSessao); setSessao(novaSessao); setActiveId(null); setScreen('dashboard');
    if (aviso) setNotice(aviso);
  }
  function sair() { salvarSessao(null); setSessao(null); setCriancas([]); setActiveId(null); setScreen('home'); }

  async function saveParent(values) {
    const r = await api.criarResponsavel({ nome: values.nome, email: values.email, telefone: values.telefone || null });
    entrar({ papel: 'responsavel', id: r.id, nome: r.nome, parentesco: values.parentesco }, 'Conta de responsável criada.');
  }
  async function saveTeacher(values) {
    const r = await api.criarProfessor({ nome: values.nome, email: values.email, escola: values.escola, turma: values.turma });
    entrar({ papel: 'professor', id: r.id, nome: r.nome }, 'Conta de professor criada.');
  }
  async function entrarDemo() {
    const r = await api.demoEntrar();
    entrar({ papel: 'responsavel', id: r.responsavel.id, nome: r.responsavel.nome, parentesco: 'Mãe' }, 'Bem-vinda, Ana! A Lia já tem um plano; a Nina está pronta para o formulário.');
  }
  async function entrarDemoProfessor() {
    const r = await api.demoProfessor();
    entrar({ papel: 'professor', id: r.professor.id, nome: r.professor.nome }, `Bem-vinda, ${r.professor.nome.split(' ')[0]}! Estas são as crianças da sua turma.`);
  }
  async function saveChild(values) {
    try {
      const e = await api.criarCrianca({
        nome: values.name, data_nascimento: values.birthDate, responsavel_id: sessao.id, parentesco: sessao.parentesco || null,
        interesses: values.interests.split(',').map((v) => v.trim()).filter(Boolean),
      });
      await recarregar(); setActiveId(e.crianca.id); setModal(''); setScreen('form');
    } catch (e) { setNotice(e.message); }
  }

  /** Abre a criança na etapa certa da jornada: formulário → agente → proposta → painel. */
  async function abrirCrianca(id, aba = 'geral') {
    setActiveId(id);
    try {
      const e = await api.estado(id);
      if (role === 'professor' && e.etapa !== 'vigente') {
        // Professor não preenche formulário, não dispara o agente e não responde às perguntas dele.
        if (e.etapa === 'proposta') { setAvaliacaoVista(e.avaliacao_proposta_id); setScreen('proposta'); }
        else setNotice(`O perfil de ${e.crianca.nome} ainda está sendo montado pela família. Você já pode registrar observações em “Diário e dúvidas”.`);
        return;
      }
      if (e.etapa === 'formulario') setScreen('form');
      else if (e.etapa === 'formulario_enviado') { const s = await api.iniciarAgente(e.formulario_id, false, sessao.id); setSessaoAgente(s.sessao_id); setScreen('agente'); }
      else if (e.etapa === 'analise') { setSessaoAgente(e.sessao_id); setScreen('agente'); }
      else if (e.etapa === 'proposta') { setAvaliacaoVista(e.avaliacao_proposta_id); setScreen('proposta'); }
      else { setAbaPainel(aba); setScreen('painel'); }
    } catch (err) { setNotice(err.message); }
  }

  async function generateAssessment(formPayload, { demo = false } = {}) {
    const f = await api.enviarFormulario({ ...formPayload, consentimento: true, crianca_id: activeChild.id, autor_id: sessao.id });
    const s = await api.iniciarAgente(f.id, demo, sessao.id);
    setSessaoAgente(s.sessao_id); setScreen('agente'); recarregar();
  }

  const voltar = () => { recarregar(); setScreen('dashboard'); };
  /** Reavaliação: acompanhar o agente (sessao_id) ou revisar a proposta pronta (avaliacao_id). */
  function abrirReavaliacao({ sessao_id: sid, avaliacao_id: avId }) {
    if (sid) { setSessaoAgente(sid); setScreen('agente'); } else { setAvaliacaoVista(avId); setScreen('proposta'); }
  }
  const vigente = activeEstado?.etapa === 'vigente';

  return (
    <div className="app-shell">
      {screen !== 'home' && <aside className="sidebar">
        <button className="brand" onClick={voltar} aria-label="Ir para início"><span className="brand-mark"><Heart size={19} fill="currentColor" /></span><span>PLACEHOLDER<span className="brand-dot">.</span></span></button>
        <div className="side-label">ESPAÇO DE ACOMPANHAMENTO</div>
        <button className={`nav-link ${screen === 'dashboard' ? 'selected' : ''}`} onClick={voltar}><Home size={18} /> Visão geral</button>
        {activeChild && <button className={`nav-link ${['form', 'agente', 'proposta'].includes(screen) || (screen === 'painel' && abaPainel !== 'chat') ? 'selected' : ''}`} onClick={() => abrirCrianca(activeChild.id)}><Baby size={18} /> {activeChild.name}</button>}
        {activeChild && vigente && <button className={`nav-link ${screen === 'painel' && abaPainel === 'chat' ? 'selected' : ''}`} onClick={() => abrirCrianca(activeChild.id, 'chat')}><Sparkles size={18} /> Conversar</button>}
        {activeChild && <button className={`nav-link ${screen === 'journal' ? 'selected' : ''}`} onClick={() => setScreen('journal')}><MessageCircle size={18} /> Diário e dúvidas</button>}
        <div className="sidebar-bottom"><div className="safe-note"><ShieldCheck size={17} /><span>Espaço de demonstração<br /><b>Dados no banco local do servidor</b></span></div><button className="profile-switch" onClick={() => setShowProfile((v) => !v)}><span className="avatar">{role === 'professor' ? 'P' : 'R'}</span><span className="profile-label"><b>{sessao?.nome}</b><small>{role === 'professor' ? 'Professor(a)' : 'Responsável'}</small></span><ChevronDown size={16} /></button>
          {showProfile && <div className="profile-menu"><button onClick={() => { sair(); setShowProfile(false); }}>Trocar perfil / sair</button></div>}
        </div>
      </aside>}
      <main className={`main-area ${screen === 'home' ? 'welcome-area' : ''}`}>
        {screen === 'home' && <Welcome onChoose={(nextRole) => setScreen(nextRole === 'responsavel' ? 'signup-parent' : 'signup-teacher')} hasAccount={!!sessao} onContinue={() => setScreen('dashboard')} onDemo={entrarDemo} onDemoProfessor={entrarDemoProfessor} />}
        {screen === 'signup-parent' && <Signup kind="responsavel" onBack={() => setScreen('home')} onSave={saveParent} />}
        {screen === 'signup-teacher' && <Signup kind="professor" onBack={() => setScreen('home')} onSave={saveTeacher} />}
        {screen === 'dashboard' && <Dashboard role={role} criancas={criancas} activeEstado={activeEstado} onOpenJournal={() => setScreen('journal')} onAddChild={() => setModal('child')} onSelectChild={setActiveId} onOpenChild={abrirCrianca} onReavaliacao={(cid, alvo) => { setActiveId(cid); abrirReavaliacao(alvo); }} onTeacherChild={() => setNotice('Peça ao responsável para vincular a criança à sua turma. Crianças vinculadas aparecem aqui.')} />}
        {screen === 'form' && activeChild && role === 'responsavel' && <ChildForm key={activeChild.id} child={activeChild} relationship={role === 'professor' ? 'Professor(a)' : activeEstado?.parentesco || sessao?.parentesco || ''} informante={role} onBack={voltar} onSubmit={generateAssessment} />}
        {screen === 'form' && !activeChild && <EmptyChild onAdd={() => setModal('child')} />}
        {screen === 'agente' && sessaoAgente && <Agente sessaoId={sessaoAgente} nomeCrianca={activeChild?.name} responsavelId={sessao?.id} podeResponder={role === 'responsavel'} onVoltar={voltar} onConcluida={(avId) => { setAvaliacaoVista(avId); setScreen('proposta'); recarregar(); }} />}
        {screen === 'proposta' && avaliacaoVista && <Proposta avaliacaoId={avaliacaoVista} responsavelId={sessao?.id} podeDecidir={role === 'responsavel'} onVoltar={() => { recarregar(); if (vigente) setScreen('painel'); else voltar(); }}
          onAjuste={(sid) => { setSessaoAgente(sid); setScreen('agente'); }}
          onAprovada={async () => { const eraVigente = vigente; await recarregar(); setAbaPainel('geral'); setScreen('painel'); setNotice(eraVigente ? 'Nova versão aprovada! A evolução fica em “Perfil e versões”.' : 'Perfil aprovado! Este é o painel de acompanhamento.'); }} />}
        {screen === 'painel' && activeChild && <Painel criancaId={activeChild.id} sessao={sessao} abaInicial={abaPainel} onVoltar={voltar} onAviso={setNotice} onVerVersao={(id) => { setAvaliacaoVista(id); setScreen('proposta'); }} onReavaliacao={abrirReavaliacao} />}
        {screen === 'journal' && activeChild && <ChildJournal child={activeChild} sessao={sessao} onBack={voltar} onAviso={setNotice} />}
      </main>
      {modal === 'child' && <ChildModal onClose={() => setModal('')} onSave={saveChild} />}
      {notice && <div className="toast"><Check size={16} />{notice}</div>}
      <footer className="global-footer">Demonstração • Dados no banco local (SQLite) • Use dados fictícios • {sessao && <button onClick={sair}>Sair</button>}</footer>
    </div>
  );
}

function Welcome({ onChoose, hasAccount, onContinue, onDemo, onDemoProfessor }) {
  const [entrando, setEntrando] = useState(false);
  const demo = (fn) => async () => { setEntrando(true); try { await fn(); } catch (e) { window.alert(e.message); setEntrando(false); } };
  return <div className="welcome-wrap">
    <header className="welcome-header"><div className="brand"><span className="brand-mark"><Heart size={19} fill="currentColor" /></span><span>PLACEHOLDER<span className="brand-dot">.</span></span></div><span className="demo-tag"><span /> Ambiente de demonstração</span></header>
    <section className="hero"><div className="hero-copy"><div className="eyebrow"><Sparkles size={15} /> DESENVOLVIMENTO COM CUIDADO</div><h1>Cada criança tem<br />seu próprio <em>jeito de florescer.</em></h1><p>Um espaço para família e escola observarem conquistas, compreenderem necessidades e combinarem próximos passos, juntos.</p><div className="hero-actions"><button className="btn-primary" onClick={() => onChoose('responsavel')}>Começar como responsável <ArrowRight size={17} /></button><button className="btn-secondary" disabled={entrando} onClick={demo(onDemo)}><Sparkles size={16} /> {entrando ? 'Preparando…' : 'Entrar na demonstração (família da Lia)'}</button><button className="btn-secondary" disabled={entrando} onClick={demo(onDemoProfessor)}><School size={16} /> Entrar como professora (demo)</button>{hasAccount && <button className="btn-text" onClick={onContinue}>Continuar de onde parei</button>}</div><div className="hero-proof"><span><ShieldCheck size={16} /> Foco no bem-estar da criança</span><span><Users size={16} /> Família e escola em parceria</span></div></div><div className="hero-art"><div className="sun" /><div className="art-note note-one"><span>🌼</span><b>Pequenos passos,<br />grandes descobertas</b></div><div className="art-card"><div className="art-card-head"><span className="art-avatar">✿</span><span><small>UM DIA DE CADA VEZ</small><b>O que já está florescendo?</b></span></div><div className="growth-row"><i>💬</i><span><b>Comunicação</b><small>Expressa escolhas</small></span><span className="growth-pill">+ progresso</span></div><div className="growth-row"><i>🧩</i><span><b>Aprendizagem</b><small>Curiosidade por histórias</small></span><span className="growth-pill">✦ força</span></div><div className="art-footer"><span>Seu ritmo também é progresso.</span><Heart size={15} /></div></div><div className="art-flower flower-a">✿</div><div className="art-flower flower-b">✿</div><div className="art-note note-two">🌱 <span>Juntos, com<br />mais acolhimento</span></div></div></section>
    <section className="choose-section"><div><span className="section-kicker">VAMOS COMEÇAR?</span><h2>Como você participa desse cuidado?</h2><p>Escolha seu perfil para criar um espaço de acompanhamento.</p></div><div className="role-cards"><button className="role-card" onClick={() => onChoose('responsavel')}><span className="role-icon parent-icon"><Heart size={21} /></span><span className="role-text"><b>Sou responsável</b><small>Quero acompanhar o desenvolvimento da criança</small></span><ArrowRight size={18} /></button><button className="role-card" onClick={() => onChoose('professor')}><span className="role-icon teacher-icon"><BookOpen size={21} /></span><span className="role-text"><b>Sou professor(a)</b><small>Quero apoiar as crianças da minha turma</small></span><ArrowRight size={18} /></button></div></section>
    <div className="welcome-bottom"><span>Construído para apoiar, nunca para rotular.</span><span>Privacidade e respeito em cada etapa <ShieldCheck size={15} /></span></div>
  </div>;
}

function Signup({ kind, onBack, onSave }) {
  const parent = kind === 'responsavel';
  const [erro, setErro] = useState('');
  async function submit(event) { event.preventDefault(); setErro(''); const values = Object.fromEntries(new FormData(event.currentTarget)); try { await onSave(values); } catch (e) { setErro(e.message); } }
  return <section className="page-wrap narrow-page"><button className="back-link" onClick={onBack}><ArrowLeft size={16} /> Voltar</button><div className="form-heading"><span className={`step-icon ${parent ? 'parent-icon' : 'teacher-icon'}`}>{parent ? <Heart size={20} /> : <School size={20} />}</span><span className="section-kicker">CRIAR CONTA DE {parent ? 'RESPONSÁVEL' : 'PROFESSOR(A)'}</span><h1>Vamos nos conhecer.</h1><p>Este perfil ajuda a organizar o acompanhamento nesta demonstração.</p></div><form className="panel signup-panel" onSubmit={submit}><div className="field-grid"><label>Nome completo<input name="nome" placeholder="Como podemos chamar você?" required /></label><label>E-mail<input name="email" type="email" placeholder="voce@email.com" required pattern="[^@\s]+@[^@\s]+\.[^@\s]+" title="Use o formato nome@dominio.com (com ponto depois do @)" /></label>{parent ? <><label>Telefone <span className="optional">opcional</span><input name="telefone" type="tel" placeholder="(00) 00000-0000" /></label><label>Parentesco<input name="parentesco" placeholder="Ex.: mãe, pai, avó" required /></label></> : <><label>Escola<input name="escola" placeholder="Nome da escola" required /></label><label>Turma<input name="turma" placeholder="Ex.: 2º ano A" required /></label></>}</div><div className="privacy-callout"><ShieldCheck size={18} /><span><b>Privacidade na demonstração</b><small>Os dados ficam no banco local da plataforma. Use dados fictícios.</small></span></div>{erro && <div className="questionnaire-error">{erro}</div>}<button className="btn-primary full-button" type="submit">Criar meu espaço <ArrowRight size={17} /></button></form><p className="mock-note">Demonstração: não há senha nem envio de e-mail; o e-mail identifica a sua conta.</p></section>;
}

const ETAPA_ROTULO = { formulario: 'Começar', formulario_enviado: 'Enviado', analise: 'Em análise', proposta: 'Revisar', vigente: 'Plano' };

function Dashboard({ role, criancas, activeEstado, onOpenJournal, onAddChild, onSelectChild, onOpenChild, onReavaliacao, onTeacherChild }) {
  const teacher = role === 'professor';
  const activeChild = activeEstado?.crianca;
  const etapa = activeEstado?.etapa;
  return <div className="page-wrap dashboard-page"><header className="topbar"><div><span className="section-kicker">{teacher ? 'ESPAÇO DA ESCOLA' : 'ESPAÇO DA FAMÍLIA'}</span><h1>{teacher ? 'Olá, professor(a).' : 'Olá, que bom ter você aqui.'}</h1><p>Um passo de cada vez, com atenção ao que faz cada criança única.</p></div><span className="today-chip"><span className="status-dot" /> Demonstração ativa</span></header>
    {teacher ? <div className="teacher-banner"><div className="banner-symbol"><School size={24} /></div><div><b>Seu espaço de turma</b><p>Aqui aparecem as crianças vinculadas à sua turma. Abra cada uma para ler o perfil, registrar o que observa na escola, contar quais estratégias do plano funcionaram e conversar com o assistente. O perfil e as metas ficam com a família, e seus registros entram nas reavaliações.</p></div><button className="btn-secondary" onClick={onTeacherChild}><CircleHelp size={16} /> Como funciona</button></div> : null}
    <div className="dash-section-title"><div><h2>{teacher ? 'Crianças acompanhadas' : 'Seu acompanhamento'}</h2><p>{criancas.length ? `${criancas.length} perfil${criancas.length > 1 ? 's' : ''}` : teacher ? 'Nenhuma criança vinculada à sua turma ainda.' : 'Comece criando um perfil para a criança.'}</p></div>{!teacher && <button className="btn-secondary" onClick={onAddChild}><Plus size={17} /> Adicionar criança</button>}</div>
    {!criancas.length ? <div className="empty-card"><span className="empty-illustration">🌱</span><h3>Um novo começo começa por aqui.</h3><p>{teacher ? 'Quando um responsável vincular a criança à sua turma, ela aparece aqui.' : 'Crie um perfil simples para iniciar o formulário e construir as primeiras metas de acompanhamento.'}</p>{!teacher && <button className="btn-primary" onClick={onAddChild}><Plus size={17} /> Cadastrar criança</button>}</div> : <div className="dashboard-grid"><div className="children-list panel"><div className="panel-heading"><span><Users size={17} /> PERFIS</span>{!teacher && <button className="icon-button" onClick={onAddChild} title="Adicionar criança"><Plus size={18} /></button>}</div>{criancas.map(({ crianca: child, etapa: e }) => <button className={`child-row ${activeChild?.id === child.id ? 'active' : ''}`} key={child.id} onClick={() => onSelectChild(child.id)}><span className="child-avatar">{child.nome?.slice(0, 1).toUpperCase()}</span><span className="child-row-text"><b>{child.nome}</b><small>{ageText(child.data_nascimento)} {child.interesses?.length ? `· ${child.interesses.slice(0, 2).join(', ')}` : ''}</small></span><span className={`mini-status ${e === 'vigente' ? 'has-plan' : ''}`}>{ETAPA_ROTULO[e]}</span></button>)}</div>
      <div className="overview-card panel">{activeChild ? <><div className="overview-head"><div><span className="section-kicker">PERFIL DA CRIANÇA</span><h3>{activeChild.nome}</h3><p>{ageText(activeChild.data_nascimento)}{activeChild.interesses?.length ? ` · Gosta de ${activeChild.interesses.join(', ')}` : ''}</p></div><span className="child-avatar large">{activeChild.nome?.slice(0, 1).toUpperCase()}</span></div><div className="overview-divider" />
        {etapa === 'vigente' && <><div className="plan-summary"><span className="summary-icon"><Sparkles size={19} /></span><span><b>Plano de acompanhamento</b><small>{activeEstado.metas} metas · versão {activeEstado.versoes_aprovadas} do perfil</small></span><span className="plan-state accepted">{activeEstado.reavaliacao ? 'Em reavaliação' : 'Em acompanhamento'}</span></div>
          {activeEstado.reavaliacao && !teacher && <button className="btn-secondary full-button journal-open-button" onClick={() => onReavaliacao(activeChild.id, activeEstado.reavaliacao.etapa === 'proposta' ? { avaliacao_id: activeEstado.reavaliacao.avaliacao_id } : { sessao_id: activeEstado.reavaliacao.sessao_id })}><Sparkles size={16} /> {activeEstado.reavaliacao.etapa === 'proposta' ? 'Revisar a nova versão do perfil' : 'Acompanhar a reavaliação'}</button>}<button className="btn-primary full-button" onClick={() => onOpenChild(activeChild.id)}>Abrir painel <ArrowRight size={17} /></button><button className="btn-secondary full-button journal-open-button" onClick={() => onOpenChild(activeChild.id, 'chat')}><Sparkles size={16} /> Conversar sobre {activeChild.nome}</button></>}
        {etapa === 'proposta' && <><div className="plan-summary"><span className="summary-icon"><Sparkles size={19} /></span><span><b>Proposta de perfil</b><small>O agente terminou. {teacher ? 'Aguardando a família aprovar.' : 'Leia, peça ajustes ou aprove.'}</small></span><span className="plan-state">Para revisar</span></div><button className="btn-primary full-button" onClick={() => onOpenChild(activeChild.id)}>{teacher ? 'Ver proposta (somente leitura)' : 'Ver proposta'} <ArrowRight size={17} /></button></>}
        {etapa === 'analise' && <><div className="plan-summary"><span className="summary-icon"><Sparkles size={19} /></span><span><b>Mapeamento em andamento</b><small>{teacher ? 'O agente está analisando o formulário da família.' : 'O agente está analisando o formulário (pode ter uma pergunta para você).'}</small></span><span className="plan-state">Em análise</span></div>{!teacher && <button className="btn-primary full-button" onClick={() => onOpenChild(activeChild.id)}>Acompanhar <ArrowRight size={17} /></button>}</>}
        {teacher && ['formulario', 'formulario_enviado'].includes(etapa) && <div className="start-assessment"><span className="start-icon"><ClipboardList size={23} /></span><h3>Perfil em construção pela família.</h3><p>Quando a família aprovar o perfil, você verá as áreas, as metas e as dicas. Enquanto isso, já dá para registrar observações da escola.</p></div>}
        {!teacher && etapa === 'formulario_enviado' && <><div className="start-assessment"><span className="start-icon"><ClipboardList size={23} /></span><h3>Formulário recebido.</h3><p>Falta gerar o mapeamento de perfil com o agente.</p><button className="btn-primary" onClick={() => onOpenChild(activeChild.id)}>Gerar mapeamento <ArrowRight size={17} /></button></div></>}
        {!teacher && etapa === 'formulario' && <><div className="start-assessment"><span className="start-icon"><ClipboardList size={23} /></span><h3>Vamos conhecer o momento atual?</h3><p>Responda sobre interesses, rotina e experiências. Não precisa saber tudo: cada observação ajuda a construir um primeiro retrato.</p><button className="btn-primary" onClick={() => onOpenChild(activeChild.id)}>Começar formulário <ArrowRight size={17} /></button></div><div className="form-meta"><span><span className="tiny-dot green-dot" /> Cerca de 5 minutos</span><span><ShieldCheck size={14} /> Depois, um agente de IA monta o perfil</span></div></>}
        <button className="btn-secondary full-button journal-open-button" onClick={onOpenJournal}><MessageCircle size={16} /> Diário e dúvidas</button></> : null}</div></div>}
    <div className="support-strip"><span className="support-icon"><Heart size={18} /></span><span><b>O desenvolvimento não é uma corrida.</b><small>Este espaço organiza observações e ideias para apoiar conversas entre família e escola.</small></span><button className="quiet-link" onClick={() => window.alert('O perfil e as metas são propostas de um agente de IA, revisadas pela família. Não substituem avaliação profissional.')}>Saiba mais <ArrowRight size={14} /></button></div>
  </div>;
}

function ChildForm({ child, initialPayload = null, relationship, informante, onBack, onSubmit }) {
  const [usouExemplo, setUsouExemplo] = useState(false);
  const [step, setStep] = useState(() => initialPayload ? 15 : 0);
  const [profile, setProfile] = useState(() => initialPayload?.perfil || ({
    apelido: child.name,
    idade_meses: ageMonthsFromBirth(child.birthDate),
    ano_escolar: '',
    vinculo: relationship,
    interesses: (child.interests || []).join(', '),
    prioridades: '', idiomas: '', prematuridade: 'nao_sei', perda_habilidades: 'nao_sei',
    condicoes_relatadas: [], outra_condicao: '', documento_comprobatorio: 'nao_sei', tipo_documento: '', observacoes_saude: '',
  }));
  const [answers, setAnswers] = useState(initialPayload?.respostas || {});
  const [contexts, setContexts] = useState(initialPayload?.dominios || {});
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const age = Number(profile.idade_meses) || 0;
  const validAge = profile.idade_meses !== '' && Number.isInteger(Number(profile.idade_meses)) && Number(profile.idade_meses) >= 0 && Number(profile.idade_meses) <= 131;
  const schoolYear = profile.ano_escolar ? Number(profile.ano_escolar) : null;
  const schema = useMemo(() => buildQuestionnaire(age, schoolYear), [age, schoolYear]);
  const domainIndex = step - 1;
  const current = step >= 1 && step <= 14 ? schema.dominios[domainIndex] : null;
  const ctx = current ? (contexts[current.id] || emptyDomainContext()) : null;
  const setProfileValue = (key, value) => {
    setProfile((previous) => ({ ...previous, [key]: value }));
    if (['idade_meses', 'ano_escolar'].includes(key)) { setAnswers({}); setContexts({}); }
  };
  const setContextValue = (key, value) => setContexts((previous) => ({ ...previous, [current.id]: { ...ctx, [key]: value } }));
  const go = (next) => { setError(''); setStep(next); window.scrollTo({ top: 0, behavior: 'smooth' }); };

  async function preencherExemplo() {
    setError('');
    try {
      const ex = await api.formularioExemplo();
      setProfile({ ...profile, ...ex.perfil, apelido: child.name, vinculo: relationship || ex.perfil.vinculo, ano_escolar: '', interesses: (child.interests || []).join(', ') || ex.perfil.interesses });
      setAnswers(ex.respostas);
      setContexts(Object.fromEntries(Object.entries(ex.dominios).map(([k, v]) => [k, { ...emptyDomainContext(), ...v }])));
      setUsouExemplo(true); setConsent(true); go(15);
    } catch (e) { setError(e.message); }
  }

  function startObservations() {
    if (!profile.apelido.trim() || !profile.vinculo.trim() || !profile.prioridades.trim() || !validAge) {
      setError('Para continuar, informe como chamar a criança, a idade em meses, seu vínculo e uma prioridade da família.');
      return;
    }
    go(1);
  }

  function nextDomain(event) {
    event.preventDefault();
    const missing = current.perguntas.find((question) => !answers[question.id]?.resposta);
    if (missing) { setError('Responda aos itens desta área ou escolha “Não sei”.'); return; }
    if (!ctx.nao_sei && ![ctx.relato, ctx.pontos_fortes, ctx.desafios, ctx.apoios, ctx.observacoes].some((value) => value?.trim())) {
      setError('Conte ao menos uma observação ou marque “Ainda não sei informar”.'); return;
    }
    go(step === 14 ? 15 : step + 1);
  }

  async function finish() {
    if (!consent) { setError('Confirme que revisou as informações e autoriza o registro local da demonstração.'); return; }
    setBusy(true); setError('');
    const payload = {
      versao: schema.versao,
      informante,
      perfil: {
        ...profile,
        idade_meses: Number(profile.idade_meses),
        ano_escolar: profile.ano_escolar ? Number(profile.ano_escolar) : null,
        interesses: profile.interesses || '',
        condicoes_relatadas: profile.condicoes_relatadas,
      },
      respostas: answers,
      dominios: Object.fromEntries(schema.dominios.map((domain) => [domain.id, contexts[domain.id] || emptyDomainContext()])),
    };
    try { await onSubmit(payload, { demo: usouExemplo }); }
    catch (submissionError) { setError(submissionError.message || 'Não foi possível concluir o formulário.'); }
    finally { setBusy(false); }
  }

  const sectionName = step === 0 ? 'Conhecendo a criança' : step === 15 ? 'Revisão' : DOMAIN_META[current?.id]?.label || 'Área';
  const progress = step === 0 ? 0 : step === 15 ? 100 : Math.round((step / 15) * 100);
  return <div className="page-wrap questionnaire-page">
    <button className="back-link" onClick={onBack}><ArrowLeft size={16} /> Voltar ao perfil</button>
    <div className="questionnaire-header"><div><span className="section-kicker">FORMULÁRIO INICIAL · {child.name.toUpperCase()}</span><h1>Um retrato amplo, feito com escuta.</h1><p>Observe habilidades, interesses, apoios e barreiras em diferentes situações. Este formulário não diagnostica nem mede o potencial da criança.</p></div><div className="questionnaire-status"><span>ETAPA {step === 0 ? '1' : step === 15 ? '16' : step + 1} DE 16</span><b>{sectionName}</b></div></div>
    <div className="questionnaire-progress"><div><span>PROGRESSO</span><span>{progress}%</span></div><div className="progress-track"><i style={{ width: `${progress}%` }} /></div></div>
    {error && <div className="questionnaire-error" role="alert">{error}</div>}

    {step === 0 && <section className="questionnaire-card panel">
      <span className="section-kicker">01 / CONHECENDO A CRIANÇA</span><h2>Começamos pelo contexto de vocês.</h2><p className="questionnaire-lead">As respostas são relatos da família. “Não sei” ou “não se aplica” são opções válidas; não transformam falta de informação em dificuldade.</p>
      <div className="form-profile-grid">
        <label>Como podemos chamar a criança?<input value={profile.apelido} maxLength={60} onChange={(event) => setProfileValue('apelido', event.target.value)} /></label>
        <label>Idade em meses completos<input type="number" min="0" max="131" step="1" value={profile.idade_meses} onChange={(event) => setProfileValue('idade_meses', event.target.value)} /><small>Usada para selecionar perguntas da referência por faixa etária.</small></label>
        <label>Seu vínculo com a criança<input value={profile.vinculo} maxLength={60} placeholder="Mãe, pai, avó, responsável…" onChange={(event) => setProfileValue('vinculo', event.target.value)} /></label>
        <label>Ano escolar atual<select value={profile.ano_escolar} onChange={(event) => setProfileValue('ano_escolar', event.target.value)}><option value="">Não se aplica / não sei</option>{[1, 2, 3, 4, 5].map((year) => <option value={year} key={year}>{year}º ano</option>)}</select></label>
        <label>Línguas usadas em casa<input value={profile.idiomas} maxLength={200} placeholder="Opcional" onChange={(event) => setProfileValue('idiomas', event.target.value)} /></label>
        <label>Nasceu prematuramente?<select value={profile.prematuridade} onChange={(event) => setProfileValue('prematuridade', event.target.value)}><option value="nao_sei">Não sei</option><option value="sim">Sim</option><option value="nao">Não</option></select><small>O formulário registra o relato; não calcula idade corrigida.</small></label>
      </div>
      <label className="long-answer">O que a criança gosta de fazer? Quais interesses, atividades ou pontos fortes você percebe?<textarea maxLength={2000} value={profile.interesses} onChange={(event) => setProfileValue('interesses', event.target.value)} placeholder="Conte sobre brincadeiras, temas favoritos, habilidades, curiosidades e momentos em que ela se sente bem…" /></label>
      <label className="long-answer">O que vocês mais gostariam de apoiar neste momento?<textarea required maxLength={2000} value={profile.prioridades} onChange={(event) => setProfileValue('prioridades', event.target.value)} placeholder="Uma ou mais prioridades da criança e da família…" /></label>
      <div className="form-profile-grid">
        <label>Deixou de fazer algo que já conseguia fazer?<select value={profile.perda_habilidades} onChange={(event) => setProfileValue('perda_habilidades', event.target.value)}><option value="nao_sei">Não sei</option><option value="nao">Não</option><option value="sim">Sim</option></select></label>
      </div>
      {profile.perda_habilidades === 'sim' && <div className="questionnaire-notice"><ShieldCheck size={17} /> Você relatou perda de uma habilidade. Converse com o profissional de saúde que acompanha a criança para avaliar essa mudança; o formulário não substitui essa avaliação.</div>}

      <div className="health-section"><div><span className="section-kicker">INFORMAÇÕES DE SAÚDE E APOIOS · OPCIONAL</span><h3>Há alguma condição informada por profissional?</h3><p>Marcar uma opção registra apenas o relato da família. Não confirma diagnóstico e não permite inferir capacidades, dificuldades ou metas por si só.</p></div>
        <div className="condition-grid">{CONDITIONS.map(([id, label]) => <label className="condition-option" key={id}><input type="checkbox" checked={profile.condicoes_relatadas.includes(id)} onChange={(event) => {
          const currentConditions = profile.condicoes_relatadas;
          const nextConditions = event.target.checked
            ? id === 'prefiro_nao_informar' ? [id] : [...currentConditions.filter((item) => item !== 'prefiro_nao_informar'), id]
            : currentConditions.filter((item) => item !== id);
          setProfileValue('condicoes_relatadas', nextConditions);
        }} />{label}</label>)}</div>
        {profile.condicoes_relatadas.includes('genetica_outra') && <label className="long-answer">Se desejar, informe outra condição ou termo usado pela equipe<textarea maxLength={500} value={profile.outra_condicao} onChange={(event) => setProfileValue('outra_condicao', event.target.value)} /></label>}
        <div className="form-profile-grid"><label>Há laudo, atestado ou relatório que a família possa consultar?<select value={profile.documento_comprobatorio} onChange={(event) => setProfileValue('documento_comprobatorio', event.target.value)}><option value="nao_sei">Não sei / prefiro não informar</option><option value="sim">Sim</option><option value="nao">Não</option></select></label>
          {profile.documento_comprobatorio === 'sim' && <label>Tipo de documento<select value={profile.tipo_documento} onChange={(event) => setProfileValue('tipo_documento', event.target.value)}><option value="">Selecione</option>{['Laudo ou atestado médico', 'Relatório de profissional de saúde', 'Relatório escolar ou multiprofissional', 'Outro documento', 'Não sei informar'].map((type) => <option key={type}>{type}</option>)}</select></label>}</div>
        <label className="long-answer">Há alguma recomendação, adaptação ou informação do documento que você queira resumir?<textarea maxLength={2000} value={profile.observacoes_saude} onChange={(event) => setProfileValue('observacoes_saude', event.target.value)} placeholder="Opcional. Não inclua números de documentos, dados de terceiros ou informações que não sejam necessárias." /></label>
        <div className="questionnaire-notice"><ShieldCheck size={17} /> Nesta demonstração não há envio de arquivo. Use somente dados fictícios; não digite laudos reais. Informação de saúde é sensível e exige proteção e base legal adequada antes de uso real.</div>
      </div>
      <div className="questionnaire-notice"><Sparkles size={17} /> <span><b>Demonstração:</b> não quer digitar? <button type="button" className="btn-text" onClick={preencherExemplo}>Preencher com respostas de exemplo</button> (criança de 3 anos e 2 meses; o agente fará uma pergunta extra).</span></div><div className="form-actions"><div><button className="btn-primary" onClick={startObservations}>Começar observações <ArrowRight size={16} /></button><small className="field-hint">Obrigatórios: nome, idade em meses, vínculo e prioridade da família.</small></div></div>
    </section>}

    {current && <section className="questionnaire-card panel"><div className="domain-intro"><span className="domain-emoji">{DOMAIN_META[current.id]?.icon}</span><div><span className="section-kicker">ÁREA {step} DE 14 · {current.natureza === 'contextual' ? 'RELATO CONTEXTUAL' : 'OBSERVAÇÃO POR IDADE'}</span><h2>{current.nome}</h2><p>{current.faixa_referencia_meses ? `Perguntas de referência: ${current.faixa_referencia_meses} meses (${Math.floor(current.faixa_referencia_meses / 12)} anos${current.faixa_referencia_meses % 12 ? ` e ${current.faixa_referencia_meses % 12} meses` : ''}).` : 'Esta área é registrada pelo contexto e impacto no cotidiano, sem classificação por marcos etários.'}</p></div></div>
      <div className="domain-guidance"><b>Para orientar o relato</b><p>{AREA_PROMPTS[current.id]}</p></div>
      {current.perguntas.length ? <div className="milestone-list"><h3>O que você observa?</h3><p>Considere oportunidades e apoios. Cada item pode receber uma resposta diferente.</p>{current.perguntas.map((question) => <fieldset className="milestone-question" key={question.id}><legend>{question.pergunta}</legend><div className="milestone-options">{Object.entries(schema.opcoes).map(([value, label]) => <label className={answers[question.id]?.resposta === value ? 'selected' : ''} key={value}><input type="radio" required name={question.id} value={value} checked={answers[question.id]?.resposta === value} onChange={() => setAnswers((previous) => ({ ...previous, [question.id]: { ...previous[question.id], resposta: value, exemplo: previous[question.id]?.exemplo || '' } }))} />{label}</label>)}</div><label className="inline-example">Exemplo ou apoio utilizado <span className="optional">opcional</span><textarea rows="2" maxLength={2000} value={answers[question.id]?.exemplo || ''} onChange={(event) => setAnswers((previous) => ({ ...previous, [question.id]: { ...previous[question.id], exemplo: event.target.value } }))} placeholder="Em que situação aconteceu? Que ajuda foi oferecida?" /></label><details className="source-detail"><summary>Ver referência e faixa</summary><small>{Array.isArray(question.fonte) ? question.fonte.join(' · ') : question.fonte} · {question.faixa}</small></details></fieldset>)}</div> : <div className="questionnaire-notice"><CircleHelp size={17} /> Não há um marco específico selecionado para esta área e idade. O relato do cotidiano e o impacto na participação são especialmente importantes.</div>}
      <div className="domain-writing"><h3>Conte mais sobre esta área</h3><label>O que a criança já faz bem ou demonstra interesse?<textarea maxLength={2000} value={ctx.pontos_fortes} onChange={(event) => setContextValue('pontos_fortes', event.target.value)} placeholder="Habilidades, preferências, situações em que participa com confiança…" /></label><label>O que é difícil, e em quais situações costuma precisar de apoio?<textarea maxLength={2000} value={ctx.desafios} onChange={(event) => setContextValue('desafios', event.target.value)} placeholder={current.pergunta_contexto} /></label><label>O que vocês já tentaram? O que ajudou, ajudou em parte ou não funcionou?<textarea maxLength={2000} value={ctx.apoios} onChange={(event) => setContextValue('apoios', event.target.value)} placeholder="Inclua o apoio, o contexto e como a criança reagiu…" /></label><label>Outros comentários ou exemplos que queira guardar<textarea maxLength={2000} value={ctx.observacoes} onChange={(event) => setContextValue('observacoes', event.target.value)} placeholder="Opcional…" /></label></div>
      <div className="form-profile-grid"><label>Onde você observa estas situações?<select value={ctx.contexto} onChange={(event) => setContextValue('contexto', event.target.value)}>{[['nao_sei', 'Não sei'], ['casa', 'Em casa'], ['escola', 'Na escola'], ['ambos', 'Em casa e na escola'], ['outro', 'Em outro lugar']].map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label className="unknown-option"><input type="checkbox" checked={ctx.nao_sei} onChange={(event) => setContextValue('nao_sei', event.target.checked)} /> Ainda não sei informar sobre esta área</label></div>
      <div className="form-actions"><button className="btn-secondary" onClick={() => go(step - 1)}><ArrowLeft size={16} /> Etapa anterior</button><button className="btn-primary" onClick={nextDomain}>{step === 14 ? 'Revisar formulário' : 'Próxima área'} <ArrowRight size={16} /></button></div>
    </section>}

    {step === 15 && <section className="questionnaire-card panel"><span className="section-kicker">REVISÃO · ANTES DE REGISTRAR</span><h2>Confira este retrato inicial.</h2><p className="questionnaire-lead">Revise cada área e ajuste o que quiser. Os relatos permanecem separados das interpretações e sugestões futuras do modelo.</p><div className="review-profile"><b>{profile.apelido}</b><span>{profile.idade_meses} meses · {profile.ano_escolar ? `${profile.ano_escolar}º ano` : 'ano escolar não informado'} · Relato de {profile.vinculo}</span><p><b>Prioridade da família:</b> {profile.prioridades}</p><p><b>Interesses e pontos fortes:</b> {profile.interesses || 'Não informado'}</p><p><b>Condição relatada:</b> {profile.condicoes_relatadas.length ? profile.condicoes_relatadas.map((id) => CONDITIONS.find(([conditionId]) => conditionId === id)?.[1] || profile.outra_condicao).filter(Boolean).join('; ') : 'Não informada'}</p><p><b>Documento:</b> {profile.documento_comprobatorio === 'sim' ? `${profile.tipo_documento || 'Tipo não informado'} — documento não anexado` : profile.documento_comprobatorio === 'nao' ? 'Família relata que não há' : 'Não informado'}</p><p><b>Informações ou adaptações de saúde resumidas:</b> {profile.observacoes_saude || profile.outra_condicao || 'Não informado'}</p><button className="btn-secondary" onClick={() => go(0)}>Editar dados iniciais</button></div>
        {schema.dominios.map((domain, index) => <details className="review-domain" key={domain.id}><summary><span>{DOMAIN_META[domain.id]?.icon} {domain.nome}</span><small>{index + 1}/14</small></summary>{domain.perguntas.map((question) => <p key={question.id}><b>{question.pergunta}</b><br />{ANSWER_LABELS[answers[question.id]?.resposta] || 'Sem resposta'}{answers[question.id]?.exemplo ? ` — ${answers[question.id].exemplo}` : ''}</p>)}<p><b>Pontos fortes:</b> {contexts[domain.id]?.pontos_fortes || 'Não informado'}</p><p><b>Dificuldades e apoios necessários:</b> {contexts[domain.id]?.desafios || (contexts[domain.id]?.nao_sei ? 'Ainda não sabe informar' : 'Não informado')}</p><p><b>O que ajuda / já foi tentado:</b> {contexts[domain.id]?.apoios || 'Não informado'}</p><p><b>Contexto:</b> {contexts[domain.id]?.contexto || 'Não informado'}</p><button className="btn-secondary" onClick={() => go(index + 1)}>Editar esta área</button></details>)}
        <label className="consent-box"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /><span><b>Confirmo que revisei as informações e autorizo o registro destas informações no banco da demonstração.</b><small>Inclui relatos de desenvolvimento e, se preenchidas, informações de saúde. Use somente dados fictícios nesta versão.</small></span></label>
        <div className="questionnaire-notice"><ShieldCheck size={17} /> As respostas são relatos familiares, não avaliação clínica validada. Ao concluir, um agente de IA organiza um mapa de perfil com metas e dicas, sem diagnóstico. Você revisa, pede ajustes e só então aprova.</div>
        <div className="form-actions"><button className="btn-secondary" onClick={() => go(14)}><ArrowLeft size={16} /> Voltar</button><button className="btn-primary" disabled={!consent || busy} onClick={finish}>{busy ? 'Enviando ao agente…' : 'Concluir e gerar mapeamento'} <Check size={16} /></button></div>
      </section>}
    <aside className="questionnaire-aside"><div><ShieldCheck size={18} /><b>Relato, não diagnóstico</b><p>As perguntas ajudam a organizar o que a família observa. Não atribuem condição, escore ou prognóstico.</p></div><div><Sparkles size={18} /><b>Forças e apoios também contam</b><p>Em cada área, registre interesses, o que já funciona e que barreiras afetam a participação.</p></div><div><BookOpen size={18} /><b>Referências visíveis</b><p>Quando houver marco selecionado, abra “Ver referência e faixa” para conferir de onde veio a pergunta.</p></div></aside>
  </div>;
}

function emptyDomainContext() {
  return { relato: '', pontos_fortes: '', desafios: '', apoios: '', observacoes: '', nao_sei: false, contexto: 'nao_sei' };
}

function ageMonthsFromBirth(date) {
  if (!date) return 0;
  const birth = new Date(`${date}T12:00:00`); const today = new Date();
  let months = (today.getFullYear() - birth.getFullYear()) * 12 + today.getMonth() - birth.getMonth();
  if (today.getDate() < birth.getDate()) months -= 1;
  return Math.max(0, Math.min(months, 131));
}

function localDateInputValue() {
  const local = new Date();
  local.setMinutes(local.getMinutes() - local.getTimezoneOffset());
  return local.toISOString().slice(0, 10);
}

const CONTEXTO_LOCAL = { casa: 'casa', escola: 'escola', comunidade: 'outro', outro: 'outro' };
const RESULTADO_REGISTRO = { ajudou: 'funcionou', parcialmente: 'parcial', nao_ajudou: 'nao_funcionou' };

function ChildJournal({ child, sessao, onBack, onAviso }) {
  const [tab, setTab] = useState('history');
  const [registros, setRegistros] = useState([]);
  const [goals, setGoals] = useState([]);
  const actorRole = sessao?.papel || 'responsavel';
  const actorLabel = actorRole === 'professor' ? 'Professor(a)' : 'Responsável';
  async function carregar() {
    const p = await api.painel(child.id);
    setRegistros(p.registros);
    setGoals(p.avaliacao_vigente?.perfil.relatorio.metas || []);
  }
  useEffect(() => { carregar().catch((e) => onAviso(e.message)); }, [child.id]);

  async function submitObservation(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const v = Object.fromEntries(new FormData(form));
    const meta = goals.find((g) => g.id === v.goalId);
    const resultado = RESULTADO_REGISTRO[v.result];
    try {
      await api.registrar(child.id, {
        tipo: 'observacao', autor: actorRole, autor_id: sessao.id, texto: v.observation,
        local: CONTEXTO_LOCAL[v.context] || null, meta_id: v.goalId || null, dominios: meta ? [meta.dominio] : [],
        ocorrido_em: v.eventDate ? new Date(`${v.eventDate}T12:00:00`).toISOString() : null,
        dados: { activity: v.activity, reaction: v.reaction, support: v.support, result: v.result, comments: v.comments, contexto: v.context },
        // Apoio tentado + resultado conhecido também alimenta o histórico de estratégias
        ...(v.support?.trim() && resultado ? { estrategia: v.support.trim().slice(0, 200), resultado } : {}),
      });
      form.reset(); setTab('history'); onAviso('Observação guardada no histórico da criança.'); carregar();
    } catch (e) { onAviso(e.message); }
  }

  function dateLabel(iso) {
    const date = new Date(iso);
    return Number.isNaN(date.getTime()) ? 'Data não informada' : date.toLocaleDateString('pt-BR', { dateStyle: 'medium' });
  }
  function contextLabel(entry) {
    const original = entry.dados?.contexto;
    return ({ casa: 'Em casa', escola: 'Na escola', comunidade: 'Na comunidade', outro: 'Outro lugar', terapia: 'Na terapia' })[original || entry.local] || 'Contexto não informado';
  }
  function resultLabel(value) {
    return ({ ajudou: 'Ajudou', parcialmente: 'Ajudou em parte', nao_ajudou: 'Não ajudou desta vez', incerto: 'Ainda não sabemos' })[value] || '';
  }

  return <div className="page-wrap journal-page">
    <button className="back-link" onClick={onBack}><ArrowLeft size={16} /> Voltar ao perfil</button>
    <header className="journal-header"><div><span className="section-kicker">HISTÓRICO DA CRIANÇA</span><h1>Diário e dúvidas de {child.name}.</h1><p>Registre o que aconteceu, como a criança reagiu e que apoios foram tentados. Cada entrada guarda quem compartilhou e quando.</p></div><span className="journal-count"><MessageCircle size={17} /> {registros.length} registros</span></header>
    <div className="journal-notice"><ShieldCheck size={18} /><span><b>Demonstração com banco local</b><small>Use dados fictícios. Os registros ficam no banco da plataforma e alimentam o perfil e o assistente.</small></span></div>
    <div className="journal-tabs" role="tablist" aria-label="Seções do histórico">
      <button type="button" className={tab === 'history' ? 'active' : ''} onClick={() => setTab('history')}><ClipboardList size={16} /> Histórico</button>
      <button type="button" className={tab === 'observation' ? 'active' : ''} onClick={() => setTab('observation')}><Plus size={16} /> Nova observação</button>
      <button type="button" className={tab === 'question' ? 'active' : ''} onClick={() => setTab('question')}><CircleHelp size={16} /> Dúvida sobre a criança</button>
    </div>

    {tab === 'history' && <section className="journal-history">
      {!registros.length ? <div className="empty-card journal-empty"><span className="empty-illustration">🌱</span><h3>O histórico começa com uma observação.</h3><p>Registre uma situação de casa ou da escola, ou converse com o assistente sobre uma dúvida.</p><div><button className="btn-primary" onClick={() => setTab('observation')}><Plus size={16} /> Registrar observação</button><button className="btn-secondary" onClick={() => setTab('question')}><CircleHelp size={16} /> Tirar uma dúvida</button></div></div> : <div className="journal-timeline">{registros.map((entry) => <article className="journal-entry panel" key={entry.id}><div className="journal-entry-head"><span className="journal-kind"><ClipboardList size={14} /> {TIPOS[entry.tipo]?.icone} {TIPOS[entry.tipo]?.rotulo}</span><time>{dateLabel(entry.ocorrido_em)}</time></div><h3>{entry.dados?.activity || TIPOS[entry.tipo]?.rotulo || 'Situação observada'}</h3><p className="journal-observation-text">{entry.dados?.activity ? entry.texto : resumoRegistro(entry, goals)}</p><div className="journal-facts"><span>{contextLabel(entry)}</span>{entry.meta_id && <span>Meta: {goals.find((goal) => goal.id === entry.meta_id)?.texto.slice(0, 50) || 'Acompanhamento geral'}</span>}{entry.dados?.result && <span>Resultado percebido: {resultLabel(entry.dados.result)}</span>}</div>{entry.dados?.reaction && <p><b>Reação da criança:</b> {entry.dados.reaction}</p>}{entry.dados?.support && <p><b>Apoio tentado:</b> {entry.dados.support}</p>}{entry.dados?.comments && <p><b>Outros comentários:</b> {entry.dados.comments}</p>}<div className="journal-entry-foot"><span>{entry.autor_nome} · {entry.autor === 'professor' ? 'Professor(a)' : 'Responsável'}</span></div></article>)}</div>}
    </section>}

    {tab === 'observation' && <form className="journal-form panel" onSubmit={submitObservation}>
      <div className="journal-form-heading"><span className="section-kicker">REGISTRAR NO HISTÓRICO</span><h2>O que aconteceu?</h2><p>Descreva uma situação concreta. O relato fica associado ao perfil de {child.name}.</p></div>
      <div className="journal-form-grid">
        <label>Data da situação<input name="eventDate" type="date" defaultValue={localDateInputValue()} required /></label>
        <label>Onde aconteceu?<select name="context" defaultValue="casa"><option value="casa">Em casa</option><option value="escola">Na escola</option><option value="comunidade">Na comunidade</option><option value="outro">Outro lugar</option></select></label>
        <label className="journal-wide">Atividade ou ação realizada<input name="activity" maxLength={180} placeholder="Ex.: brincadeira em grupo, tarefa de leitura, hora de se vestir" /></label>
        <label className="journal-wide">Conte o que aconteceu<textarea name="observation" required maxLength={2000} placeholder="O que estava acontecendo antes? O que a criança fez? Inclua somente o que você observou." /></label>
        <label>Como a criança reagiu?<textarea name="reaction" maxLength={1500} placeholder="Como demonstrou que gostou, não gostou, precisou de pausa ou de ajuda?" /></label>
        <label>Que apoio foi tentado?<textarea name="support" maxLength={1500} placeholder="Ex.: instrução curta, imagem, escolha, pausa, mudança no ambiente…" /></label>
        <label>O que aconteceu depois?<select name="result" defaultValue="incerto"><option value="incerto">Ainda não sabemos</option><option value="ajudou">O apoio pareceu ajudar</option><option value="parcialmente">Ajudou em parte</option><option value="nao_ajudou">Não ajudou desta vez</option></select></label>
        <label>Relacionar a uma meta <span className="optional">opcional</span><select name="goalId" defaultValue=""><option value="">Acompanhamento geral</option>{goals.map((goal) => <option value={goal.id} key={goal.id}>{goal.texto.slice(0, 70)}</option>)}</select></label>
        <label className="journal-wide">Outro comentário <span className="optional">opcional</span><textarea name="comments" maxLength={1500} placeholder="Uma informação que ajude a entender o contexto…" /></label>
      </div>
      <div className="journal-form-footer"><span>Registrado por você como {actorLabel}</span><button className="btn-primary" type="submit"><Check size={16} /> Guardar no histórico</button></div>
    </form>}

    {tab === 'question' && <section className="pp"><Chat criancaId={child.id} nomeCrianca={child.name} sessao={sessao} /></section>}
  </div>;
}

function ChildModal({ onClose, onSave }) {
  function submit(event) { event.preventDefault(); onSave(Object.fromEntries(new FormData(event.currentTarget))); }
  return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><form className="modal-card" onSubmit={submit}><div className="modal-header"><span className="role-icon parent-icon"><Baby size={21} /></span><button type="button" className="icon-button" onClick={onClose}><X size={18} /></button></div><span className="section-kicker">NOVO PERFIL</span><h2>Vamos conhecer a criança.</h2><p>Use um nome fictício para esta demonstração.</p><label>Como podemos chamá-la?<input name="name" placeholder="Ex.: Nina" required autoFocus /></label><label>Data de nascimento<input name="birthDate" type="date" required /></label><label>O que ela gosta? <span className="optional">separado por vírgulas</span><input name="interests" placeholder="Ex.: música, animais, água" /></label><button className="btn-primary full-button" type="submit">Salvar e continuar <ArrowRight size={16} /></button></form></div>;
}

function EmptyChild({ onAdd }) { return <div className="page-wrap"><div className="empty-card"><span className="empty-illustration">🌱</span><h3>Vamos começar pelo perfil.</h3><p>Cadastre uma criança para seguir com o formulário de observações.</p><button className="btn-primary" onClick={onAdd}><Plus size={17} /> Criar perfil</button></div></div>; }

function ageText(date) {
  if (!date) return 'Idade não informada';
  const birth = new Date(`${date}T12:00:00`); const now = new Date();
  let years = now.getFullYear() - birth.getFullYear(); let months = now.getMonth() - birth.getMonth();
  if (now.getDate() < birth.getDate()) months -= 1;
  if (months < 0) { years -= 1; months += 12; }
  if (years < 0) return 'Data inválida';
  if (years === 0) return `${Math.max(months, 0)} ${months === 1 ? 'mês' : 'meses'}`;
  return `${years} ${years === 1 ? 'ano' : 'anos'}${months > 0 ? ` e ${months} ${months === 1 ? 'mês' : 'meses'}` : ''}`;
}

export default App;

