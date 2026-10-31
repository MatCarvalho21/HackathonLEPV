// Ícones da interface (lucide), no lugar dos emojis: mesmo traço, mesma cor do texto e tamanho controlado.
import {
  AudioLines, Brain, CircleMinus, CloudRain, CloudSun, Compass, Ear, Footprints, Hand, Headphones, HeartPulse,
  House, Handshake, Lightbulb, MessageCircle, MessageSquareText, NotebookPen, Puzzle, Sprout, Star, Stethoscope,
  Target, ThumbsDown, ThumbsUp, ToyBrick,
} from 'lucide-react';

const POR_TIPO = {
  saude: Stethoscope, atividade: Puzzle, comportamento: CloudRain, conquista: Star, observacao: NotebookPen,
  checkin_meta: Target, feedback_estrategia: Lightbulb, feedback_perfil: MessageSquareText,
};

const POR_DOMINIO = {
  COM_R: Ear, COM_E: MessageCircle, FAL: AudioLines, SOC: Handshake, BRI: ToyBrick, COG: Brain,
  MOT_A: Footprints, MOT_F: Hand, AUT: Sprout, REG: CloudSun, ATE: Compass, SEN: Headphones, SAU: HeartPulse, CTX: House,
};

const POR_RESULTADO = { funcionou: ThumbsUp, parcial: CircleMinus, nao_funcionou: ThumbsDown };

/** Ícone do tipo de registro (conquista, comportamento, saúde...). */
export function IconeTipo({ tipo, size = 16, ...resto }) {
  const I = POR_TIPO[tipo] || NotebookPen;
  return <I size={size} aria-hidden="true" {...resto} />;
}

/** Ícone de uma das 14 áreas do desenvolvimento. */
export function IconeDominio({ codigo, size = 18, ...resto }) {
  const I = POR_DOMINIO[codigo] || Sprout;
  return <I size={size} aria-hidden="true" {...resto} />;
}

/** Ícone do resultado de uma estratégia testada (funcionou / em parte / não funcionou). */
export function IconeResultado({ resultado, size = 15, ...resto }) {
  const I = POR_RESULTADO[resultado] || CircleMinus;
  return <I size={size} aria-hidden="true" {...resto} />;
}
