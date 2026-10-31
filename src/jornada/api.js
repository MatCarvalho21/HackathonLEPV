// Camada de acesso ao backend (FastAPI, banco local). O Vite encaminha /api para a porta 8000.
async function req(method, url, body) {
  const r = await fetch(url, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) {
    let detail = `Erro ${r.status}`;
    try {
      const j = await r.json();
      detail = typeof j.detail === 'string' ? j.detail : (j.detail || []).map((d) => d.msg).join('; ') || detail;
    } catch { /* sem corpo */ }
    throw new Error(detail);
  }
  return r.json();
}

export const api = {
  // pessoas
  criarResponsavel: (body) => req('POST', '/api/responsaveis', body),
  criarProfessor: (body) => req('POST', '/api/professores', body),
  criancas: (sessao) => req('GET', `/api/${sessao.papel === 'professor' ? 'professores' : 'responsaveis'}/${sessao.id}/criancas`),
  criarCrianca: (body) => req('POST', '/api/criancas', body),
  estado: (cid) => req('GET', `/api/criancas/${cid}/estado`),
  demoEntrar: () => req('POST', '/api/demo/entrar'),
  demoProfessor: () => req('POST', '/api/demo/entrar-professor'),
  formularioExemplo: () => req('GET', '/api/demo/formulario-exemplo'),
  // formulário e agente
  enviarFormulario: (body) => req('POST', '/api/formularios', body),
  // ações que mudam o perfil levam o id do responsável: o backend recusa professor (403)
  iniciarAgente: (formulario_id, demo = false, responsavel_id = null) => req('POST', '/api/avaliacoes', { formulario_id, demo, responsavel_id }),
  sessao: (id) => req('GET', `/api/avaliacoes/sessoes/${id}`),
  responder: (id, respostas, responsavel_id) => req('POST', `/api/avaliacoes/sessoes/${id}/respostas`, { respostas, responsavel_id }),
  avaliacao: (id) => req('GET', `/api/avaliacoes/${id}`),
  ajustar: (id, comentario, responsavel_id) => req('POST', `/api/avaliacoes/${id}/ajustes`, { comentario, responsavel_id }),
  aprovar: (id, responsavel_id) => req('POST', `/api/avaliacoes/${id}/aprovar`, { responsavel_id }),
  reavaliar: (cid, responsavel_id, comentario = '') => req('POST', `/api/criancas/${cid}/reavaliacoes`, { responsavel_id, comentario }),
  // acompanhamento
  painel: (cid) => req('GET', `/api/criancas/${cid}/painel`),
  registrar: (cid, body) => req('POST', `/api/criancas/${cid}/registros`, body),
  conversas: (cid) => req('GET', `/api/criancas/${cid}/conversas`),
  mensagens: (conversaId) => req('GET', `/api/conversas/${conversaId}/mensagens`),
  conversar: (cid, body) => req('POST', `/api/criancas/${cid}/chat`, body),
};

// Sessão do usuário: só o "quem sou eu" fica no navegador; os dados ficam no banco.
const CHAVE_SESSAO = 'primeiros-passos-sessao';
export function lerSessao() {
  try { return JSON.parse(localStorage.getItem(CHAVE_SESSAO) || 'null'); } catch { return null; }
}
export function salvarSessao(s) {
  try { s ? localStorage.setItem(CHAVE_SESSAO, JSON.stringify(s)) : localStorage.removeItem(CHAVE_SESSAO); } catch { /* sem storage */ }
}

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
