import { useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft, ArrowRight, Baby, BookOpen, Check, ChevronDown, CircleHelp,
  ClipboardList, Heart, Home, MessageCircle, Plus, School, ShieldCheck,
  Sparkles, Users, X,
} from 'lucide-react';

const STORE = 'florescer-demo-v1';
const emptyState = { parents: [], teachers: [], children: [], assessments: [] };
const domains = [
  { id: 'COM_R', label: 'Compreensão', icon: '💬', question: 'Como costuma compreender pedidos e orientações do dia a dia?' },
  { id: 'COM_E', label: 'Comunicação', icon: '🗣️', question: 'Como costuma expressar o que quer, sente ou pensa?' },
  { id: 'SOC', label: 'Interação social', icon: '🤝', question: 'Como participa de brincadeiras ou atividades com outras pessoas?' },
  { id: 'COG', label: 'Aprendizagem', icon: '🧩', question: 'Quais atividades de aprender ou resolver problemas despertam seu interesse?' },
  { id: 'AUT', label: 'Autonomia', icon: '🌱', question: 'Em quais momentos do autocuidado ou da rotina participa com mais autonomia?' },
  { id: 'REG', label: 'Regulação', icon: '🌤️', question: 'Que situações ajudam a criança a se sentir segura e tranquila? O que costuma ser difícil?' },
  { id: 'ATE', label: 'Atenção e rotina', icon: '🧭', question: 'O que ajuda a começar, continuar ou concluir uma atividade?' },
  { id: 'SEN', label: 'Sensações', icon: '🎧', question: 'Há sons, texturas, ambientes ou movimentos de que gosta ou que prefere evitar?' },
];
const scale = [
  ['com_frequencia', 'Na maioria das vezes'],
  ['as_vezes', 'Às vezes'],
  ['ainda_nao', 'Ainda é difícil'],
  ['nao_sei', 'Não sei / não observei'],
];

function readStore() {
  try { return { ...emptyState, ...JSON.parse(localStorage.getItem(STORE) || '{}') }; }
  catch { return emptyState; }
}

