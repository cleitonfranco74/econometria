"""Monta o manuscrito da REA em Word a partir de paper_rea.tex.
Uso (dentro de av2_did_armas/paper/):  python gera_paper.py rea && python rea/monta_docx.py
Saídas: rea/REA_manuscrito.docx (anônimo, para avaliação cega) e rea/REA_folha_de_rosto.docx (identificação dos autores)."""
import json, re, subprocess, copy
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

P = Path(__file__).resolve().parent.parent; R = P / 'rea'
OUT = R / 'REA_manuscrito.docx'
subprocess.run(['pandoc', str(P / 'paper_rea.tex'), '-o', str(OUT), '--citeproc', f'--bibliography={P / "referencias.bib"}',
                f'--csl={R / "abnt.csl"}', f'--reference-doc={R / "ref_rea.docx"}', '--number-sections', '-M', 'lang=pt-BR',
                '-M', 'reference-section-title=Referências', f'--resource-path={P}'], check=True, cwd=P)

TAB = json.load(open(R / 'tabelas_rea.json', encoding='utf-8'))
HEAD = {'tab2': ['', '(1) TWFE', '(2) TWFE', '(3) Fronteira', '(4) Reversão', '(5) Poisson', '(6) C&S'],
        'tab4': ['Especificação', 'Coeficiente', 'EP', 'p-valor', 'N'],
        'tab6': ['', 'vs. sem soja', 'EP', 'vs. soja consolidada', 'EP'],
        'tab7': ['', 'Coeficiente', 'EP', 'p-valor', 'N']}

def plain(s):
    for a, b in [('$-$', '−'), ('$^{***}$', '***'), ('$^{**}$', '**'), ('$^{*}$', '*'), ('{,}', ','), ('\\&', '&'), ('$\\geq$', '≥'),
                 ('$\\times$', '×'), ('$<$', '<'), ('$\\Delta REG_i \\times Pos_t \\times Fronteira_i$', 'ΔREG × Pós × Fronteira'),
                 ('$\\Delta REG_i \\times Pos2023_t$', 'ΔREG × Pós-2023'), ('$\\Delta REG_i \\times Pos_t$', 'ΔREG × Pós-2019'), ('--', '–')]:
        s = s.replace(a, b)
    s = re.sub(r'\\textit\{(.*?)\}', r'\1', s)
    return s.strip()

def rows_of(key):
    out = []
    for line in TAB[key].split('\n'):
        line = line.strip()
        if not line: continue
        if line == r'\midrule': out.append('MID'); continue
        line = re.sub(r'\\\\\s*$', '', line)
        out.append([plain(c) for c in re.split(r'(?<!\\)&', line)])
    return out

def border(cell, sides):
    tcPr = cell._tc.get_or_add_tcPr(); b = OxmlElement('w:tcBorders')
    for s in sides:
        e = OxmlElement(f'w:{s}'); e.set(qn('w:val'), 'single'); e.set(qn('w:sz'), '6'); e.set(qn('w:color'), '000000'); b.append(e)
    tcPr.append(b)

def fmt_par(p, align, bold=False, italic=False):
    p.alignment = align; pf = p.paragraph_format
    pf.first_line_indent = Cm(0); pf.space_before = Pt(0); pf.space_after = Pt(0); pf.line_spacing_rule = WD_LINE_SPACING.DOUBLE
    for r in p.runs: r.font.name = 'Times New Roman'; r.font.size = Pt(10); r.font.bold = bold; r.font.italic = italic

def build_table(doc, key):
    head, body = HEAD[key], rows_of(key)
    data = [r for r in body if r != 'MID']
    t = doc.add_table(rows=1 + len(data), cols=len(head)); t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, h in enumerate(head):
        c = t.cell(0, j); c.text = h; fmt_par(c.paragraphs[0], WD_ALIGN_PARAGRAPH.CENTER if j else WD_ALIGN_PARAGRAPH.LEFT, bold=True)
        border(c, ['top', 'bottom'])
    mids = set(); i = 0
    for r in body:
        if r == 'MID': mids.add(i); continue
        i += 1
        for j in range(len(head)):
            c = t.cell(i, j); txt = r[j] if j < len(r) else ''
            c.text = txt
            painel = txt.startswith('Painel')
            fmt_par(c.paragraphs[0], WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER, italic=painel)
    for j in range(len(head)): border(t.cell(len(data), j), ['bottom'])
    for i in mids:
        for j in range(len(head)): border(t.cell(i, j), ['bottom'])
    widths = {7: [4.0] + [1.85] * 6, 5: [6.2, 2.4, 1.9, 2.6, 1.9]}[len(head)]
    t.autofit = False
    tblPr = t._tbl.tblPr; lay = OxmlElement('w:tblLayout'); lay.set(qn('w:type'), 'fixed'); tblPr.append(lay)
    for j, w in enumerate(widths):
        t.columns[j].width = Cm(w)
        for c in t.columns[j].cells: c.width = Cm(w)
    return t

