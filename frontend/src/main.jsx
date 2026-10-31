import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';
import './form-extra.css';

const CONDITIONS = [
  ['tea', 'TEA (inclui diagnóstico anteriormente chamado síndrome de Asperger)'],
  ['tdah', 'TDAH'], ['down', 'Síndrome de Down'],
  ['deficiencia_intelectual', 'Deficiência intelectual ou cognitiva'],
  ['atraso_global', 'Atraso global do desenvolvimento'],
  ['linguagem_aprendizagem', 'Condição de linguagem ou aprendizagem'],
  ['motora', 'Condição motora ou física'], ['genetica_outra', 'Condição genética ou outra condição de desenvolvimento'],
  ['em_investigacao', 'Em investigação / sem diagnóstico concluído'], ['prefiro_nao_informar', 'Prefiro não informar'],
];
const OPTIONS = [
  ['COM_R', 'Compreensão', 'Em quais situações a criança entende melhor? Há diferença entre instruções faladas, gestos, imagens ou rotinas conhecidas?'],
  ['COM_E', 'Comunicação expressiva', 'Como comunica desejos, escolhas, sentimentos ou ideias? Que recursos usa, como fala, gestos, olhar, imagens ou comunicação alternativa?'],
  ['FAL', 'Fala e verbalização', 'Se fala é uma forma usada pela criança, como são os sons, palavras e frases? Se não usa fala, que formas de comunicação funcionam?'],
  ['SOC', 'Interação social', 'Como demonstra interesse por outras pessoas e participa com familiares, colegas ou adultos conhecidos?'],
  ['BRI', 'Brincadeira', 'Que brincadeiras, temas ou objetos despertam interesse? Como explora, imagina, compartilha ou prefere brincar?'],
  ['COG', 'Cognição e aprendizagem', 'O que desperta curiosidade? Como aprende algo novo, resolve problemas, lembra etapas ou demonstra o que sabe?'],
  ['MOT_A', 'Movimento amplo', 'Como participa de movimentos e atividades físicas? Que adaptações ou condições do espaço fazem diferença?'],
  ['MOT_F', 'Movimento fino', 'Como usa as mãos em brincadeiras, alimentação, desenho, escrita ou objetos? Quais materiais ou adaptações ajudam?'],
  ['AUT', 'Autonomia e autocuidado', 'Em quais rotinas de autocuidado participa? Quais etapas faz e que apoio respeita sua autonomia?'],
  ['REG', 'Regulação e comportamento', 'Quais situações, mudanças ou demandas podem ser difíceis? Como demonstra que precisa de pausa, ajuda ou previsibilidade?'],
  ['ATE', 'Atenção e funções executivas', 'O que ajuda a começar, manter-se envolvida, alternar etapas ou terminar uma atividade?'],
  ['SEN', 'Processamento sensorial', 'Quais sons, luzes, cheiros, texturas, sabores ou movimentos parecem confortáveis, interessantes ou difíceis?'],
  ['SAU', 'Saúde e corpo', 'Há aspectos de sono, alimentação, visão, audição, mobilidade ou saúde que afetam a rotina e que deseja compartilhar?'],
  ['CTX', 'Contexto e participação', 'Como os ambientes, horários, relações e apoios de casa, escola e comunidade influenciam a participação?'],
];
const AREA_PROMPTS = Object.fromEntries(OPTIONS.map(([id, , prompt]) => [id, prompt]));
const emptyContext = () => ({ relato: '', pontos_fortes: '', desafios: '', apoios: '', observacoes: '', nao_sei: false, contexto: 'nao_sei' });