function App() {
  const [data, setData] = useState(readStore);
  const [screen, setScreen] = useState('home');
  const [role, setRole] = useState('responsavel');
  const [activeId, setActiveId] = useState(null);
  const [form, setForm] = useState({});
  const [modal, setModal] = useState('');
  const [notice, setNotice] = useState('');
  const [showProfile, setShowProfile] = useState(false);

  useEffect(() => { localStorage.setItem(STORE, JSON.stringify(data)); }, [data]);
  useEffect(() => {
    if (!notice) return undefined;
    const timer = setTimeout(() => setNotice(''), 3200);
    return () => clearTimeout(timer);
  }, [notice]);

  const activeChild = data.children.find((child) => child.id === activeId) || data.children[0];
  const activeAssessment = useMemo(() => data.assessments.find((item) => item.childId === activeChild?.id), [data.assessments, activeChild]);

  function saveParent(values) {
    const parent = { id: crypto.randomUUID(), ...values, role: 'responsavel' };
    setData((current) => ({ ...current, parents: [...current.parents, parent] }));
    setRole('responsavel'); setScreen('dashboard'); setNotice('Conta de responsável criada.');
  }

  function saveTeacher(values) {
    const teacher = { id: crypto.randomUUID(), ...values, role: 'professor' };
    setData((current) => ({ ...current, teachers: [...current.teachers, teacher] }));
    setRole('professor'); setScreen('dashboard'); setNotice('Conta de professor criada.');
  }

  function saveChild(values) {
    const child = { id: crypto.randomUUID(), ...values, interests: values.interests.split(',').map((v) => v.trim()).filter(Boolean), createdAt: new Date().toISOString(), turma_id: null };
    setData((current) => ({ ...current, children: [...current.children, child] }));
    setActiveId(child.id); setForm({}); setModal(''); setScreen('form');
  }

  function generateAssessment() {
    const answers = Object.fromEntries(domains.map((item) => [item.id, form[item.id] || 'nao_sei']));
    answers._observacoes = Object.fromEntries(domains.map((item) => [item.id, form[`nota_${item.id}`] || '']).filter(([, value]) => value));
    const metas = domains.filter((item) => ['as_vezes', 'ainda_nao'].includes(answers[item.id])).slice(0, 3).map((item, index) => ({
      id: `m${index + 1}`,
      dominio: item.id,
      nomeDominio: item.label,
      horizonte: index === 0 ? 'curto' : 'medio',
      texto: goalFor(item.id, activeChild),
      estado: 'proposta',
    }));
    const proposal = {
      id: crypto.randomUUID(), childId: activeChild.id, tipo: 'inicial', status: 'proposta',
      respostas_formulario: answers,
      perfil: { interesses: activeChild.interests, resumo: `Perfil inicial de ${activeChild.name}, construído a partir das observações da família.` },
      niveis: Object.fromEntries(domains.map((item) => [item.id, answers[item.id]])),
      metas, createdAt: new Date().toISOString(),
    };
    setData((current) => ({ ...current, assessments: [proposal, ...current.assessments.filter((item) => item.childId !== activeChild.id)] }));
    setScreen('goals');
  }

  function acceptAssessment() {
    setData((current) => ({ ...current, assessments: current.assessments.map((item) => item.childId === activeChild.id ? { ...item, status: 'vigente', aceitaEm: new Date().toISOString() } : item) }));
    setNotice('Plano marcado como vigente para a demonstração.');
  }

  function markDemoDone() {
    setData((current) => ({ ...current, assessments: current.assessments.map((item) => item.childId === activeChild.id ? { ...item, metas: item.metas.map((goal, index) => index === 0 ? { ...goal, estado: 'em_acompanhamento' } : goal) } : item) }));
    setNotice('Acompanhamento atualizado.');
  }

  const hasAccount = data.parents.length + data.teachers.length > 0;

  return (
    <div className="app-shell">
      {screen !== 'home' && <aside className="sidebar">
        <button className="brand" onClick={() => setScreen('dashboard')} aria-label="Ir para início"><span className="brand-mark"><Heart size={19} fill="currentColor" /></span><span>PLACEHOLDER<span className="brand-dot">.</span></span></button>
        <div className="side-label">ESPAÇO DE ACOMPANHAMENTO</div>
        <button className={`nav-link ${screen === 'dashboard' ? 'selected' : ''}`} onClick={() => setScreen('dashboard')}><Home size={18} /> Visão geral</button>
        {activeChild && <button className={`nav-link ${['form', 'goals'].includes(screen) ? 'selected' : ''}`} onClick={() => setScreen(activeAssessment ? 'goals' : 'form')}><Baby size={18} /> {activeChild.name}</button>}
        <div className="sidebar-bottom"><div className="safe-note"><ShieldCheck size={17} /><span>Espaço de demonstração<br /><b>Seus dados ficam neste navegador</b></span></div><button className="profile-switch" onClick={() => setShowProfile((v) => !v)}><span className="avatar">{role === 'professor' ? 'P' : 'R'}</span><span className="profile-label"><b>{role === 'professor' ? data.teachers.at(-1)?.nome : data.parents.at(-1)?.nome}</b><small>{role === 'professor' ? 'Professor(a)' : 'Responsável'}</small></span><ChevronDown size={16} /></button>
          {showProfile && <div className="profile-menu"><button onClick={() => { setScreen('home'); setShowProfile(false); }}>Trocar perfil / sair</button></div>}
        </div>
      </aside>}
      <main className={`main-area ${screen === 'home' ? 'welcome-area' : ''}`}>
        {screen === 'home' && <Welcome onChoose={(nextRole) => { setRole(nextRole); setScreen(nextRole === 'responsavel' ? 'signup-parent' : 'signup-teacher'); }} hasAccount={hasAccount} onContinue={() => setScreen('dashboard')} />}
        {screen === 'signup-parent' && <Signup kind="responsavel" onBack={() => setScreen('home')} onSave={saveParent} />}
        {screen === 'signup-teacher' && <Signup kind="professor" onBack={() => setScreen('home')} onSave={saveTeacher} />}
        {screen === 'dashboard' && <Dashboard role={role} data={data} activeChild={activeChild} onAddChild={() => setModal('child')} onSelectChild={(id) => { setActiveId(id); setScreen(data.assessments.some((a) => a.childId === id) ? 'goals' : 'form'); }} onNewForm={() => { setForm({}); setScreen('form'); }} onTeacherChild={() => setNotice('A vinculação de turma e alunos será conectada ao banco na próxima etapa.')} />}
        {screen === 'form' && activeChild && <ChildForm child={activeChild} answers={form} onAnswer={(id, value) => setForm((current) => ({ ...current, [id]: value }))} onBack={() => setScreen('dashboard')} onSubmit={generateAssessment} />}
        {screen === 'form' && !activeChild && <EmptyChild onAdd={() => setModal('child')} />}
        {screen === 'goals' && activeChild && <Goals child={activeChild} assessment={activeAssessment} onBack={() => setScreen('dashboard')} onAccept={acceptAssessment} onDone={markDemoDone} onEdit={() => setScreen('form')} />}
      </main>
      {modal === 'child' && <ChildModal onClose={() => setModal('')} onSave={saveChild} />}
      {notice && <div className="toast"><Check size={16} />{notice}</div>}
      <footer className="global-footer">Demonstração • Dados salvos somente neste navegador • <button onClick={() => { localStorage.removeItem(STORE); setData(emptyState); setScreen('home'); setActiveId(null); setNotice('Dados de demonstração apagados.'); }}>Limpar demonstração</button></footer>
    </div>
  );
}

