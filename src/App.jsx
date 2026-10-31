import { useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft, ArrowRight, Baby, BookOpen, Check, ChevronDown, CircleHelp,
  ClipboardList, Heart, Home, MessageCircle, Plus, School, ShieldCheck,
  Sparkles, Users, X,
} from 'lucide-react';
import {
  ANSWER_LABELS, AREA_PROMPTS, CONDITIONS, DOMAIN_META, buildQuestionnaire,
} from './questionnaire.js';

const STORE = 'placeholder-demo-v1';
const emptyState = { parents: [], teachers: [], children: [], assessments: [] };

function readStore() {
  try { return { ...emptyState, ...JSON.parse(localStorage.getItem(STORE) || '{}') }; }
  catch { return emptyState; }
}

function App() {
  const [data, setData] = useState(readStore);
  const [screen, setScreen] = useState('home');
  const [role, setRole] = useState('responsavel');
  const [activeId, setActiveId] = useState(null);
  const [formEdit, setFormEdit] = useState(null);
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
    setActiveId(child.id); setModal(''); setScreen('form');
  }

  async function generateAssessment(formPayload) {
    const { perfil, respostas, dominios, versao, informante } = formPayload;
    const questionnaire = buildQuestionnaire(perfil.idade_meses, perfil.ano_escolar);
    const metas = questionnaire.dominios.filter((domain) => {
      const context = dominios[domain.id] || {};
      const flagged = domain.perguntas.some((question) => ['nao', 'as_vezes'].includes(respostas[question.id]?.resposta));
      return flagged || Boolean(context.desafios?.trim()) || Boolean(context.pontos_fortes?.trim());
    }).slice(0, 3).map((item, index) => ({
      id: `m${index + 1}`,
      dominio: item.id,
      nomeDominio: item.nome,
      horizonte: index === 0 ? 'curto' : 'medio',
      texto: goalFor(item.id, activeChild, dominios[item.id], perfil, !dominios[item.id]?.desafios?.trim() && !item.perguntas.some((question) => ['nao', 'as_vezes'].includes(respostas[question.id]?.resposta))),
      estado: 'proposta',
    }));
    if (!metas.length && perfil.prioridades?.trim()) metas.push({
      id: 'm1', dominio: 'CTX', nomeDominio: DOMAIN_META.CTX.label, horizonte: 'curto',
      texto: `Combinar um próximo passo a partir da prioridade da família: ${perfil.prioridades.trim()}`,
      estado: 'proposta',
    });

    const localPayload = { versao, informante, perfil, respostas, dominios };
    let backendResult = null;
    let backendStatus = 'local';
    let backendNotice = '';
    try {
      const response = await fetch('/api/formularios', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...localPayload, consentimento: true }),
      });
      if (response.ok) { backendResult = await response.json(); backendStatus = 'registrado'; }
      else { backendNotice = 'O backend recusou o envio; as respostas ficaram salvas apenas nesta demonstração.'; }
    } catch {
      backendNotice = 'Backend indisponível; as respostas ficaram salvas apenas neste navegador.';
    }
    const proposal = {
      id: backendResult?.id || crypto.randomUUID(), childId: activeChild.id, tipo: 'inicial', status: 'proposta',
      respostas_formulario: respostas,
      perfil: { ...perfil, resumo: `Relato inicial da família sobre ${activeChild.name}. Informações de saúde e condições são autorrelatadas.` },
      dominios, niveis: Object.fromEntries(questionnaire.dominios.map((item) => [item.id, null])),
      metas, payload: localPayload, backendStatus, backendNotice, createdAt: new Date().toISOString(),
    };
    setData((current) => ({ ...current, assessments: [proposal, ...current.assessments.filter((item) => item.childId !== activeChild.id)] }));
    setFormEdit(null);
    if (backendNotice) setNotice(backendNotice);
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
        {screen === 'dashboard' && <Dashboard role={role} data={data} activeChild={activeChild} onAddChild={() => setModal('child')} onSelectChild={(id) => { setActiveId(id); setScreen(data.assessments.some((a) => a.childId === id) ? 'goals' : 'form'); }} onNewForm={() => { setFormEdit(null); setScreen('form'); }} onTeacherChild={() => setNotice('A vinculação de turma e alunos será conectada ao banco na próxima etapa.')} />}
        {screen === 'form' && activeChild && <ChildForm key={formEdit ? 'editing' : activeChild.id} initialPayload={formEdit} child={activeChild} relationship={role === 'professor' ? 'Professor(a)' : data.parents.at(-1)?.parentesco || ''} informante={role} onBack={() => setScreen('dashboard')} onSubmit={generateAssessment} />}
        {screen === 'form' && !activeChild && <EmptyChild onAdd={() => setModal('child')} />}
        {screen === 'goals' && activeChild && <Goals child={activeChild} assessment={activeAssessment} onBack={() => setScreen('dashboard')} onAccept={acceptAssessment} onDone={markDemoDone} onEdit={() => { setFormEdit(activeAssessment?.payload || null); setScreen('form'); }} />}
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