doc = Document(OUT)
# tabelas nos marcadores
for p in list(doc.paragraphs):
    m = re.fullmatch(r'TABELA@(tab\d)@', p.text.strip())
    if m:
        t = build_table(doc, m.group(1)); p._p.addnext(t._tbl); p._p.getparent().remove(p._p)
# legenda das figuras acima da imagem (ABNT) e legendas/notas sem recuo
body = doc.element.body
for p in list(doc.paragraphs):
    st = p.style.name if p.style is not None else ''
    if st in ('Image Caption', 'Caption'):
        prev = p._p.getprevious()
        if prev is not None and prev.tag == qn('w:p') and prev.findall('.//' + qn('w:drawing')):
            prev.addprevious(p._p)
    if st in ('Image Caption', 'Caption', 'Captioned Figure') or p.text.startswith(('Nota:', 'Fonte:', 'Tabela ')):
        p.paragraph_format.first_line_indent = Cm(0)
        if p.text.startswith(('Nota:', 'Fonte:')):
            for r in p.runs: r.font.size = Pt(10)
# título centralizado e sem recuo nos blocos iniciais
for p in doc.paragraphs[:12]:
    if p.text.startswith(('MAIS ARMAS', 'MORE GUNS')): p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if p.text.startswith(('MAIS ARMAS', 'MORE GUNS', 'Resumo', 'Abstract', 'Palavras', 'Keywords', 'Classificação')): p.paragraph_format.first_line_indent = Cm(0)
# referências: sem recuo, espaço simples entre linhas e uma linha em branco entre elas (ABNT)
inref = False
for p in doc.paragraphs:
    if p.text.strip().endswith('Referências') and p.style.name.startswith('Heading'): inref = True; continue
    if inref:
        pf = p.paragraph_format; pf.first_line_indent = Cm(0); pf.left_indent = Cm(0)
        pf.line_spacing_rule = WD_LINE_SPACING.SINGLE; pf.space_after = Pt(12)
# ABNT: citação narrativa com dois autores usa "e" (ex.: Callaway e Sant'Anna (2021)); a parentética mantém ";" em maiúsculas
N = r"[A-ZÁ-Ú][\w’'\-]+"
pat3 = re.compile(rf"\b({N}); ({N}) e ({N} \(\d{{4}}\))"); pat2 = re.compile(rf"\b({N}); ({N} \(\d{{4}}\))")
for p in doc.paragraphs:
    for r in p.runs:
        if ';' in r.text and '(' in r.text: r.text = pat2.sub(r'\1 e \2', pat3.sub(r'\1, \2 e \3', r.text))
# ABNT: sobrenomes em maiúsculas nas citações entre parênteses, ex.: (BACULI et al., 2021; WAKIM, 2025)
cit = re.compile(r"^\((?:[^()]*?, \d{4}[a-z]?)(?:; [^()]*?, \d{4}[a-z]?)*\)$")
nome = re.compile(r"[A-ZÁ-Ú][\w’'\-]+")
for p in doc.paragraphs:
    for r in p.runs:
        if cit.match(r.text.strip()):
            r.text = nome.sub(lambda m: m.group(0).upper(), r.text)
# anonimização das propriedades do arquivo
cp = doc.core_properties; cp.author = ''; cp.last_modified_by = ''; cp.title = ''; cp.subject = ''; cp.keywords = ''; cp.comments = ''
doc.save(OUT)

# folha de rosto (enviada separadamente como documento suplementar)
fr = Document(R / 'ref_rea.docx')
for el in list(fr.element.body):
    if el.tag != qn('w:sectPr'): fr.element.body.remove(el)
def par(txt, bold=False, center=False):
    p = fr.add_paragraph(); r = p.add_run(txt); r.bold = bold; r.font.name = 'Times New Roman'; r.font.size = Pt(12)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT; p.paragraph_format.first_line_indent = Cm(0)
par('MAIS ARMAS, MAIS HOMICÍDIOS? FLEXIBILIZAÇÃO DO ACESSO A ARMAS E VIOLÊNCIA NA FRONTEIRA DA SOJA', bold=True, center=True)
par('Folha de rosto — identificação dos autores', center=True)
for nome, extra in [('Ricardo Alves dos Santos', ' Autor correspondente. E-mail: ricardo.alves@unemat.br'), ('Cleiton Franco', ''),
                    ('Wylmor Dalfovo', ''), ('Lindomar Pegorini', '')]:
    par(f'{nome} — Universidade do Estado de Mato Grosso (UNEMAT), Inovapro.{extra}')
par('Disponibilidade de dados: todos os dados utilizados são públicos; os códigos de montagem do painel e de estimação estão disponíveis mediante solicitação ao autor correspondente.')
cp = fr.core_properties; cp.author = ''; cp.last_modified_by = ''
fr.save(R / 'REA_folha_de_rosto.docx')
print('ok:', OUT.name, 'e REA_folha_de_rosto.docx')