function Welcome({ onChoose, hasAccount, onContinue }) {
  return <div className="welcome-wrap">
    <header className="welcome-header"><div className="brand"><span className="brand-mark"><Heart size={19} fill="currentColor" /></span><span>PLACEHOLDER<span className="brand-dot">.</span></span></div><span className="demo-tag"><span /> Ambiente de demonstração</span></header>
    <section className="hero"><div className="hero-copy"><div className="eyebrow"><Sparkles size={15} /> DESENVOLVIMENTO COM CUIDADO</div><h1>Cada criança tem<br />seu próprio <em>jeito de florescer.</em></h1><p>Um espaço para família e escola observarem conquistas, compreenderem necessidades e combinarem próximos passos, juntos.</p><div className="hero-actions"><button className="btn-primary" onClick={() => onChoose('responsavel')}>Começar como responsável <ArrowRight size={17} /></button>{hasAccount && <button className="btn-text" onClick={onContinue}>Continuar demonstração</button>}</div><div className="hero-proof"><span><ShieldCheck size={16} /> Foco no bem-estar da criança</span><span><Users size={16} /> Família e escola em parceria</span></div></div><div className="hero-art"><div className="sun" /><div className="art-note note-one"><span>🌼</span><b>Pequenos passos,<br />grandes descobertas</b></div><div className="art-card"><div className="art-card-head"><span className="art-avatar">✿</span><span><small>UM DIA DE CADA VEZ</small><b>O que já está florescendo?</b></span></div><div className="growth-row"><i>💬</i><span><b>Comunicação</b><small>Expressa escolhas</small></span><span className="growth-pill">+ progresso</span></div><div className="growth-row"><i>🧩</i><span><b>Aprendizagem</b><small>Curiosidade por histórias</small></span><span className="growth-pill">✦ força</span></div><div className="art-footer"><span>Seu ritmo também é progresso.</span><Heart size={15} /></div></div><div className="art-flower flower-a">✿</div><div className="art-flower flower-b">✿</div><div className="art-note note-two">🌱 <span>Juntos, com<br />mais acolhimento</span></div></div></section>
    <section className="choose-section"><div><span className="section-kicker">VAMOS COMEÇAR?</span><h2>Como você participa desse cuidado?</h2><p>Escolha seu perfil para criar um espaço de acompanhamento.</p></div><div className="role-cards"><button className="role-card" onClick={() => onChoose('responsavel')}><span className="role-icon parent-icon"><Heart size={21} /></span><span className="role-text"><b>Sou responsável</b><small>Quero acompanhar o desenvolvimento da criança</small></span><ArrowRight size={18} /></button><button className="role-card" onClick={() => onChoose('professor')}><span className="role-icon teacher-icon"><BookOpen size={21} /></span><span className="role-text"><b>Sou professor(a)</b><small>Quero apoiar as crianças da minha turma</small></span><ArrowRight size={18} /></button></div></section>
    <div className="welcome-bottom"><span>Construído para apoiar, nunca para rotular.</span><span>Privacidade e respeito em cada etapa <ShieldCheck size={15} /></span></div>
  </div>;
}

