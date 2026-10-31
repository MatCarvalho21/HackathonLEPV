// Camada de acesso ao backend (FastAPI, banco local). O Vite encaminha /api para a porta 8000.
// Toda chamada leva o token de login; o backend descobre por ele quem está agindo.
const CHAVE_SESSAO = 'primeiros-passos-sessao';

export function lerSessao() {
  try {
    const s = JSON.parse(localStorage.getItem(CHAVE_SESSAO) || 'null');
    return s?.token ? s : null; // sessões antigas (sem login) não valem mais
  } catch { return null; }
}
export function salvarSessao(s) {
  try { s ? localStorage.setItem(CHAVE_SESSAO, JSON.stringify(s)) : localStorage.removeItem(CHAVE_SESSAO); } catch { /* sem storage */ }
}

async function bruto(method, url, body) {
  const token = lerSessao()?.token;
  const r = await fetch(url, {
    method,
    headers: { ...(body ? { 'Content-Type': 'application/json' } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) {
    let detail = `Erro ${r.status}`;
    try {
      const j = await r.json();
      detail = typeof j.detail === 'string' ? j.detail : (j.detail || []).map((d) => d.msg).join('; ') || detail;
    } catch { /* sem corpo */ }
    if (r.status === 401 && token) window.dispatchEvent(new CustomEvent('pp-sessao-expirada', { detail }));
    throw new Error(detail);
  }
  return r;
}
const req = async (method, url, body) => (await bruto(method, url, body)).json();

export const api = {
  // login
  cadastro: (body) => req('POST', '/api/auth/cadastro', body),
  entrar: (email, senha) => req('POST', '/api/auth/entrar', { email, senha }),
  eu: () => req('GET', '/api/auth/eu'),
  adicionarPerfil: (body) => req('POST', '/api/auth/perfis', body),
  sair: () => req('POST', '/api/auth/sair').catch(() => null),
  demoEntrar: () => req('POST', '/api/demo/entrar'),
  demoProfessor: () => req('POST', '/api/demo/entrar-professor'),
  // crianças
  criancas: (papel) => req('GET', `/api/eu/criancas?papel=${papel}`),
  criarCrianca: (body) => req('POST', '/api/criancas', body),
  estado: (cid) => req('GET', `/api/criancas/${cid}/estado`),
  formularioExemplo: () => req('GET', '/api/demo/formulario-exemplo'),
  formularioAtual: (cid) => req('GET', `/api/criancas/${cid}/formulario-atual`),
  // formulário e agente (as ações que mudam o perfil são só do responsável; o backend confere)
  enviarFormulario: (body) => req('POST', '/api/formularios', body),
  iniciarAgente: (formulario_id, demo = false) => req('POST', '/api/avaliacoes', { formulario_id, demo }),
  sessao: (id) => req('GET', `/api/avaliacoes/sessoes/${id}`),
  responder: (id, respostas) => req('POST', `/api/avaliacoes/sessoes/${id}/respostas`, { respostas }),
  avaliacao: (id) => req('GET', `/api/avaliacoes/${id}`),
  ajustar: (id, comentario) => req('POST', `/api/avaliacoes/${id}/ajustes`, { comentario }),
  aprovar: (id) => req('POST', `/api/avaliacoes/${id}/aprovar`),
  reavaliar: (cid, { comentario = '', formulario_id = null } = {}) => req('POST', `/api/criancas/${cid}/reavaliacoes`, { comentario, formulario_id }),
  // acompanhamento
  painel: (cid) => req('GET', `/api/criancas/${cid}/painel`),
  registrar: (cid, body) => req('POST', `/api/criancas/${cid}/registros`, body),
  conversas: (cid) => req('GET', `/api/criancas/${cid}/conversas`),
  mensagens: (conversaId) => req('GET', `/api/conversas/${conversaId}/mensagens`),
  conversar: (cid, body) => req('POST', `/api/criancas/${cid}/chat`, body),
  // canal da criança (pessoas)
  canal: (cid, depois = null) => req('GET', `/api/criancas/${cid}/canal${depois ? `?depois=${encodeURIComponent(depois)}` : ''}`),
  escreverCanal: (cid, texto) => req('POST', `/api/criancas/${cid}/canal`, { texto }),
  // compartilhamento
  compartilhamentos: (cid) => req('GET', `/api/criancas/${cid}/compartilhamentos`),
  compartilhar: (cid, email, funcao) => req('POST', `/api/criancas/${cid}/compartilhamentos`, { email, funcao }),
  revogar: (id) => req('DELETE', `/api/compartilhamentos/${id}`),
  convites: () => req('GET', '/api/eu/convites'),
  aceitarConvite: (id) => req('POST', `/api/compartilhamentos/${id}/aceitar`),
  recusarConvite: (id) => req('POST', `/api/compartilhamentos/${id}/recusar`),
  /** Baixa o PDF resumido da criança (salvar no computador). */
  async baixarResumo(cid) {
    const r = await bruto('GET', `/api/criancas/${cid}/resumo.pdf`);
    const nome = /filename="([^"]+)"/.exec(r.headers.get('content-disposition') || '')?.[1] || 'resumo.pdf';
    const url = URL.createObjectURL(await r.blob());
    const a = Object.assign(document.createElement('a'), { href: url, download: nome });
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  },
};

/** Monta a sessão do navegador a partir da resposta de login, escolhendo o perfil ativo. */
export function sessaoDeLogin(resp, papelPreferido = null) {
  const perfil = resp.perfis.find((p) => p.papel === papelPreferido) || resp.perfis[0];
  return { token: resp.token, conta: resp.conta, perfis: resp.perfis, papel: perfil?.papel, id: perfil?.id, nome: resp.conta.nome, funcao: perfil?.funcao };
}

export const FUNCOES = {
  professor: 'Professor(a)', pedagogo: 'Pedagogo(a)', medico: 'Médico(a)', terapeuta: 'Terapeuta', familiar: 'Familiar', outro: 'Outro',
};
export const rotuloFuncao = (f) => (f === 'responsavel' ? 'Responsável' : FUNCOES[f] || 'Acompanhante');
export const VINCULOS = ['Mãe', 'Pai', 'Avó', 'Avô', 'Tia', 'Tio', 'Madrasta', 'Padrasto', 'Tutor(a) legal', 'Cuidador(a)'];

export const DOMINIOS = {
  COM_R: 'Compreensão', COM_E: 'Comunicação expressiva', FAL: 'Fala e verbalização', SOC: 'Interação social',
  BRI: 'Brincadeira', COG: 'Cognição e aprendizagem', MOT_A: 'Movimento amplo', MOT_F: 'Movimento fino',
  AUT: 'Autonomia e autocuidado', REG: 'Regulação e comportamento', ATE: 'Atenção e funções executivas',
  SEN: 'Processamento sensorial', SAU: 'Saúde e corpo', CTX: 'Contexto e participação',
};

export const STATUS = {
  verde: { rotulo: 'Dentro do esperado', cor: 'var(--pp-verde)' },
  amarelo: { rotulo: 'Pede atenção', cor: 'var(--pp-amarelo)' },
  vermelho: { rotulo: 'Conversar com profissional', cor: 'var(--pp-vermelho)' },
  cinza: { rotulo: 'Informação insuficiente', cor: 'var(--pp-cinza)' },
  contextual: { rotulo: 'Contexto', cor: 'var(--pp-contexto)' },
};

export const HORIZONTE = { curto: 'Curto prazo', medio: 'Médio prazo', longo: 'Longo prazo' };

export function idade(meses) {
  const a = Math.floor(meses / 12), m = meses % 12;
  return [a ? `${a} ano${a > 1 ? 's' : ''}` : '', m || !a ? `${m} ${m === 1 ? 'mês' : 'meses'}` : ''].filter(Boolean).join(' e ');
}

export const DIRECAO = {
  melhorou: { rotulo: 'avançou', seta: '↑', classe: 'sobe' },
  piorou: { rotulo: 'pede mais atenção', seta: '↓', classe: 'desce' },
  mudou: { rotulo: 'mudou', seta: '↔', classe: 'muda' },
  igual: { rotulo: 'estável', seta: '=', classe: 'igual' },
};
export const SITUACAO_META = {
  alcancada: 'Alcançada 🎉', em_progresso: 'Em progresso', sem_progresso: 'Sem progresso ainda', sem_dados: 'Sem registros',
};
export const DESTINO_META = { concluida: 'concluída', mantida: 'continua', ajustada: 'ajustada', substituida: 'substituída' };

export function mesesDesde(dataNascimento) {
  if (!dataNascimento) return null;
  const n = new Date(`${dataNascimento.slice(0, 10)}T12:00:00`), h = new Date();
  return Math.max(0, (h.getFullYear() - n.getFullYear()) * 12 + h.getMonth() - n.getMonth() - (h.getDate() < n.getDate() ? 1 : 0));
}

export const dataDia = (iso) => new Date(iso.length === 10 ? `${iso}T12:00:00` : iso).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });

export const dataCurta = (iso) => new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
