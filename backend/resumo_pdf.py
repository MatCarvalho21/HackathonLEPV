"""PDF resumido da criança, para a família salvar no computador ou imprimir (até ~2 páginas).

Conteúdo: quem é a criança, o que já vai bem, as 14 áreas (cor + porquê), onde focar, metas atuais com
o último progresso, algumas dicas, evolução (se houve reavaliação), lembretes e o aviso de que não é
diagnóstico. Sem perfil aprovado, sai uma ficha básica com o cadastro e as prioridades do formulário.
"""
from __future__ import annotations

import os
import re
import unicodedata
from datetime import date, datetime
from io import BytesIO
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.agente_perfil import repositorio as repo
from src.agente_perfil.dossie import idade_por_extenso

NOMES = {"COM_R": "Compreensão", "COM_E": "Comunicação expressiva", "FAL": "Fala e verbalização",
         "SOC": "Interação social", "BRI": "Brincadeira", "COG": "Cognição e aprendizagem", "MOT_A": "Movimento amplo",
         "MOT_F": "Movimento fino", "AUT": "Autonomia e autocuidado", "REG": "Regulação e comportamento",
         "ATE": "Atenção e funções executivas", "SEN": "Processamento sensorial", "SAU": "Saúde e corpo",
         "CTX": "Contexto e participação"}
STATUS = {"verde": ("Dentro do esperado", "#4f9a6a"), "amarelo": ("Pede atenção", "#e2ad3e"),
          "vermelho": ("Conversar com profissional", "#d0644f"), "cinza": ("Informação insuficiente", "#a3aca6"),
          "contextual": ("Contexto", "#7f9db3")}
HORIZONTE = {"curto": "Curto prazo", "medio": "Médio prazo", "longo": "Longo prazo"}
VERDE, TINTA, SUAVE, LINHA = colors.HexColor("#285c47"), colors.HexColor("#24352e"), colors.HexColor("#6b7a72"), colors.HexColor("#e3e9e2")


def _registrar_fontes() -> tuple[str, str, bool]:
    """DejaVu (cobre mais símbolos) se o sistema tiver; senão a Vera que vem com o reportlab.
    Devolve (normal, negrito, tem_setas)."""
    candidatos = [("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
                  (os.path.join(os.path.dirname(reportlab.__file__), "fonts", "Vera.ttf"),
                   os.path.join(os.path.dirname(reportlab.__file__), "fonts", "VeraBd.ttf"))]
    for normal, negrito in candidatos:
        if os.path.exists(normal) and os.path.exists(negrito):
            pdfmetrics.registerFont(TTFont("PP", normal))
            pdfmetrics.registerFont(TTFont("PP-B", negrito))
            return "PP", "PP-B", "DejaVu" in normal
    return "Helvetica", "Helvetica-Bold", False


FONTE, NEGRITO, TEM_SETAS = _registrar_fontes()
EST = {
    "titulo": ParagraphStyle("t", fontName=NEGRITO, fontSize=20, leading=24, textColor=TINTA),
    "sub": ParagraphStyle("s", fontName=FONTE, fontSize=9.5, leading=13, textColor=SUAVE),
    "h2": ParagraphStyle("h2", fontName=NEGRITO, fontSize=12.5, leading=16, textColor=VERDE, spaceBefore=10, spaceAfter=4),
    "p": ParagraphStyle("p", fontName=FONTE, fontSize=9.5, leading=13.5, textColor=TINTA, alignment=TA_LEFT),
    "peq": ParagraphStyle("pq", fontName=FONTE, fontSize=8.5, leading=11.5, textColor=TINTA),
    "nota": ParagraphStyle("n", fontName=FONTE, fontSize=8, leading=11, textColor=SUAVE),
    "cel_b": ParagraphStyle("cb", fontName=NEGRITO, fontSize=8.5, leading=11.5, textColor=TINTA),
}
EMOJI = re.compile("[\U0001F000-\U0001FFFF☀-➿️‍]")


def _t(texto, limite: int | None = None) -> str:
    """Texto seguro para o Paragraph: sem emoji, com XML escapado e, se pedido, encurtado."""
    s = EMOJI.sub("", unicodedata.normalize("NFC", str(texto or ""))).strip()
    if not TEM_SETAS:
        s = s.replace("→", "->")
    if limite and len(s) > limite:
        s = s[: limite - 1].rsplit(" ", 1)[0].rstrip(".,;:—- ") + "…"
    return escape(s)


class Bolinha(Flowable):
    def __init__(self, cor: str, d: float = 3.2 * mm):
        super().__init__()
        self.cor, self.d = colors.HexColor(cor), d
        self.width = self.height = d

    def draw(self):
        self.canv.setFillColor(self.cor)
        self.canv.setStrokeColor(self.cor)
        self.canv.circle(self.d / 2, self.d / 2, self.d / 2, fill=1)


def _p(texto, estilo="p", limite=None):
    return Paragraph(_t(texto, limite), EST[estilo])


def _lista(itens, limite=None, estilo="p"):
    return [Paragraph("• " + _t(i, limite), EST[estilo]) for i in itens if i]


def _tabela(linhas, larguras, cabecalho=True):
    t = Table(linhas, colWidths=larguras, repeatRows=1 if cabecalho else 0)
    estilo = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINHA),
              ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
              ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    if cabecalho:
        estilo += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef4ee"))]
    t.setStyle(TableStyle(estilo))
    return t