function App() {
  const [profile, setProfile] = useState({ apelido: '', idade_meses: '', ano_escolar: '', vinculo: '', interesses: '', prioridades: '', idiomas: '', prematuridade: 'nao_sei', perda_habilidades: 'nao_sei', condicoes_relatadas: [], outra_condicao: '', documento_comprobatorio: 'nao_sei', tipo_documento: '', observacoes_saude: '' });
  const [schema, setSchema] = useState(null);
  const [step, setStep] = useState(-1);
  const [answers, setAnswers] = useState({});
  const [contexts, setContexts] = useState({});
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const current = schema?.dominios[step];
  const ctx = current ? (contexts[current.id] || emptyContext()) : null;
  const change = (key, value) => setProfile((previous) => ({ ...previous, [key]: value }));
  const changeContext = (key, value) => setContexts((previous) => ({ ...previous, [current.id]: { ...ctx, [key]: value } }));
  const go = (next) => { setError(''); setStep(next); window.scrollTo({ top: 0, behavior: 'smooth' }); };

  async function start(event) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const query = new URLSearchParams({ idade_meses: profile.idade_meses });
      if (profile.ano_escolar) query.set('ano_escolar', profile.ano_escolar);
      const response = await fetch(`/api/questionario?${query}`);
      if (!response.ok) throw new Error('Não foi possível carregar as perguntas. Confira idade e ano escolar.');
      setSchema(await response.json()); setAnswers({}); setContexts({}); setConsent(false); go(0);
    } catch (requestError) { setError(requestError.message || 'Não foi possível conectar ao formulário.'); }
    finally { setBusy(false); }
  }

  function advance(event) {
    event.preventDefault();
    const missing = current.perguntas.find((question) => !answers[question.id]?.resposta);
    if (missing) { setError('Responda aos itens desta área ou escolha “Não sei”.'); return; }
    if (!ctx.nao_sei && ![ctx.relato, ctx.pontos_fortes, ctx.desafios, ctx.apoios, ctx.observacoes].some((value) => value.trim())) {
      setError('Conte ao menos uma observação ou marque “Ainda não sei informar”.'); return;
    }
    go(step === 13 ? 14 : step + 1);
  }

  async function send() {
    if (!consent) { setError('Confirme a revisão e o registro local para continuar.'); return; }
    setBusy(true); setError('');
    const body = {
      informante: 'responsavel', versao: schema.versao,
      perfil: { ...profile, idade_meses: Number(profile.idade_meses), ano_escolar: profile.ano_escolar ? Number(profile.ano_escolar) : null },
      respostas: answers, dominios: Object.fromEntries(schema.dominios.map((domain) => [domain.id, contexts[domain.id] || emptyContext()])), consentimento: true,
    };
    try {
      const response = await fetch('/api/formularios', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (!response.ok) { const detail = await response.json(); throw new Error(typeof detail.detail === 'string' ? detail.detail : 'Confira os campos e tente novamente.'); }
      setResult(await response.json());
    } catch (requestError) { setError(requestError.message || 'Não foi possível registrar as respostas.'); }
    finally { setBusy(false); }
  }

  function download() {
    const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a'); link.href = url; link.download = 'formulario-inicial.json'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  const conditionsLabel = profile.condicoes_relatadas.map((id) => CONDITIONS.find(([condition]) => condition === id)?.[1]).filter(Boolean).join('; ') || 'Não informado';
  return <><header><a href="/" className="brand"><span className="logo">✳</span> PLACEHOLDER</a><span className="tag">Conhecer • Acolher • Acompanhar</span></header><main><aside><span className="eyebrow">UM OLHAR PARA CADA CRIANÇA</span><h1>Todo caminho começa com escuta.</h1><p>Conte como a criança aprende, se comunica e participa. Suas observações ajudam a construir próximos passos possíveis.</p><div className="aside-note">Não há respostas certas ou erradas.<br />Você pode dizer que ainda não sabe.</div><ol className="steps"><li className={step === -1 ? 'active' : ''}>01 &nbsp; Conhecendo a criança</li><li className={step >= 0 && step < 14 ? 'active' : ''}>02 &nbsp; Um olhar sobre 14 áreas</li><li className={step === 14 ? 'active' : ''}>03 &nbsp; Revisar e compartilhar</li></ol><small>Protótipo local: use dados fictícios nesta demonstração.</small></aside><section className="card">
    {error && <div className="error" role="alert">{error}</div>}
    {result ? <><span className="eyebrow">PRIMEIRO PASSO CONCLUÍDO</span><h2>Obrigado por compartilhar.</h2><p>As respostas foram registradas no backend local e estão organizadas para o agente. Avaliação, metas e plano ainda não foram gerados.</p><div className="notice">14 áreas registradas · {Object.keys(answers).length} itens respondidos · Status: {result.status}</div><button onClick={download}>Baixar respostas estruturadas</button><p><small>Guarde o arquivo apenas com pessoas autorizadas a acompanhar a criança.</small></p><button className="secondary" onClick={() => { setResult(null); setSchema(null); setAnswers({}); setContexts({}); go(-1); }}>Iniciar outro formulário</button></>
      : step === -1 ? <form onSubmit={start}><span className="eyebrow">01 / CONHECENDO A CRIANÇA</span><h2>Vamos começar pelo cotidiano.</h2><p>Este formulário organiza relatos para apoiar o acompanhamento. Ele não produz diagnóstico clínico.</p><div className="grid">
        <label className="field">Como podemos chamar a criança? *<input required maxLength="60" value={profile.apelido} onChange={(event) => change('apelido', event.target.value)} /></label>
        <label className="field">Seu vínculo com a criança *<input required maxLength="60" value={profile.vinculo} placeholder="Mãe, pai, avó, responsável…" onChange={(event) => change('vinculo', event.target.value)} /></label>
        <label className="field">Idade em meses completos *<input type="number" min="0" max="131" required value={profile.idade_meses} onChange={(event) => change('idade_meses', event.target.value)} /><small>Ex.: 7 anos = 84 meses; até 10 anos e 11 meses.</small></label>
        <label className="field">Ano escolar atual<select value={profile.ano_escolar} onChange={(event) => change('ano_escolar', event.target.value)}><option value="">Não se aplica / não sei</option>{[1, 2, 3, 4, 5].map((year) => <option key={year} value={year}>{year}º ano</option>)}</select></label>
        <label className="field">Línguas usadas em casa<input maxLength="200" value={profile.idiomas} onChange={(event) => change('idiomas', event.target.value)} /></label>
        <label className="field">Nasceu prematuramente?<select value={profile.prematuridade} onChange={(event) => change('prematuridade', event.target.value)}><option value="nao_sei">Não sei</option><option value="sim">Sim</option><option value="nao">Não</option></select></label>
      </div><label className="field">Interesses, brincadeiras e pontos fortes<textarea maxLength="2000" value={profile.interesses} onChange={(event) => change('interesses', event.target.value)} placeholder="O que desperta curiosidade? Em quais momentos ela se sente confiante ou feliz?" /></label><label className="field">O que vocês mais gostariam de apoiar agora? *<textarea required maxLength="2000" value={profile.prioridades} onChange={(event) => change('prioridades', event.target.value)} /></label><label className="field">Deixou de fazer algo que já conseguia fazer?<select value={profile.perda_habilidades} onChange={(event) => change('perda_habilidades', event.target.value)}><option value="nao_sei">Não sei</option><option value="nao">Não</option><option value="sim">Sim</option></select></label>{profile.perda_habilidades === 'sim' && <p className="notice">Converse com o profissional de saúde que acompanha a criança sobre essa mudança. Este formulário não substitui avaliação profissional.</p>}
      <div className="health-intake"><span className="eyebrow">INFORMAÇÕES DE SAÚDE E APOIOS · OPCIONAL</span><h3>Há uma condição ou diagnóstico relatado?</h3><p>Marcar uma opção registra o relato da família; não confirma diagnóstico nem permite inferir capacidades ou necessidades.</p><div className="condition-options">{CONDITIONS.map(([id, label]) => <label key={id}><input type="checkbox" checked={profile.condicoes_relatadas.includes(id)} onChange={(event) => { const next = event.target.checked ? id === 'prefiro_nao_informar' ? [id] : [...profile.condicoes_relatadas.filter((item) => item !== 'prefiro_nao_informar'), id] : profile.condicoes_relatadas.filter((item) => item !== id); change('condicoes_relatadas', next); }} />{label}</label>)}</div>{profile.condicoes_relatadas.includes('genetica_outra') && <label className="field">Se desejar, informe outra condição ou termo usado pela equipe<textarea maxLength="500" value={profile.outra_condicao} onChange={(event) => change('outra_condicao', event.target.value)} /></label>}<div className="grid"><label className="field">Há laudo, atestado ou relatório que a família possa consultar?<select value={profile.documento_comprobatorio} onChange={(event) => change('documento_comprobatorio', event.target.value)}><option value="nao_sei">Não sei / prefiro não informar</option><option value="sim">Sim</option><option value="nao">Não</option></select></label>{profile.documento_comprobatorio === 'sim' && <label className="field">Tipo de documento<select value={profile.tipo_documento} onChange={(event) => change('tipo_documento', event.target.value)}><option value="">Selecione</option>{['Laudo ou atestado médico', 'Relatório de profissional de saúde', 'Relatório escolar ou multiprofissional', 'Outro documento', 'Não sei informar'].map((item) => <option key={item}>{item}</option>)}</select></label>}</div><label className="field">Se quiser, resuma recomendações ou adaptações relevantes<textarea maxLength="2000" value={profile.observacoes_saude} onChange={(event) => change('observacoes_saude', event.target.value)} /></label><p className="notice">Não há upload de laudo nesta demonstração. Use dados fictícios; informações de saúde de crianças exigem proteção adequada.</p></div><button disabled={busy}>{busy ? 'Preparando perguntas…' : 'Começar observações →'}</button></form>
      : step < 14 ? <form onSubmit={advance}><div className="progress-label"><span>ÁREA {step + 1} DE 14</span><span>{Math.round(step / 14 * 100)}%</span></div><progress value={step} max="14" /><h2>{current.nome}</h2><p>{AREA_PROMPTS[current.id]} Pense também no que já funciona e nos apoios presentes.</p>{!current.perguntas.length && <p className="notice">Não há marco específico selecionado nesta idade. O relato do cotidiano e a participação são importantes nesta área.</p>}{current.perguntas.map((question) => <fieldset key={question.id}><legend>{question.pergunta}</legend><div className="options">{Object.entries(schema.opcoes).map(([value, label]) => <label key={value} className={answers[question.id]?.resposta === value ? 'selected' : ''}><input type="radio" required name={question.id} value={value} checked={answers[question.id]?.resposta === value} onChange={() => setAnswers((previous) => ({ ...previous, [question.id]: { ...previous[question.id], resposta: value, exemplo: previous[question.id]?.exemplo || '' } }))} />{label}</label>)}</div><label className="field small">Exemplo ou apoio utilizado <input maxLength="2000" value={answers[question.id]?.exemplo || ''} onChange={(event) => setAnswers((previous) => ({ ...previous, [question.id]: { ...previous[question.id], exemplo: event.target.value } }))} /></label><details><summary>Referência da pergunta</summary><small>{Array.isArray(question.fonte) ? question.fonte.join(' · ') : question.fonte} · Faixa: {question.faixa}</small></details></fieldset>)}<label className="field">O que a criança já faz bem ou demonstra interesse?<textarea maxLength="2000" value={ctx.pontos_fortes} onChange={(event) => changeContext('pontos_fortes', event.target.value)} placeholder="Habilidades, preferências e situações em que participa com confiança…" /></label><label className="field">O que é difícil, e em quais situações precisa de apoio?<textarea maxLength="2000" value={ctx.desafios} onChange={(event) => changeContext('desafios', event.target.value)} placeholder={current.pergunta_contexto} /></label><label className="field">O que vocês já tentaram? O que ajudou ou não funcionou?<textarea maxLength="2000" value={ctx.apoios} onChange={(event) => changeContext('apoios', event.target.value)} /></label><label className="field">Outros comentários ou exemplos<textarea maxLength="2000" value={ctx.observacoes} onChange={(event) => changeContext('observacoes', event.target.value)} /></label><label className="field">Onde observa estas situações?<select value={ctx.contexto} onChange={(event) => changeContext('contexto', event.target.value)}>{[['nao_sei', 'Não sei'], ['casa', 'Em casa'], ['escola', 'Na escola'], ['ambos', 'Em casa e na escola'], ['outro', 'Em outro lugar']].map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label className="check"><input type="checkbox" checked={ctx.nao_sei} onChange={(event) => changeContext('nao_sei', event.target.checked)} />Ainda não sei informar sobre esta área</label><div className="actions"><button type="button" className="secondary" onClick={() => go(step - 1)}>← Voltar</button><button>{step === 13 ? 'Revisar respostas' : 'Próxima área →'}</button></div></form>
      : <><span className="eyebrow">03 / REVISÃO</span><h2>Um retrato do que você compartilhou.</h2><p><strong>{profile.apelido}</strong> · {profile.idade_meses} meses · Relato de {profile.vinculo}</p><p><strong>Prioridade:</strong> {profile.prioridades}</p><p><strong>Condições relatadas:</strong> {conditionsLabel}</p><p><strong>Documento:</strong> {profile.documento_comprobatorio === 'sim' ? `${profile.tipo_documento || 'Tipo não informado'} — não anexado` : profile.documento_comprobatorio === 'nao' ? 'Família relata que não há' : 'Não informado'}</p><p><strong>Resumo de saúde/adaptações:</strong> {profile.observacoes_saude || profile.outra_condicao || 'Não informado'}</p>{schema.dominios.map((domain, index) => <details key={domain.id} className="review"><summary>{domain.nome}<span>{domain.perguntas.length} itens</span></summary>{domain.perguntas.map((question) => <p key={question.id}><strong>{question.pergunta}</strong><br />{schema.opcoes[answers[question.id]?.resposta]}{answers[question.id]?.exemplo && ` — ${answers[question.id].exemplo}`}</p>)}<p><b>Pontos fortes:</b> {contexts[domain.id]?.pontos_fortes || 'Não informado'}</p><p><b>Desafios:</b> {contexts[domain.id]?.desafios || 'Não informado'}</p><p><b>Apoios tentados:</b> {contexts[domain.id]?.apoios || 'Não informado'}</p><p><b>Outros comentários:</b> {contexts[domain.id]?.observacoes || 'Não informado'}</p><button className="secondary" onClick={() => go(index)}>Editar esta área</button></details>)}<label className="check"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} />Confirmo que revisei e autorizo o registro local destas informações, incluindo dados de saúde que informei. Usarei dados fictícios nesta demonstração.</label><div className="notice">Relatos familiares não são diagnóstico. O sistema não calcula escore ou classificação clínica. Metas futuras devem ser rascunhos revisados por adultos responsáveis.</div><div className="actions"><button className="secondary" disabled={busy} onClick={() => go(13)}>← Voltar</button><button disabled={!consent || busy} onClick={send}>{busy ? 'Registrando…' : 'Concluir formulário'}</button></div></>}
    </section></main><footer>PLACEHOLDER · Cada criança tem uma história.</footer></>;
}

createRoot(document.getElementById('root')).render(<App />);