function Signup({ kind, onBack, onSave }) {
  const parent = kind === 'responsavel';
  function submit(event) { event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget)); onSave(values); }
  return <section className="page-wrap narrow-page"><button className="back-link" onClick={onBack}><ArrowLeft size={16} /> Voltar</button><div className="form-heading"><span className={`step-icon ${parent ? 'parent-icon' : 'teacher-icon'}`}>{parent ? <Heart size={20} /> : <School size={20} />}</span><span className="section-kicker">CRIAR CONTA DE {parent ? 'RESPONSÁVEL' : 'PROFESSOR(A)'}</span><h1>Vamos nos conhecer.</h1><p>Este perfil ajuda a organizar o acompanhamento nesta demonstração.</p></div><form className="panel signup-panel" onSubmit={submit}><div className="field-grid"><label>Nome completo<input name="nome" placeholder="Como podemos chamar você?" required /></label><label>E-mail<input name="email" type="email" placeholder="voce@email.com" required /></label>{parent ? <><label>Telefone <span className="optional">opcional</span><input name="telefone" type="tel" placeholder="(00) 00000-0000" /></label><label>Parentesco<input name="parentesco" placeholder="Ex.: mãe, pai, avó" required /></label></> : <><label>Escola<input name="escola" placeholder="Nome da escola" required /></label><label>Turma<input name="turma" placeholder="Ex.: 2º ano A" required /></label></>}</div><div className="privacy-callout"><ShieldCheck size={18} /><span><b>Privacidade na demonstração</b><small>Informações ficam salvas somente neste navegador. Use dados fictícios.</small></span></div><button className="btn-primary full-button" type="submit">Criar meu espaço <ArrowRight size={17} /></button></form><p className="mock-note">Esta versão não cria uma conta real nem envia seus dados.</p></section>;
}