def _meses(nascimento: str) -> int:
    n, h = date.fromisoformat(nascimento[:10]), date.today()
    return max(0, (h.year - n.year) * 12 + h.month - n.month - (h.day < n.day))


def _rodape(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONTE, 7.5)
    canvas.setFillColor(SUAVE)
    canvas.drawString(18 * mm, 10 * mm, "Primeiros Passos · resumo gerado em " + datetime.now().strftime("%d/%m/%Y %H:%M")
                      + " · não é diagnóstico e não substitui avaliação profissional")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"página {doc.page}")
    canvas.restoreState()


def gerar_resumo(crianca_id: str) -> tuple[bytes, str]:
    crianca = repo.obter_crianca(crianca_id)
    av = repo.avaliacao_vigente(crianca_id)
    form = repo.ultimo_formulario(crianca_id)
    meses = _meses(crianca["data_nascimento"])
    largura = A4[0] - 36 * mm
    h: list = []

    versoes = sum(1 for a in repo.listar_avaliacoes(crianca_id) if a["status"] in ("vigente", "substituida"))
    h.append(Paragraph(f"Resumo de {_t(crianca['nome'])}", EST["titulo"]))
    sub = [idade_por_extenso(meses)]
    if crianca.get("interesses"):
        sub.append("gosta de " + ", ".join(crianca["interesses"]))
    if av:
        sub.append(f"perfil versão {versoes}, aprovado em {(av.get('aceita_em') or av['criado_em'])[:10][8:10]}/"
                   f"{(av.get('aceita_em') or av['criado_em'])[5:7]}/{(av.get('aceita_em') or av['criado_em'])[:4]}")
    h += [Paragraph(_t(" · ".join(sub)), EST["sub"]), Spacer(1, 4 * mm)]

    if not av:
        h.append(Paragraph("Perfil ainda em construção", EST["h2"]))
        h.append(_p("O mapeamento completo aparece aqui depois que o responsável aprovar o perfil proposto pelo agente."))
        if form:
            p = form["perfil"]
            h.append(Paragraph("Prioridades da família", EST["h2"]))
            h.append(_p(p.get("prioridades")))
            if p.get("interesses"):
                h.append(Paragraph("Interesses e pontos fortes", EST["h2"]))
                h.append(_p(p.get("interesses")))
    else:
        r = av["perfil"]["relatorio"]
        h.append(Paragraph(f"Quem é {_t(crianca['nome'])}", EST["h2"]))
        h.append(_p(r["resumo"], limite=650))
        if r.get("caracteristicas"):
            h += [Spacer(1, 2 * mm), _p("Características: " + "; ".join(r["caracteristicas"][:4]), "peq", 260)]

        h.append(Paragraph("O que já vai bem", EST["h2"]))
        h += _lista([e["texto"] for e in r["pontos_fortes_gerais"][:4]], 160)

        ev = r.get("evolucao")
        cmp = av["perfil"].get("reavaliacao")
        if ev and cmp:
            subiram = sum(1 for a in cmp["areas"] if a["direcao"] == "melhorou")
            h.append(Paragraph("Evolução desde a versão anterior", EST["h2"]))
            h.append(_p(ev["resumo"], limite=700))
            h.append(_p(f"{cmp['periodo']['dias']} dias · {cmp['registros']['total']} registros · "
                        f"{subiram} área(s) avançaram de cor", "nota"))

        linhas = [[Paragraph("", EST["cel_b"]), Paragraph("Área", EST["cel_b"]), Paragraph("Situação", EST["cel_b"]),
                   Paragraph("Por quê", EST["cel_b"])]]
        for d in r["dominios"]:
            rot, cor = STATUS.get(d["status"], ("—", "#a3aca6"))
            linhas.append([Bolinha(cor), _p(NOMES.get(d["codigo"], d["codigo"]), "peq"), _p(rot, "peq"),
                           _p(d["justificativa_status"], "peq", 115)])
        h += [Paragraph("As 14 áreas do desenvolvimento", EST["h2"]),
              _tabela(linhas, [6 * mm, 42 * mm, 33 * mm, largura - 81 * mm])]

        h.append(Paragraph("Onde focar agora", EST["h2"]))
        h += _lista([f"{NOMES.get(f['dominio'], f['dominio'])}: {f['por_que']}" for f in r["foco_prioritario"]], 170)

        checkins: dict[str, int] = {}
        for reg in repo.listar_registros(crianca_id, tipo="checkin_meta", limite=200):
            checkins.setdefault(reg["meta_id"], (reg.get("dados") or {}).get("nivel_gas"))
        linhas = [[Paragraph("Prazo", EST["cel_b"]), Paragraph("Meta", EST["cel_b"]), Paragraph("Último progresso", EST["cel_b"])]]
        for m in r["metas"]:
            n = checkins.get(m["id"])
            prog = "sem registro ainda" if n is None else f"nível {n:+d}" if n else "nível 0 (meta alcançada)"
            linhas.append([_p(f"{HORIZONTE[m['horizonte']]} ({m['prazo_semanas']} sem.)", "peq"), _p(m["texto"], "peq", 150),
                           _p(prog, "peq")])
        h += [Paragraph("Metas atuais", EST["h2"]), _tabela(linhas, [32 * mm, largura - 66 * mm, 34 * mm]),
              _p("Escala de progresso: -2 = como estava no início · 0 = meta alcançada · +2 = muito além.", "nota")]

        h.append(Paragraph("Dicas para o dia a dia", EST["h2"]))
        for d in r["dicas"][:3]:
            bloco = [Paragraph(f"<font name='{NEGRITO}'>{_t(d['titulo'])}</font> · {_t(d['momento_do_dia'], 60)}", EST["p"])]
            bloco += _lista(d["como_fazer"][:2], 130, "peq")
            h.append(KeepTogether(bloco + [Spacer(1, 2 * mm)]))

        if r.get("alertas"):
            h.append(Paragraph("Lembretes importantes", EST["h2"]))
            h += _lista([a["recomendacao"] for a in r["alertas"][:3]], 180)
        h.append(Paragraph("Próximos passos", EST["h2"]))
        h += _lista(r["proximos_passos"][:4], 150)

    h += [Spacer(1, 5 * mm), _p("Este resumo organiza o que a família e os acompanhantes observaram e as sugestões do "
                                "agente de IA revisadas pela família. Não é diagnóstico e não substitui a avaliação de "
                                "profissionais de saúde ou educação.", "nota")]

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=16 * mm, title=f"Resumo de {crianca['nome']}", author="Primeiros Passos")
    doc.build(h, onFirstPage=_rodape, onLaterPages=_rodape)
    nome = re.sub(r"[^A-Za-z0-9]+", "-", unicodedata.normalize("NFKD", crianca["nome"]).encode("ascii", "ignore").decode()).strip("-")
    return buf.getvalue(), f"resumo-{nome.lower() or 'crianca'}-{date.today().isoformat()}.pdf"
