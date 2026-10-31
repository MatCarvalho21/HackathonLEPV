import { useState } from 'react';
import { ArrowLeft, ArrowRight, Heart, LogIn, School, ShieldCheck } from 'lucide-react';
import { FUNCOES, VINCULOS } from './api.js';

const EMAIL = '[^@\\s]+@[^@\\s]+\\.[^@\\s]+';

/** Entrar com e-mail e senha. */
export function Login({ onVoltar, onEntrar, onCriarConta }) {
  const [erro, setErro] = useState('');
  const [ocupado, setOcupado] = useState(false);
  async function enviar(e) {
    e.preventDefault(); setErro(''); setOcupado(true);
    const v = Object.fromEntries(new FormData(e.currentTarget));
    try { await onEntrar(v.email, v.senha); } catch (x) { setErro(x.message); setOcupado(false); }
  }
  return <section className="page-wrap narrow-page acesso-page">
    <button className="back-link" onClick={onVoltar}><ArrowLeft size={16} /> Voltar</button>
    <div className="form-heading"><span className="step-icon parent-icon"><LogIn size={20} /></span>
      <span className="section-kicker">ENTRAR</span><h1>Que bom ver você de novo.</h1>
      <p>Entre com o e-mail e a senha da sua conta.</p></div>
    <form className="panel signup-panel" onSubmit={enviar}>
      <div className="field-grid uma-coluna">
        <label>E-mail<input name="email" type="email" autoComplete="email" required placeholder="voce@email.com" /></label>
        <label>Senha<input name="senha" type="password" autoComplete="current-password" required placeholder="Sua senha" /></label>
      </div>
      {erro && <div className="questionnaire-error">{erro}</div>}
      <button className="btn-primary full-button" disabled={ocupado}>{ocupado ? 'Entrando…' : 'Entrar'} <ArrowRight size={17} /></button>
    </form>
    <p className="mock-note">Ainda não tem conta? <button className="btn-text" onClick={onCriarConta}>Criar conta</button></p>
    <p className="mock-note">Demonstração: <b>ana@demo.primeirospassos</b> (responsável) ou <b>carla@demo.primeirospassos</b> (professora), senha <b>demo1234</b>.</p>
  </section>;
}

/** Criar conta como responsável pelo perfil ou como acompanhante. */
export function Cadastro({ tipo, onVoltar, onTrocarTipo, onCriar, onEntrar }) {
  const responsavel = tipo === 'responsavel';
  const [erro, setErro] = useState('');
  const [ocupado, setOcupado] = useState(false);
  const [vinculo, setVinculo] = useState('Mãe');
  async function enviar(e) {
    e.preventDefault(); setErro('');
    const v = Object.fromEntries(new FormData(e.currentTarget));
    if (v.senha !== v.confirmar) { setErro('As senhas não conferem.'); return; }
    setOcupado(true);
    const corpo = { tipo, nome: v.nome, email: v.email, senha: v.senha };
    if (responsavel) Object.assign(corpo, { telefone: v.telefone || null, vinculo: vinculo === 'outro' ? v.vinculo_outro : vinculo });
    else Object.assign(corpo, { funcao: v.funcao, instituicao: v.instituicao || null });
    try { await onCriar(corpo, responsavel ? corpo.vinculo : null); } catch (x) { setErro(x.message); setOcupado(false); }
  }
  return <section className="page-wrap narrow-page acesso-page">
    <button className="back-link" onClick={onVoltar}><ArrowLeft size={16} /> Voltar</button>
    <div className="form-heading">
      <span className={`step-icon ${responsavel ? 'parent-icon' : 'teacher-icon'}`}>{responsavel ? <Heart size={20} /> : <School size={20} />}</span>
      <span className="section-kicker">CRIAR CONTA · {responsavel ? 'RESPONSÁVEL PELO PERFIL' : 'ACOMPANHANTE'}</span>
      <h1>Vamos nos conhecer.</h1>
      <p>{responsavel
        ? 'Quem cuida da criança e decide sobre o perfil dela: mãe, pai, avó, tutor legal, cuidador. Você cadastra a criança, preenche o formulário e escolhe quem acompanha.'
        : 'Para quem acompanha uma criança: professor, pedagogo, médico, terapeuta ou familiar. Você vê as crianças que o responsável compartilhar com o seu e-mail.'}</p>
    </div>
    <div className="acesso-abas" role="tablist">
      <button type="button" className={responsavel ? 'active' : ''} onClick={() => onTrocarTipo('responsavel')}><Heart size={15} /> Responsável pelo perfil</button>
      <button type="button" className={!responsavel ? 'active' : ''} onClick={() => onTrocarTipo('acompanhante')}><School size={15} /> Acompanhante</button>
    </div>
    <form className="panel signup-panel" onSubmit={enviar}>
      <div className="field-grid">
        <label>Nome completo<input name="nome" autoComplete="name" required maxLength={120} placeholder="Como podemos chamar você?" /></label>
        <label>E-mail<input name="email" type="email" autoComplete="email" required pattern={EMAIL} title="Use o formato nome@dominio.com (com ponto depois do @)" placeholder="voce@email.com" /></label>
        <label>Senha<input name="senha" type="password" autoComplete="new-password" required minLength={6} placeholder="Pelo menos 6 caracteres" /></label>
        <label>Confirme a senha<input name="confirmar" type="password" autoComplete="new-password" required minLength={6} placeholder="Repita a senha" /></label>
        {responsavel ? <>
          <label>Seu vínculo com a criança<select value={vinculo} onChange={(e) => setVinculo(e.target.value)}>
            {VINCULOS.map((x) => <option key={x}>{x}</option>)}<option value="outro">Outro</option></select></label>
          {vinculo === 'outro'
            ? <label>Qual vínculo?<input name="vinculo_outro" required maxLength={60} placeholder="Ex.: madrinha" /></label>
            : <label>Telefone <span className="optional">opcional</span><input name="telefone" type="tel" placeholder="(00) 00000-0000" /></label>}
        </> : <>
          <label>Sua função<select name="funcao" defaultValue="professor">{Object.entries(FUNCOES).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
          <label>Instituição <span className="optional">opcional</span><input name="instituicao" maxLength={160} placeholder="Escola, clínica, UBS…" /></label>
        </>}
      </div>
      <div className="privacy-callout"><ShieldCheck size={18} /><span><b>Privacidade na demonstração</b>
        <small>Os dados ficam no banco local da plataforma e a senha é guardada com hash. Use dados fictícios.</small></span></div>
      {erro && <div className="questionnaire-error">{erro}</div>}
      <button className="btn-primary full-button" type="submit" disabled={ocupado}>{ocupado ? 'Criando…' : 'Criar minha conta'} <ArrowRight size={17} /></button>
    </form>
    <p className="mock-note">Já tem conta? <button className="btn-text" onClick={onEntrar}>Entrar</button></p>
  </section>;
}
