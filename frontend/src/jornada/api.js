async function req(method, url, body) {
  const r = await fetch(url, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) {
    let detail = `Erro ${r.status}`;
    try { const j = await r.json(); detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail); } catch { /* sem corpo */ }
    throw new Error(detail);
  }
  return r.json();
}

export const api = {
  formularioDemo: () => req('POST', '/api/demo/formulario'),
  iniciarAgente: (formulario_id, demo = false) => req('POST', '/api/avaliacoes', { formulario_id, demo }),
  sessao: (id) => req('GET', `/api/avaliacoes/sessoes/${id}`),
  responder: (id, respostas) => req('POST', `/api/avaliacoes/sessoes/${id}/respostas`, { respostas }),
  avaliacao: (id) => req('GET', `/api/avaliacoes/${id}`),
  ajustar: (id, comentario) => req('POST', `/api/avaliacoes/${id}/ajustes`, { comentario }),
  aprovar: (id) => req('POST', `/api/avaliacoes/${id}/aprovar`),
  painel: (fid) => req('GET', `/api/criancas/${fid}/painel`),
  registrar: (fid, body) => req('POST', `/api/criancas/${fid}/registros`, body),
};

export const ir = (rota) => { window.location.hash = rota; window.scrollTo({ top: 0 }); };

export const DOMINIOS = {
  COM_R: 'Compreensão', COM_E: 'Comunicação expressiva', FAL: 'Fala e verbalização', SOC: 'Interação social',
  BRI: 'Brincadeira', COG: 'Cognição e aprendizagem', MOT_A: 'Motor amplo', MOT_F: 'Motor fino',
  AUT: 'Autonomia e autocuidado', REG: 'Regulação e comportamento', ATE: 'Atenção e funções executivas',
  SEN: 'Processamento sensorial', SAU: 'Saúde e corpo', CTX: 'Contexto e participação',
};

export const STATUS = {
  verde: { rotulo: 'Dentro do esperado', cor: 'var(--verde)' },
  amarelo: { rotulo: 'Pede atenção', cor: 'var(--amarelo)' },
  vermelho: { rotulo: 'Conversar com profissional', cor: 'var(--vermelho)' },
  cinza: { rotulo: 'Informação insuficiente', cor: 'var(--cinza)' },
  contextual: { rotulo: 'Contexto', cor: 'var(--contexto)' },
};

export const HORIZONTE = { curto: 'Curto prazo', medio: 'Médio prazo', longo: 'Longo prazo' };

export function idade(meses) {
  const a = Math.floor(meses / 12), m = meses % 12;
  return [a ? `${a} ano${a > 1 ? 's' : ''}` : '', m || !a ? `${m} ${m === 1 ? 'mês' : 'meses'}` : ''].filter(Boolean).join(' e ');
}

export const data = (iso) => new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
