import reference from '../prompts/matheus/07/ouput.json';

export const REFERENCE = reference;

export const DOMAIN_META = {
  COM_R: { label: 'Compreensão', focus: 'compreensão e comunicação receptiva' },
  COM_E: { label: 'Comunicação expressiva', focus: 'formas de expressar escolhas, necessidades e ideias' },
  FAL: { label: 'Fala e verbalização', focus: 'sons, palavras e formas de fala, quando aplicável' },
  SOC: { label: 'Interação social', focus: 'participação e conexão com outras pessoas' },
  BRI: { label: 'Brincadeira', focus: 'brincadeiras, interesses e exploração' },
  COG: { label: 'Cognição e aprendizagem', focus: 'curiosidade, aprendizagem e resolução de problemas' },
  MOT_A: { label: 'Movimento amplo', focus: 'movimento, equilíbrio e participação corporal' },
  MOT_F: { label: 'Movimento fino', focus: 'uso das mãos e coordenação em atividades do cotidiano' },
  AUT: { label: 'Autonomia e autocuidado', focus: 'participação em rotinas e autocuidado' },
  REG: { label: 'Regulação e comportamento', focus: 'bem-estar, comunicação de desconforto e transições' },
  ATE: { label: 'Atenção e funções executivas', focus: 'iniciar, organizar e continuar atividades' },
  SEN: { label: 'Processamento sensorial', focus: 'conforto sensorial e participação nos ambientes' },
  SAU: { label: 'Saúde e corpo', focus: 'rotinas de saúde e informações que a família queira compartilhar' },
  CTX: { label: 'Contexto e participação', focus: 'ambientes, apoios, barreiras e participação' },
};

export const DOMAIN_CONTEXT = {
  REG: 'O que costuma causar desconforto ou frustração? Como a criança demonstra isso? O que ajuda a se sentir segura ou a se recuperar?',
  ATE: 'Como a criança participa de uma atividade de que gosta? O que ajuda a começar, manter a atenção ou encerrar a atividade?',
  SEN: 'Como reage a sons, luzes, cheiros, texturas e movimento? Há sensações ou ambientes que procura ou prefere evitar?',
  SAU: 'Há aspectos de sono, alimentação, visão, audição, mobilidade ou saúde que afetam a rotina e que você deseja compartilhar?',
  CTX: 'Como é a rotina em casa e na escola? Quem oferece apoio? O que facilita ou cria barreiras para a participação?',
};

export const AREA_PROMPTS = {
  COM_R: 'Em quais situações a criança entende melhor? Há diferença entre instruções faladas, gestos, imagens ou rotinas conhecidas?',
  COM_E: 'Como comunica desejos, escolhas, sentimentos ou ideias? Que recursos usa (fala, gestos, olhar, imagens, comunicação alternativa)?',
  FAL: 'Se fala é uma forma usada pela criança, como são os sons, palavras e frases no cotidiano? Se não usa fala, que formas de comunicação funcionam?',
  SOC: 'Como demonstra interesse por outras pessoas e participa com familiares, colegas ou adultos conhecidos? Em que situações fica mais à vontade?',
  BRI: 'Que brincadeiras, temas ou objetos despertam interesse? Como explora, imagina, compartilha ou prefere brincar?',
  COG: 'O que desperta curiosidade? Como aprende algo novo, resolve problemas, lembra etapas ou demonstra o que sabe?',
  MOT_A: 'Como participa de movimentos e atividades físicas do cotidiano? Que apoios, adaptações ou condições do espaço fazem diferença?',
  MOT_F: 'Como usa as mãos em brincadeiras, alimentação, desenho, escrita ou objetos? Quais materiais ou adaptações ajudam?',
  AUT: 'Em quais rotinas de autocuidado participa? Que etapas consegue fazer, quais prefere fazer de outro jeito e que apoio respeita sua autonomia?',
  REG: 'Quais situações, mudanças ou demandas podem ser difíceis? Como a criança demonstra que precisa de pausa, ajuda ou previsibilidade?',
  ATE: 'Em atividades escolhidas e necessárias, o que ajuda a criança a começar, manter-se envolvida, alternar etapas ou terminar?',
  SEN: 'Quais sons, luzes, cheiros, texturas, sabores ou movimentos parecem confortáveis, interessantes ou difíceis? Que ajustes ajudam?',
  SAU: 'Há informações de saúde que influenciam o cotidiano, como sono, alimentação, visão, audição, mobilidade, acompanhamentos ou cuidados?',
  CTX: 'Como os ambientes, horários, relações e apoios de casa, escola e comunidade influenciam a participação da criança?',
};

export const ANSWER_LABELS = {
  sim: 'Faz com frequência',
  as_vezes: 'Às vezes ou com ajuda',
  nao: 'Ainda não / ainda é difícil',
  nao_sei: 'Não sei / não observei',
  nao_aplicavel: 'Não se aplica / não houve oportunidade',
};

export const CONDITIONS = [
  ['tea', 'TEA (inclui diagnóstico anteriormente chamado síndrome de Asperger)'],
  ['tdah', 'TDAH'],
  ['down', 'Síndrome de Down'],
  ['deficiencia_intelectual', 'Deficiência intelectual ou cognitiva'],
  ['atraso_global', 'Atraso global do desenvolvimento'],
  ['linguagem_aprendizagem', 'Condição de linguagem ou aprendizagem'],
  ['motora', 'Condição motora ou física'],
  ['genetica_outra', 'Condição genética ou outra condição de desenvolvimento'],
  ['em_investigacao', 'Em investigação / ainda sem diagnóstico concluído'],
  ['prefiro_nao_informar', 'Prefiro não informar'],
];

export const CERTIFICATE_TYPES = ['Laudo ou atestado médico', 'Relatório de profissional de saúde', 'Relatório escolar ou multiprofissional', 'Outro documento', 'Não sei informar'];

export function buildQuestionnaire(ageMonths, schoolYear) {
  const domains = [];
  for (const code of reference.dominios_por_idade.concat(reference.dominios_funcionais, reference.dominios_sem_classificacao)) {
    let candidates = reference.marcos.filter((milestone) => milestone.dominio === code && milestone.faixa_meses <= ageMonths);
    if (ageMonths >= 72 && reference.regua_6_10?.dominios_por_ano_escolar?.includes(code)) {
      const cap = schoolYear === 1 ? 60 : (schoolYear ? (schoolYear + 4) * 12 : null);
      candidates = candidates.filter((milestone) => cap !== null && milestone.faixa_meses <= cap);
    }
    const band = Math.max(0, ...candidates.map((milestone) => milestone.faixa_meses));
    domains.push({
      id: code,
      nome: DOMAIN_META[code]?.label || code,
      faixa_referencia_meses: band || null,
      perguntas: band ? candidates.filter((milestone) => milestone.faixa_meses === band) : [],
      pergunta_contexto: DOMAIN_CONTEXT[code] || 'Conte uma situação cotidiana: o que a criança gosta de fazer, o que já consegue fazer e em que precisa de apoio?',
      natureza: reference.dominios_sem_classificacao.includes(code) ? 'contextual' : 'relato_observacional',
    });
  }
  return {
    versao: reference.versao,
    idade_meses: ageMonths,
    dominios: domains,
    opcoes: ANSWER_LABELS,
  };
}