function Dashboard({ role, data, activeChild, onAddChild, onSelectChild, onNewForm, onTeacherChild }) {
  const teacher = role === 'professor';
  const children = data.children;
  const latest = activeChild && data.assessments.find((item) => item.childId === activeChild.id);
  return <div className="page-wrap dashboard-page"><header className="topbar"><div><span className="section-kicker">{teacher ? 'ESPAÇO DA ESCOLA' : 'ESPAÇO DA FAMÍLIA'}</span><h1>{teacher ? 'Olá, professor(a).' : 'Olá, que bom ter você aqui.'}</h1><p>Um passo de cada vez, com atenção ao que faz cada criança única.</p></div><span className="today-chip"><span className="status-dot" /> Demonstração ativa</span></header>
    {teacher ? <div className="teacher-banner"><div className="banner-symbol"><School size={24} /></div><div><b>Seu espaço de turma</b><p>Na próxima etapa, vamos conectar escola, turma e alunos ao banco SQL. Para esta demonstração, você pode iniciar um perfil fictício de criança.</p></div><button className="btn-secondary" onClick={onTeacherChild}><CircleHelp size={16} /> Como funciona</button></div> : null}
    <div className="dash-section-title"><div><h2>{teacher ? 'Crianças acompanhadas' : 'Seu acompanhamento'}</h2><p>{children.length ? `${children.length} perfil${children.length > 1 ? 's' : ''} nesta demonstração` : 'Comece criando um perfil para a criança.'}</p></div>{!teacher && <button className="btn-secondary" onClick={onAddChild}><Plus size={17} /> Adicionar criança</button>}</div>
    {!children.length ? <div className="empty-card"><span className="empty-illustration">🌱</span><h3>Um novo começo começa por aqui.</h3><p>Crie um perfil simples para iniciar o formulário e construir as primeiras metas de acompanhamento.</p><button className="btn-primary" onClick={onAddChild}><Plus size={17} /> Cadastrar criança</button></div> : <div className="dashboard-grid"><div className="children-list panel"><div className="panel-heading"><span><Users size={17} /> PERFIS</span><button className="icon-button" onClick={onAddChild} title="Adicionar criança"><Plus size={18} /></button></div>{children.map((child) => { const assessment = data.assessments.find((item) => item.childId === child.id); return <button className={`child-row ${activeChild?.id === child.id ? 'active' : ''}`} key={child.id} onClick={() => onSelectChild(child.id)}><span className="child-avatar">{child.name?.slice(0, 1).toUpperCase()}</span><span className="child-row-text"><b>{child.name}</b><small>{ageText(child.birthDate)} {child.interests?.length ? `· ${child.interests.slice(0, 2).join(', ')}` : ''}</small></span><span className={`mini-status ${assessment ? 'has-plan' : ''}`}>{assessment ? 'Plano' : 'Começar'}</span></button>; })}</div>
      <div className="overview-card panel">{activeChild ? <><div className="overview-head"><div><span className="section-kicker">PERFIL DA CRIANÇA</span><h3>{activeChild.name}</h3><p>{ageText(activeChild.birthDate)}{activeChild.interests?.length ? ` · Gosta de ${activeChild.interests.join(', ')}` : ''}</p></div><span className="child-avatar large">{activeChild.name?.slice(0, 1).toUpperCase()}</span></div><div className="overview-divider" />{latest ? <><div className="plan-summary"><span className="summary-icon"><Sparkles size={19} /></span><span><b>{latest.status === 'vigente' ? 'Plano de acompanhamento' : 'Proposta de metas'}</b><small>{latest.metas.length} metas · atualizado agora</small></span><span className={`plan-state ${latest.status === 'vigente' ? 'accepted' : ''}`}>{latest.status === 'vigente' ? 'Em acompanhamento' : 'Para revisar'}</span></div><div className="goal-preview">{latest.metas.slice(0, 2).map((goal) => <div key={goal.id}><span className="goal-check"><Check size={13} /></span><span><b>{goal.nomeDominio}</b><small>{goal.texto}</small></span></div>)}{latest.metas.length === 0 && <p>O formulário não apontou uma área prioritária. Revise as respostas ou registre o que a família deseja acompanhar.</p>}</div><button className="btn-primary full-button" onClick={() => onSelectChild(activeChild.id)}>Ver perfil e metas <ArrowRight size={17} /></button></> : <><div className="start-assessment"><span className="start-icon"><ClipboardList size={23} /></span><h3>Vamos conhecer o momento atual?</h3><p>Responda sobre interesses, rotina e experiências. Não precisa saber tudo: cada observação ajuda a construir um primeiro retrato.</p><button className="btn-primary" onClick={onNewForm}>Começar formulário <ArrowRight size={17} /></button></div><div className="form-meta"><span><span className="tiny-dot green-dot" /> Cerca de 5 minutos</span><span><ShieldCheck size={14} /> Respostas editáveis</span></div></>}</> : null}</div></div>}
    <div className="support-strip"><span className="support-icon"><Heart size={18} /></span><span><b>O desenvolvimento não é uma corrida.</b><small>Este espaço organiza observações e ideias para apoiar conversas entre família e escola.</small></span><button className="quiet-link" onClick={() => window.alert('As sugestões são propostas de demonstração e devem ser revisadas por adultos responsáveis.')}>Saiba mais <ArrowRight size={14} /></button></div>
  </div>;
}

