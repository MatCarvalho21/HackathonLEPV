import { BookOpen, ClipboardList, HeartHandshake, MessagesSquare, ShieldCheck, Sparkles, X } from 'lucide-react';

const PASSOS = [
  [ClipboardList, 'Você conta como a criança está', 'O responsável preenche um formulário sobre 14 áreas do desenvolvimento: o que a criança já faz, o que ainda é difícil, o que ajuda e o contexto de casa e da escola. Leva de 15 a 25 minutos.'],
  [Sparkles, 'Um agente de IA organiza o retrato', 'O agente lê as respostas, consulta materiais oficiais (Caderneta da Criança, OMS, CDC e outros) e propõe um perfil: o que vai bem, onde focar, metas e dicas para a rotina. Se faltar algo importante, ele pergunta.'],
  [HeartHandshake, 'A família decide', 'O perfil é uma proposta. Você lê, pede ajustes e só então aprova. Nada vira plano sem a sua aprovação.'],
  [MessagesSquare, 'Família e acompanhantes juntos', 'Você compartilha o perfil com professores, médicos, terapeutas e familiares. Todos registram o que observam e conversam no canal da criança.'],
  [BookOpen, 'O acompanhamento continua', 'Os registros mostram o que funciona. Quando quiser, peça uma reavaliação: o agente compara com a versão anterior e mostra a evolução.'],
];

/** Explicação da plataforma (antes era um alerta do navegador). */
export function SaibaMais({ onFechar }) {
  return <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onFechar()}>
    <div className="modal-card pp-saiba" role="dialog" aria-modal="true" aria-labelledby="saiba-titulo">
      <div className="modal-header"><span className="section-kicker">SOBRE A PLATAFORMA</span>
        <button type="button" className="icon-button" onClick={onFechar} aria-label="Fechar"><X size={18} /></button></div>
      <h2 id="saiba-titulo">Como funciona o acompanhamento</h2>
      <p>Um espaço para família, escola e profissionais acompanharem juntos o desenvolvimento de crianças de 0 a 10 anos, com ou sem necessidades específicas.</p>
      <ol className="pp-passos">{PASSOS.map(([Icone, titulo, texto], i) => <li key={titulo}>
        <span className="pp-passo-num"><Icone size={18} /></span>
        <div><b>{i + 1}. {titulo}</b><p>{texto}</p></div></li>)}</ol>
      <div className="pp-saiba-limites"><ShieldCheck size={18} /><div>
        <b>O que a plataforma não faz</b>
        <p>Não faz diagnóstico, não calcula idade mental nem escore e não substitui pediatras, terapeutas ou educadores. As cores das áreas indicam onde vale atenção e quando conversar com um profissional. Nesta demonstração, use apenas dados fictícios.</p></div></div>
      <button className="btn-primary full-button" onClick={onFechar}>Entendi</button>
    </div>
  </div>;
}