function ChildForm({ child, initialPayload, relationship, informante, onBack, onSubmit }) {
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
    try { await onSubmit(payload); }
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
      <div className="form-actions"><div><button className="btn-primary" onClick={startObservations}>Começar observações <ArrowRight size={16} /></button><small className="field-hint">Obrigatórios: nome, idade em meses, vínculo e prioridade da família.</small></div></div>
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
        <label className="consent-box"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /><span><b>Confirmo que revisei as informações e autorizo o registro local desta demonstração.</b><small>Inclui relatos de desenvolvimento e, se preenchidas, informações de saúde. Use somente dados fictícios nesta versão.</small></span></label>
        <div className="questionnaire-notice"><ShieldCheck size={17} /> As respostas são relatos familiares, não avaliação clínica validada. O sistema não gera diagnóstico nem classificação automática. Metas e atividades futuras devem ser rascunhos revisados por adultos responsáveis.</div>
        <div className="form-actions"><button className="btn-secondary" onClick={() => go(14)}><ArrowLeft size={16} /> Voltar</button><button className="btn-primary" disabled={!consent || busy} onClick={finish}>{busy ? 'Registrando…' : 'Concluir formulário'} <Check size={16} /></button></div>
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

function Goals({ child, assessment, onBack, onAccept, onDone, onEdit }) {
  if (!assessment) return <EmptyChild onAdd={onBack} />;
  const approved = assessment.status === 'vigente';
  const age = Number(assessment.perfil?.idade_meses) || ageMonthsFromBirth(child.birthDate);
  const questionnaire = buildQuestionnaire(age, Number(assessment.perfil?.ano_escolar) || null);
  const reportedConditions = (assessment.perfil?.condicoes_relatadas || []).map((id) => CONDITIONS.find(([conditionId]) => conditionId === id)?.[1] || assessment.perfil?.outra_condicao).filter(Boolean);
  return <div className="page-wrap goals-page"><button className="back-link" onClick={onBack}><ArrowLeft size={16} /> Voltar à visão geral</button><div className="goals-hero"><span className="goal-spark"><Sparkles size={22} /></span><div><span className="section-kicker">{approved ? 'PLANO EM ACOMPANHAMENTO' : 'PRIMEIRA PROPOSTA'}</span><h1>Um caminho para {child.name}.</h1><p>Uma proposta inicial, construída a partir das observações da família. Revise e ajuste antes de acompanhar.</p></div><button className="btn-secondary" onClick={onEdit}>Editar respostas</button></div><div className="demo-warning"><ShieldCheck size={18} /><span><b>Proposta de demonstração</b><small>As metas abaixo são exemplos gerados localmente. A integração com o modelo e validação das referências legais ainda será feita.</small></span></div>
    <div className="goal-content"><section className="panel profile-summary"><div className="summary-heading"><div><span className="section-kicker">RETRATO INICIAL</span><h2>O que já sabemos</h2></div><span className="profile-badge"><Baby size={15} /> {ageText(child.birthDate)}</span></div><div className="strength-box"><span>🌟</span><div><b>Interesses que podem abrir caminhos</b><p>{assessment.perfil?.interesses || child.interests?.join(', ') || 'Ainda não informado. Converse com a criança e registre o que desperta curiosidade.'}</p></div></div>{reportedConditions.length > 0 && <div className="health-summary"><b>Condições relatadas pela família</b><p>{reportedConditions.join('; ')}</p><small>Relato não verificado. Não determina metas nem permite inferir habilidades.</small></div>}{assessment.perfil?.documento_comprobatorio === 'sim' && <div className="health-summary"><b>Documento informado</b><p>{assessment.perfil.tipo_documento || 'Tipo não especificado'} · não anexado</p></div>}<div className="answer-overview"><h3>Observações nas 14 áreas</h3><div className="answer-grid">{questionnaire.dominios.map((domain) => {
      const questions = domain.perguntas;
      const counts = questions.reduce((accumulator, question) => {
        const answer = assessment.respostas_formulario?.[question.id]?.resposta;
        if (answer) accumulator[answer] = (accumulator[answer] || 0) + 1;
        return accumulator;
      }, {});
      const labels = Object.entries(counts).map(([answer, count]) => `${count} ${ANSWER_LABELS[answer]}`).join(' · ');
      return <div key={domain.id}><span>{DOMAIN_META[domain.id]?.icon} {domain.nome}</span><b className="answer-badge contextual-answer">{labels || 'Relato contextual'}</b></div>;
    })}</div></div></section>
      <section className="goals-section"><div className="goals-section-head"><div><span className="section-kicker">PRÓXIMOS PASSOS</span><h2>Metas para conversar juntos</h2></div><span className="goals-count">{assessment.metas.length} propostas</span></div>{assessment.metas.length ? assessment.metas.map((goal, index) => <article className="goal-card panel" key={goal.id}><div className="goal-card-top"><span className="goal-number">0{index + 1}</span><span className="domain-tag">{goal.nomeDominio}</span><span className={`goal-status ${goal.estado}`}>{goal.estado === 'em_acompanhamento' ? 'Em acompanhamento' : 'Proposta'}</span></div><h3>{goal.texto}</h3><div className="goal-detail"><span><Home size={15} /> Casa ou escola, conforme a rotina</span><span><MessageCircle size={15} /> Combinar com a criança</span><span><ClipboardList size={15} /> Rever em 2 semanas</span></div><div className="goal-note"><b>Como observar:</b> anotem quando a oportunidade aconteceu e que tipo de apoio ajudou, sem exigir que todos os dias sejam iguais.</div></article>) : <div className="no-goals panel"><span>🌼</span><h3>O formulário não destacou uma meta prioritária.</h3><p>Isso pode significar que faltam observações ou que vocês preferem começar por outra área. Conversem e editem as respostas.</p></div>}
        <div className="goal-actions">{!approved ? <><button className="btn-secondary" onClick={onEdit}>Revisar respostas</button><button className="btn-primary" onClick={onAccept}><Check size={16} /> Confirmar para acompanhar</button></> : <button className="btn-primary" onClick={onDone}><Check size={16} /> Registrar acompanhamento</button>}</div>
      </section></div><div className="goals-footnote">O perfil é um registro de observações contextualizadas. Não substitui a avaliação de profissionais nem deve ser usado para limitar oportunidades da criança.</div>
    <section className="reported-areas"><span className="section-kicker">RELATOS POR ÁREA</span><h2>O que a família compartilhou</h2>{questionnaire.dominios.map((domain) => {
      const context = assessment.dominios?.[domain.id] || {};
      return <details className="review-domain" key={domain.id}><summary><span>{DOMAIN_META[domain.id]?.icon} {domain.nome}</span><small>{context.contexto || 'Contexto não informado'}</small></summary><p><b>Pontos fortes e interesses:</b> {context.pontos_fortes || 'Não informado'}</p><p><b>Desafios e apoios necessários:</b> {context.desafios || (context.nao_sei ? 'Ainda não sabe informar' : 'Não informado')}</p><p><b>O que ajuda ou já foi tentado:</b> {context.apoios || 'Não informado'}</p><p><b>Outros comentários:</b> {context.observacoes || 'Não informado'}</p></details>;
    })}</section>
  </div>;
}

function ChildModal({ onClose, onSave }) {
  function submit(event) { event.preventDefault(); onSave(Object.fromEntries(new FormData(event.currentTarget))); }
  return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><form className="modal-card" onSubmit={submit}><div className="modal-header"><span className="role-icon parent-icon"><Baby size={21} /></span><button type="button" className="icon-button" onClick={onClose}><X size={18} /></button></div><span className="section-kicker">NOVO PERFIL</span><h2>Vamos conhecer a criança.</h2><p>Use um nome fictício para esta demonstração.</p><label>Como podemos chamá-la?<input name="name" placeholder="Ex.: Nina" required autoFocus /></label><label>Data de nascimento<input name="birthDate" type="date" required /></label><label>O que ela gosta? <span className="optional">separado por vírgulas</span><input name="interests" placeholder="Ex.: música, animais, água" /></label><button className="btn-primary full-button" type="submit">Salvar e continuar <ArrowRight size={16} /></button></form></div>;
}

function EmptyChild({ onAdd }) { return <div className="page-wrap"><div className="empty-card"><span className="empty-illustration">🌱</span><h3>Vamos começar pelo perfil.</h3><p>Cadastre uma criança para seguir com o formulário de observações.</p><button className="btn-primary" onClick={onAdd}><Plus size={17} /> Criar perfil</button></div></div>; }

function goalFor(domain, child, context = {}, profile = {}, strengthFocus = false) {
  const name = child.name || 'a criança';
  if (strengthFocus && context.pontos_fortes?.trim()) {
    return `Criar uma oportunidade agradável para ${name} explorar e compartilhar uma habilidade ou interesse já observado, respeitando seu ritmo e oferecendo escolhas. A família descreveu: “${context.pontos_fortes.trim().slice(0, 180)}${context.pontos_fortes.trim().length > 180 ? '…' : ''}”`;
  }
  const goals = {
    COM_R: `Experimentar uma instrução curta em atividade escolhida por ${name}, oferecendo gesto ou apoio visual se ajudar e observando como ela compreende.`,
    COM_E: `Criar oportunidades para ${name} expressar escolhas e necessidades pela forma de comunicação que preferir, sem exigir fala.`,
    FAL: `Oferecer uma brincadeira de interesse de ${name} com pausas e turnos, valorizando todos os meios que ela usa para se comunicar.`,
    SOC: `Combinar uma atividade compartilhada de interesse de ${name}, com possibilidade de observar, participar e fazer pausas.`,
    BRI: `Seguir o interesse de ${name} em uma brincadeira e acrescentar uma pequena possibilidade de escolha ou exploração.`,
    COG: `Explorar um desafio simples ligado ao interesse de ${name}, dividindo-o em passos e valorizando diferentes maneiras de resolver.`,
    MOT_A: `Escolher com ${name} uma atividade de movimento segura e agradável, adaptando o espaço e o nível de ajuda conforme necessário.`,
    MOT_F: `Oferecer a ${name} materiais acessíveis para uma atividade manual que ela escolha, sem exigir um resultado único.`,
    AUT: `Oferecer a ${name} uma escolha e tempo para participar de uma etapa da rotina, combinando apenas o apoio de que precisar.`,
    REG: `Observar com ${name} quais sinais ou apoios tornam uma transição mais previsível e confortável, interrompendo se aumentar o desconforto.`,
    ATE: `Experimentar dividir uma atividade escolhida por ${name} em etapas visíveis e observar qual apoio facilita começar ou continuar.`,
    SEN: `Identificar com ${name} um ajuste sensorial simples no ambiente e observar se aumenta conforto e participação.`,
    SAU: `Conversar com a equipe que acompanha ${name} sobre a informação de saúde compartilhada e como ela se relaciona à rotina e à participação.`,
    CTX: `Combinar com a família e a escola um ajuste possível no contexto de ${name}, observando se facilita sua participação.`,
  };
  const text = goals[domain] || `Escolher junto com ${name} uma pequena oportunidade de participação e observar qual apoio funciona melhor.`;
  const strength = context.pontos_fortes?.trim();
  const helpfulSupport = context.apoios?.trim();
  const priority = profile.prioridades?.trim();
  const additions = [];
  if (strength) additions.push(`Partir do ponto forte/interesse que a família descreveu: “${strength.slice(0, 180)}${strength.length > 180 ? '…' : ''}”`);
  if (helpfulSupport) additions.push(`Considerar o apoio já tentado: “${helpfulSupport.slice(0, 160)}${helpfulSupport.length > 160 ? '…' : ''}”`);
  if (priority && !strength && !helpfulSupport) additions.push(`Manter como referência a prioridade familiar: “${priority.slice(0, 180)}${priority.length > 180 ? '…' : ''}”`);
  return additions.length ? `${text} ${additions.join(' ')}` : text;
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