function ChildForm({ child, answers, onAnswer, onBack, onSubmit }) {
  const [step, setStep] = useState(0);
  const groups = [domains.slice(0, 4), domains.slice(4)];
  return <div className="page-wrap form-page"><button className="back-link" onClick={onBack}><ArrowLeft size={16} /> Voltar ao perfil</button><div className="form-top"><div><span className="section-kicker">PERFIL DE {child.name.toUpperCase()}</span><h1>Vamos olhar para o dia a dia.</h1><p>Não existe resposta certa. Conte o que você observa, no ritmo de vocês.</p></div><div className="progress-box"><span>ETAPA {step + 1} DE 2</span><div className="progress-track"><i style={{ width: `${(step + 1) * 50}%` }} /></div></div></div>
    <div className="form-layout"><div className="question-column">{step === 0 ? <section className="panel intro-panel"><div className="question-index">01</div><div><span className="section-kicker">UM POUCO SOBRE A CRIANÇA</span><h2>O que faz os olhos dela brilharem?</h2><p>Interesses, brincadeiras, assuntos favoritos ou atividades que dão alegria.</p><div className="interest-chips">{child.interests?.length ? child.interests.map((interest) => <span key={interest}>✦ {interest}</span>) : <span>Conteúdos informados no perfil</span>}</div></div></section> : <section className="panel intro-panel"><div className="question-index">02</div><div><span className="section-kicker">OBSERVAÇÕES DA FAMÍLIA</span><h2>O que acontece na rotina?</h2><p>Escolha a opção que mais se aproxima do que você observa hoje. “Não sei” também é uma resposta importante.</p></div></section>}
      <div className="domain-list">{groups[step].map((domain, index) => <article className="domain-card panel" key={domain.id}><div className="domain-head"><span className="domain-emoji">{domain.icon}</span><span className="domain-num">{String(step * 4 + index + 1).padStart(2, '0')}</span><span className="domain-title">{domain.label}</span></div><p>{domain.question}</p><div className="answer-options">{scale.map(([value, label]) => <button key={value} className={`answer-option ${answers[domain.id] === value ? 'checked' : ''}`} onClick={() => onAnswer(domain.id, value)}><span className="radio-dot">{answers[domain.id] === value && <i />}</span>{label}</button>)}</div><label className="note-field">Quer contar um exemplo? <span className="optional">opcional</span><textarea rows="2" value={answers[`nota_${domain.id}`] || ''} onChange={(event) => onAnswer(`nota_${domain.id}`, event.target.value)} placeholder="Uma situação do dia a dia ajuda a dar contexto…" /></label></article>)}</div>
      <div className="form-actions">{step > 0 && <button className="btn-secondary" onClick={() => setStep(step - 1)}><ArrowLeft size={16} /> Etapa anterior</button>}{step === 0 ? <button className="btn-primary" onClick={() => setStep(1)}>Continuar <ArrowRight size={16} /></button> : <button className="btn-primary" onClick={onSubmit}><Sparkles size={16} /> Organizar respostas e propor metas</button>}</div>
      </div><aside className="form-aside"><div className="aside-card"><span className="aside-illustration">🌿</span><h3>Olhe para o contexto.</h3><p>Uma habilidade pode aparecer em casa e não na escola, ou depender do dia, do ambiente e do apoio disponível.</p></div><div className="aside-card tinted"><ShieldCheck size={18} /><h3>Sem julgamentos</h3><p>Este formulário organiza observações. Não é uma avaliação clínica nem define o potencial da criança.</p></div><div className="aside-ref"><span>REFERENCIAL</span><p>Domínios de desenvolvimento e participação do projeto.</p></div></aside></div>
  </div>;
}

function Goals({ child, assessment, onBack, onAccept, onDone, onEdit }) {
  if (!assessment) return <EmptyChild onAdd={onBack} />;
  const approved = assessment.status === 'vigente';
  return <div className="page-wrap goals-page"><button className="back-link" onClick={onBack}><ArrowLeft size={16} /> Voltar à visão geral</button><div className="goals-hero"><span className="goal-spark"><Sparkles size={22} /></span><div><span className="section-kicker">{approved ? 'PLANO EM ACOMPANHAMENTO' : 'PRIMEIRA PROPOSTA'}</span><h1>Um caminho para {child.name}.</h1><p>Uma proposta inicial, construída a partir das observações da família. Revise e ajuste antes de acompanhar.</p></div><button className="btn-secondary" onClick={onEdit}>Editar respostas</button></div><div className="demo-warning"><ShieldCheck size={18} /><span><b>Proposta de demonstração</b><small>As metas abaixo são exemplos gerados localmente. A integração com o modelo e validação das referências legais ainda será feita.</small></span></div>
    <div className="goal-content"><section className="panel profile-summary"><div className="summary-heading"><div><span className="section-kicker">RETRATO INICIAL</span><h2>O que já sabemos</h2></div><span className="profile-badge"><Baby size={15} /> {ageText(child.birthDate)}</span></div><div className="strength-box"><span>🌟</span><div><b>Interesses que podem abrir caminhos</b><p>{child.interests?.length ? child.interests.join(', ') : 'Ainda não informado. Converse com a criança e registre o que desperta curiosidade.'}</p></div></div><div className="answer-overview"><h3>Observações por área</h3><div className="answer-grid">{domains.map((domain) => { const answer = assessment.respostas_formulario[domain.id] || 'nao_sei'; return <div key={domain.id}><span>{domain.icon} {domain.label}</span><b className={`answer-badge ${answer}`}>{scale.find(([value]) => value === answer)?.[1]}</b></div>; })}</div></div></section>
      <section className="goals-section"><div className="goals-section-head"><div><span className="section-kicker">PRÓXIMOS PASSOS</span><h2>Metas para conversar juntos</h2></div><span className="goals-count">{assessment.metas.length} propostas</span></div>{assessment.metas.length ? assessment.metas.map((goal, index) => <article className="goal-card panel" key={goal.id}><div className="goal-card-top"><span className="goal-number">0{index + 1}</span><span className="domain-tag">{goal.nomeDominio}</span><span className={`goal-status ${goal.estado}`}>{goal.estado === 'em_acompanhamento' ? 'Em acompanhamento' : 'Proposta'}</span></div><h3>{goal.texto}</h3><div className="goal-detail"><span><Home size={15} /> Casa ou escola, conforme a rotina</span><span><MessageCircle size={15} /> Combinar com a criança</span><span><ClipboardList size={15} /> Rever em 2 semanas</span></div><div className="goal-note"><b>Como observar:</b> anotem quando a oportunidade aconteceu e que tipo de apoio ajudou, sem exigir que todos os dias sejam iguais.</div></article>) : <div className="no-goals panel"><span>🌼</span><h3>O formulário não destacou uma meta prioritária.</h3><p>Isso pode significar que faltam observações ou que vocês preferem começar por outra área. Conversem e editem as respostas.</p></div>}
        <div className="goal-actions">{!approved ? <><button className="btn-secondary" onClick={onEdit}>Revisar respostas</button><button className="btn-primary" onClick={onAccept}><Check size={16} /> Confirmar para acompanhar</button></> : <button className="btn-primary" onClick={onDone}><Check size={16} /> Registrar acompanhamento</button>}</div>
      </section></div><div className="goals-footnote">O perfil é um registro de observações contextualizadas. Não substitui a avaliação de profissionais nem deve ser usado para limitar oportunidades da criança.</div>
  </div>;
}

function ChildModal({ onClose, onSave }) {
  function submit(event) { event.preventDefault(); onSave(Object.fromEntries(new FormData(event.currentTarget))); }
  return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><form className="modal-card" onSubmit={submit}><div className="modal-header"><span className="role-icon parent-icon"><Baby size={21} /></span><button type="button" className="icon-button" onClick={onClose}><X size={18} /></button></div><span className="section-kicker">NOVO PERFIL</span><h2>Vamos conhecer a criança.</h2><p>Use um nome fictício para esta demonstração.</p><label>Como podemos chamá-la?<input name="name" placeholder="Ex.: Nina" required autoFocus /></label><label>Data de nascimento<input name="birthDate" type="date" required /></label><label>O que ela gosta? <span className="optional">separado por vírgulas</span><input name="interests" placeholder="Ex.: música, animais, água" /></label><button className="btn-primary full-button" type="submit">Salvar e continuar <ArrowRight size={16} /></button></form></div>;
}

function EmptyChild({ onAdd }) { return <div className="page-wrap"><div className="empty-card"><span className="empty-illustration">🌱</span><h3>Vamos começar pelo perfil.</h3><p>Cadastre uma criança para seguir com o formulário de observações.</p><button className="btn-primary" onClick={onAdd}><Plus size={17} /> Criar perfil</button></div></div>; }

function goalFor(domain, child) {
  const name = child.name || 'a criança';
  const goals = {
    COM_R: `Experimentar orientações curtas durante uma atividade que ${name} escolher, observando quais palavras, gestos ou imagens ajudam a compreender.`,
    COM_E: `Criar oportunidades para ${name} expressar escolhas e necessidades por fala, gesto, imagem ou outro meio confortável.`,
    SOC: `Combinar uma brincadeira breve de interesse de ${name}, respeitando momentos de participação e de pausa.`,
    COG: `Explorar uma atividade de interesse de ${name} em pequenos passos, valorizando tentativas e diferentes formas de resolver.`,
    AUT: `Oferecer a ${name} uma escolha e o tempo necessário para participar de uma etapa da rotina com o apoio que preferir.`,
    REG: `Observar com ${name} quais sinais ou apoios deixam uma transição mais previsível e confortável.`,
    ATE: `Experimentar dividir uma atividade escolhida por ${name} em etapas visíveis e registrar qual apoio facilita continuar.`,
    SEN: `Identificar com ${name} um ajuste sensorial simples no ambiente e observar se aumenta conforto e participação.`,
  };
  return goals[domain] || 'Escolher junto com a criança uma pequena oportunidade de participação e observar qual apoio funciona melhor.';
}

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
