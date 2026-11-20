#!/usr/bin/env python3
"""
Gera os SVGs animados de assets/ usados no README do perfil.

    pip install fonttools brotli
    python3 scripts/build.py

Os textos ficam nas funções abaixo (hero, frentes, stack, projetos, rodape):
mude o texto, rode o script e faça o commit dos SVGs.

As fontes (Bricolage Grotesque e JetBrains Mono, licença OFL, em fonts/) são
recortadas para os caracteres usados e embutidas em cada SVG — o GitHub exibe
SVG como imagem, e imagem não carrega fonte externa.
"""
import base64
import html
import io
import pathlib
from string import Template

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "fonts"
OUT = ROOT / "assets"

# ── Paleta: verdes Copapel ────────────────────────────────────────────────
BG0 = "#021c19"    # fundo mais escuro
BG1 = "#013f38"    # verde-escuro Copapel
PANEL = "#06302a"  # cartões
PANEL2 = "#0a4439"
LINE = "#1f6354"   # contornos
LIME = "#8cc63f"   # verde Copapel
LIME2 = "#c3ec7a"  # realce
MINT = "#4fc392"
TEXT = "#f1f8e9"
MUTED = "#a3c2b3"

# ── Fontes ────────────────────────────────────────────────────────────────
FONT_SPEC = {
    # classe: (arquivo, eixos, fallback, peso)
    "d8": ("BricolageGrotesque.ttf", {"wght": 800, "opsz": 96, "wdth": 100}, "'Arial Black',Arial,sans-serif", 800),
    "d6": ("BricolageGrotesque.ttf", {"wght": 600, "opsz": 32, "wdth": 100}, "'Helvetica Neue',Arial,sans-serif", 600),
    "b4": ("BricolageGrotesque.ttf", {"wght": 400, "opsz": 20, "wdth": 100}, "'Helvetica Neue',Arial,sans-serif", 400),
    "m5": ("JetBrainsMono.ttf", {"wght": 500}, "ui-monospace,Menlo,Consolas,monospace", 500),
}


class Face:
    def __init__(self, key):
        file, axes, self.fallback, self.weight = FONT_SPEC[key]
        self.key = key
        font = instancer.instantiateVariableFont(TTFont(FONT_DIR / file), axes)
        buf = io.BytesIO()
        font.save(buf)
        self.data = buf.getvalue()
        self.cmap = font.getBestCmap()
        self.hmtx = font["hmtx"]
        self.upem = font["head"].unitsPerEm

    def width(self, text, size, ls=0.0):
        total = 0
        for ch in text:
            glyph = self.cmap.get(ord(ch))
            if glyph is None:
                print(f"  ! sem glifo em {self.key}: {ch!r}")
                continue
            total += self.hmtx[glyph][0]
        return total / self.upem * size + ls * len(text)

    def wrap(self, text, size, maxw):
        lines, cur = [], ""
        for word in text.split():
            trial = (cur + " " + word).strip()
            if cur and self.width(trial, size) > maxw:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        if cur:
            lines.append(cur)
        return lines

    def subset_b64(self, chars):
        font = TTFont(io.BytesIO(self.data))
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern"]
        opts.hinting = False
        opts.notdef_outline = True
        sub = subset.Subsetter(opts)
        sub.populate(text="".join(sorted(chars)))
        sub.subset(font)
        buf = io.BytesIO()
        font.flavor = "woff2"
        font.save(buf)
        return base64.b64encode(buf.getvalue()).decode()


FACES = {}


def n(v):
    """Número curto para atributos SVG."""
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


BASE_CSS = """
.in{opacity:0;animation:in .9s cubic-bezier(.22,1,.36,1) forwards}
@keyframes in{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
.blink{animation:blink 1.1s steps(1) infinite}@keyframes blink{50%{opacity:0}}
.beat{animation:beat 2.4s ease-in-out infinite}@keyframes beat{50%{opacity:.25}}
.flow{stroke-dasharray:3 9;animation:flow 1.1s linear infinite}@keyframes flow{to{stroke-dashoffset:-24}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}.in{opacity:1}}
"""


class Doc:
    def __init__(self, name, w, h, label, glow=None, dots=True, radius=20):
        self.name, self.w, self.h, self.label = name, w, h, label
        self.glow, self.dots, self.radius = glow, dots, radius
        self.used = {k: set() for k in FONT_SPEC}
        self.body = []
        self.css = ""
        self.defs = ""

    def use(self, face, text):
        self.used[face].update(text)

    def t(self, x, y, s, face, size, fill, anchor=None, ls=None, cls="", style="", extra=""):
        self.use(face, s)
        a = f'x="{n(x)}" y="{n(y)}" class="{(face + " " + cls).strip()}" font-size="{n(size)}" fill="{fill}"'
        if anchor:
            a += f' text-anchor="{anchor}"'
        if ls:
            a += f' letter-spacing="{n(ls)}"'
        if style:
            a += f' style="{style}"'
        if extra:
            a += " " + extra
        return f"<text {a}>{html.escape(s)}</text>"

    def add(self, *parts):
        self.body.extend(parts)

    def render(self):
        w, h, r = self.w, self.h, self.radius
        faces_css = ""
        for key, chars in self.used.items():
            if not chars:
                continue
            face = FACES[key]
            faces_css += (
                f"@font-face{{font-family:{key.upper()};font-weight:{face.weight};"
                f"src:url(data:font/woff2;base64,{face.subset_b64(chars)}) format('woff2')}}"
                f".{key}{{font-family:{key.upper()},{face.fallback};font-weight:{face.weight}}}\n"
            )
        defs = (
            f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{BG0}"/>'
            f'<stop offset="1" stop-color="{BG1}"/></linearGradient>'
            f'<radialGradient id="glow"><stop offset="0" stop-color="{LIME}" stop-opacity=".24"/>'
            f'<stop offset="1" stop-color="{LIME}" stop-opacity="0"/></radialGradient>'
            f'<pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse">'
            f'<circle cx="2" cy="2" r="1.1" fill="{LIME}" fill-opacity=".11"/></pattern>'
            f'<clipPath id="clip"><rect width="{w}" height="{h}" rx="{r}"/></clipPath>' + self.defs
        )
        bg = f'<rect width="{w}" height="{h}" fill="url(#bg)"/>'
        if self.dots:
            bg += f'<rect width="{w}" height="{h}" fill="url(#dots)"/>'
        if self.glow:
            gx, gy, gr = self.glow
            bg += f'<circle cx="{gx}" cy="{gy}" r="{gr}" fill="url(#glow)"/>'
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{html.escape(self.label)}"><style>{faces_css}{BASE_CSS}{self.css}</style>'
            f"<defs>{defs}</defs>\n"
            f'<g clip-path="url(#clip)">{bg}\n' + "\n".join(self.body) + "\n</g>"
            f'<rect x=".75" y=".75" width="{w - 1.5}" height="{h - 1.5}" rx="{r - .75}" fill="none" '
            f'stroke="{LIME}" stroke-opacity=".28" stroke-width="1.5"/></svg>\n'
        )

    def save(self):
        path = OUT / f"{self.name}.svg"
        path.write_text(self.render(), encoding="utf-8")
        print(f"{path.name:22s} {path.stat().st_size / 1024:6.1f} KB")


def header(d, num, kicker, title, sub=None, y=86):
    d.add(
        f'<rect x="64" y="{y - 11}" width="26" height="4" rx="2" fill="{LIME}" class="in"/>',
        d.t(102, y - 3, f"{num} — {kicker}", "m5", 15, LIME, ls=3, cls="in"),
        d.t(62, y + 56, title, "d8", 46, TEXT, cls="in", style="animation-delay:.12s"),
    )
    if sub:
        d.add(d.t(64, y + 92, sub, "b4", 21, MUTED, cls="in", style="animation-delay:.24s"))


def curve(x1, y1, x2, y2):
    mx = (x1 + x2) / 2
    return f"M{n(x1)} {n(y1)}C{n(mx)} {n(y1)} {n(mx)} {n(y2)} {n(x2)} {n(y2)}"


def pulse(path, dur, begin, travel=0.45, r=4):
    """Ponto de luz que percorre `path` na primeira fração `travel` do ciclo."""
    kt = f"0;{travel};1"
    return (
        f'<g opacity="0"><circle r="{r * 2.4}" fill="{LIME}" opacity=".22"/><circle r="{r}" fill="{LIME2}"/>'
        f'<animateMotion dur="{dur}s" begin="{begin}s" repeatCount="indefinite" calcMode="linear" '
        f'keyPoints="0;1;1" keyTimes="{kt}" path="{path}"/>'
        f'<animate attributeName="opacity" dur="{dur}s" begin="{begin}s" repeatCount="indefinite" '
        f'values="0;1;1;0;0" keyTimes="0;{travel * .12:.3f};{travel * .88:.3f};{travel};1"/></g>'
    )


# ══════════════════════════════════════════════════════════════════════════
# 00 · HERO
# ══════════════════════════════════════════════════════════════════════════
def hero():
    W, H = 1200, 600
    d = Doc("00-hero", W, H, "Flávio R. — gerente de TI: gestão, software, integrações e automação, em Joinville, SC",
            glow=(980, 140, 470))
    d.css = f"""
.tag{{opacity:0;animation:tag 16s ease-in-out infinite}}
@keyframes tag{{0%{{opacity:0;transform:translateY(8px)}}3%,22%{{opacity:1;transform:none}}25%,100%{{opacity:0;transform:translateY(-8px)}}}}
.draw{{stroke-dasharray:700;stroke-dashoffset:700;animation:draw 1.5s .7s cubic-bezier(.65,0,.35,1) forwards}}
@keyframes draw{{to{{stroke-dashoffset:0}}}}
.bub{{opacity:0;animation:rise linear infinite}}
@keyframes rise{{0%{{opacity:0;transform:translateY(0)}}12%{{opacity:.5}}80%{{opacity:.25}}100%{{opacity:0;transform:translateY(-300px)}}}}
.halo{{transform-box:fill-box;transform-origin:center;animation:halo 4s ease-out infinite}}
@keyframes halo{{0%{{opacity:.7;transform:scale(1)}}60%,100%{{opacity:0;transform:scale(1.22,1.5)}}}}
.l1,.l2,.l3{{opacity:0;animation:9s ease-out infinite}}.l1{{animation-name:l1}}.l2{{animation-name:l2}}.l3{{animation-name:l3}}
@keyframes l1{{0%,4%{{opacity:0;transform:translateX(-8px)}}8%,88%{{opacity:1;transform:none}}94%,100%{{opacity:0}}}}
@keyframes l2{{0%,28%{{opacity:0;transform:translateX(-8px)}}32%,88%{{opacity:1;transform:none}}94%,100%{{opacity:0}}}}
@keyframes l3{{0%,52%{{opacity:0;transform:translateX(-8px)}}56%,88%{{opacity:1;transform:none}}94%,100%{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{.tag.t0,.l1,.l2,.l3{{opacity:1}}.draw{{stroke-dashoffset:0}}}}
"""
    # bolhas subindo ao fundo
    for i, (x, y, r, dur, delay) in enumerate([
        (120, 640, 7, 13, 0), (300, 660, 4, 10, 3), (470, 650, 9, 16, 6), (585, 640, 5, 11, 1.5),
        (820, 660, 6, 14, 4), (1010, 650, 10, 17, 8), (1130, 640, 4, 9, 2.5),
    ]):
        d.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="none" stroke="{LIME}" stroke-width="1.2" class="bub" '
              f'style="animation-duration:{dur}s;animation-delay:{delay}s"/>')

    # ── coluna da esquerda ────────────────────────────────────────────────
    d.add(
        f'<g class="in"><circle cx="70" cy="89" r="5" fill="{LIME}" class="beat"/>'
        + d.t(88, 94, "JOINVILLE, SC · BRASIL", "m5", 15, MUTED, ls=2.5) + "</g>"
    )
    name, last = "Flávio", "R."
    full = f"{name} {last}"
    size = min(132, 132 * 540 / FACES["d8"].width(full, 132))
    wname = FACES["d8"].width(full, size)
    d.use("d8", full)
    d.add(
        f'<text x="60" y="226" class="d8 in" font-size="{n(size)}" fill="{TEXT}" letter-spacing="-2" '
        f'style="animation-delay:.12s">{name} <tspan fill="{LIME}">{last}</tspan></text>',
        f'<path d="M66 258C{n(66 + wname * .3)} 246 {n(66 + wname * .62)} 270 {n(50 + wname)} 252" fill="none" '
        f'stroke="{LIME}" stroke-width="6" stroke-linecap="round" class="draw"/>',
        d.t(64, 318, "GERENTE DE TI · SOFTWARE · INTEGRAÇÕES", "m5", 17, TEXT, ls=3, cls="in",
            style="animation-delay:.5s"),
        d.t(64, 364, "Gerente de TI com a mão no código —", "b4", 23, MUTED, cls="in",
            style="animation-delay:.62s"),
        d.t(64, 396, "do contrato ao celular de quem está na rua.", "b4", 23, MUTED, cls="in",
            style="animation-delay:.62s"),
    )
    tags = [
        "gestão de contratos, orçamento e equipe",
        "integrações com SAP Business One e HANA",
        "automação com n8n e agentes de IA",
        "infraestrutura, segurança e LGPD",
    ]
    box = (f'<rect x="60" y="436" width="540" height="52" rx="12" fill="{BG0}" fill-opacity=".55" '
           f'stroke="{LINE}" stroke-width="1.4"/>')
    box += d.t(80, 469, "›", "m5", 21, LIME, cls="blink")
    for i, tag in enumerate(tags):
        box += d.t(106, 468, tag, "m5", 18, TEXT, cls="tag" + (" t0" if i == 0 else ""),
                   style=f"animation-delay:{i * 4}s")
    d.add(f'<g class="in" style="animation-delay:.8s">{box}</g>')
    d.add(d.t(64, 541, "NO GITHUB DESDE 2015 · @flavio-r", "m5", 14, MUTED, ls=2, cls="in",
              style="animation-delay:1s"))

    # ── fluxo de integração à direita ────────────────────────────────────
    NW, NH = 132, 46
    ax, bx, cx = 642, 826, 1010
    A = [("ERP", 152), ("LOJA", 268), ("SITE", 384)]
    B = [("n8n", 204), ("IA · LLM", 332)]
    C = [("HUB", 152), ("CELULAR", 268), ("DASHBOARDS", 384)]
    g = ""
    for x, label in ((ax, "ORIGEM"), (bx, "ORQUESTRA"), (cx, "ENTREGA")):
        g += d.t(x, 104, label, "m5", 12.5, MUTED, ls=2.2)
    edges = [  # (x1, y1, x2, y2, início do pulso)
        (ax + NW, A[0][1], bx, B[0][1], 0.0), (ax + NW, A[1][1], bx, B[0][1], 2.2),
        (ax + NW, A[1][1], bx, B[1][1], 3.1), (ax + NW, A[2][1], bx, B[1][1], 1.0),
        (bx + NW, B[0][1], cx, C[0][1], 1.9), (bx + NW, B[0][1], cx, C[1][1], 4.1),
        (bx + NW, B[1][1], cx, C[1][1], 2.9), (bx + NW, B[1][1], cx, C[2][1], 5.0),
    ]
    for x1, y1, x2, y2, begin in edges:
        p = curve(x1, y1, x2, y2)
        g += (f'<path d="{p}" fill="none" stroke="{LINE}" stroke-width="1.6"/>'
              f'<path d="{p}" fill="none" stroke="{LIME}" stroke-opacity=".55" stroke-width="1.6" class="flow"/>')
        g += pulse(p, 6, begin, travel=0.3)

    def node(x, cy, label, kind):
        y = cy - NH / 2
        s = ""
        if kind == "core":
            s += (f'<rect x="{x}" y="{n(y)}" width="{NW}" height="{NH}" rx="12" fill="none" stroke="{LIME}" '
                  f'stroke-width="1.5" class="halo"/>'
                  f'<rect x="{x}" y="{n(y)}" width="{NW}" height="{NH}" rx="12" fill="{PANEL2}" stroke="{LIME}" '
                  f'stroke-width="1.6"/>'
                  f'<rect x="{x + 12}" y="{n(cy - 10)}" width="20" height="20" rx="6" fill="{LIME}"/>')
        elif kind == "in":
            s += (f'<rect x="{x}" y="{n(y)}" width="{NW}" height="{NH}" rx="12" fill="{PANEL}" stroke="{LINE}" '
                  f'stroke-width="1.4"/>'
                  f'<circle cx="{x + 22}" cy="{cy}" r="8" fill="none" stroke="{LIME}" stroke-width="2"/>'
                  f'<circle cx="{x + 22}" cy="{cy}" r="2.6" fill="{LIME}"/>')
        else:
            s += (f'<rect x="{x}" y="{n(y)}" width="{NW}" height="{NH}" rx="12" fill="{PANEL}" stroke="{LINE}" '
                  f'stroke-width="1.4"/>'
                  f'<rect x="{x + 13}" y="{n(cy - 9)}" width="18" height="18" rx="5" fill="{MINT}"/>')
        s += d.t(x + 40, cy + 5, label, "m5", 13.5, TEXT, ls=.4)
        return s

    for label, cy in A:
        g += node(ax, cy, label, "in")
    for label, cy in B:
        g += node(bx, cy, label, "core")
    for label, cy in C:
        g += node(cx, cy, label, "out")
    # registro do que passou pelo fluxo
    g += (f'<rect x="{ax}" y="440" width="{cx + NW - ax}" height="108" rx="14" fill="{BG0}" fill-opacity=".6" '
          f'stroke="{LINE}" stroke-width="1.4"/>'
          f'<circle cx="{cx + NW - 132}" cy="462" r="4" fill="{LIME}" class="beat"/>'
          + d.t(cx + NW - 120, 467, "FLUXO ATIVO", "m5", 12, MUTED, ls=1.8)
          + d.t(ax + 22, 470, "→ pedido recebido na loja", "m5", 14.5, TEXT, cls="l1")
          + d.t(ax + 22, 498, "→ documento lido e validado por IA", "m5", 14.5, TEXT, cls="l2")
          + d.t(ax + 22, 526, "✓ SAP atualizado · time avisado", "m5", 14.5, LIME2, cls="l3"))
    d.add(f'<g class="in" style="animation-delay:.4s">{g}</g>')
    d.save()


# ══════════════════════════════════════════════════════════════════════════
# 01 · GESTÃO DE TI
# ══════════════════════════════════════════════════════════════════════════
GESTAO_ICONES = {
    "contratos": '<path d="M7 3h8l4 4v14H7z"/><path d="M15 3v4h4"/><path d="M10 12h6M10 16h3"/><path d="M4 7v14h3"/>',
    "orcamento": '<path d="M3 20h18"/><path d="M6 20v-6M11 20V9M16 20v-9M21 20V5"/><path d="M4 9l5-4 4 3 6-5"/>',
    "negociacao": '<path d="M4 8h14l-3.5-3.5"/><path d="M20 16H6l3.5 3.5"/>',
    "infra": '<rect x="3" y="4" width="18" height="7" rx="2"/><rect x="3" y="13" width="18" height="7" rx="2"/>'
             '<path d="M7 7.5h.01M7 16.5h.01M11 7.5h6M11 16.5h6"/>',
    "seguranca": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    "equipe": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.8-3.5 3.4-5.5 6.5-5.5s5.7 2 6.5 5.5"/>'
              '<path d="M16 4.5a3.5 3.5 0 0 1 0 7M18 14.8c1.8.7 3 2.5 3.5 5.2"/>',
    "suporte": '<path d="M4 14v-2a8 8 0 0 1 16 0v2"/><rect x="3" y="14" width="4" height="6" rx="1.5"/>'
               '<rect x="17" y="14" width="4" height="6" rx="1.5"/><path d="M19 20c0 1.2-1.2 2-3 2h-3"/>',
    "estrategia": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.4"/>',
}


def gestao():
    areas = [
        ("contratos", "Contratos", "Licenças, links, nuvem e suporte, com SLA cobrado."),
        ("orcamento", "Orçamento", "Custeio, investimento e realizado × orçado."),
        ("negociacao", "Negociação", "Mais de uma cotação; preço, prazo e SLA juntos."),
        ("infra", "Infraestrutura", "Servidores, rede, firewall, VPN e o ambiente do HANA."),
        ("seguranca", "Segurança e LGPD", "Acesso por cargo, MFA, backup testado e LGPD."),
        ("equipe", "Equipe", "Prioridades claras, sustentação e projetos."),
        ("suporte", "Suporte", "Chamados com prazo, inventário e treinamento."),
        ("estrategia", "Estratégia", "Roadmap do negócio e indicadores à diretoria."),
    ]
    cad = [("DIÁRIO", "sistemas e chamados"), ("SEMANAL", "projetos e fornecedores"),
           ("MENSAL", "realizado × orçado"), ("ANUAL", "orçamento e contratos")]
    W, cw, gap, ch, y0 = 1200, 258, 16, 168, 214
    cy0 = y0 + 2 * ch + gap + 20
    H = cy0 + 100 + 44
    label = ("Gestão de TI — " + "; ".join(f"{t}: {d}" for _, t, d in areas)
             + ". Cadência: " + "; ".join(f"{a.lower()}: {b}" for a, b in cad) + ".")
    d = Doc("01-gestao", W, H, label, glow=(1080, 120, 420))
    d.css = Template("""
.lit{animation:lit 12s ease-in-out infinite}
@keyframes lit{0%,9%,100%{stroke:$LINE}3%{stroke:$LIME}}
.ico{animation:ico 12s ease-in-out infinite}
@keyframes ico{0%,9%,100%{stroke:$LIME}3%{stroke:$LIME2}}
.run{animation:run 9s ease-in-out infinite}
@keyframes run{0%{transform:translateX(0);opacity:0}6%,88%{opacity:1}96%,100%{transform:translateX(860px);opacity:0}}
""").substitute(LINE=LINE, LIME=LIME, LIME2=LIME2)
    header(d, "01", "GESTÃO DE TI", "Da negociação ao servidor",
           "Contratos, orçamento, infraestrutura, segurança e pessoas — sem largar o código.")
    for i, (key, title, desc) in enumerate(areas):
        x, y = 60 + (i % 4) * (cw + gap), y0 + (i // 4) * (ch + gap)
        delay = f"animation-delay:{i * 1.5:.1f}s"
        g = (f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="16" fill="{PANEL}" fill-opacity=".85" '
             f'stroke="{LINE}" stroke-width="1.4" class="lit" style="{delay}"/>'
             f'<rect x="{x + 20}" y="{y + 20}" width="52" height="52" rx="14" fill="{LIME}" fill-opacity=".1" '
             f'stroke="{LIME}" stroke-opacity=".35" stroke-width="1.2"/>'
             f'<g transform="translate({x + 31} {y + 31}) scale(1.25)" fill="none" stroke="{LIME}" stroke-width="1.7" '
             f'stroke-linecap="round" stroke-linejoin="round" class="ico" style="{delay}">{GESTAO_ICONES[key]}</g>'
             + d.t(x + cw - 20, y + 42, f"0{i + 1}", "m5", 13, MUTED, anchor="end", ls=1.2)
             + d.t(x + 20, y + 104, title, "d6", 21, TEXT))
        lines = FACES["b4"].wrap(desc, 16.5, cw - 40)
        assert len(lines) <= 2, f"descrição longa demais em {title}: {lines}"
        for j, line in enumerate(lines):
            g += d.t(x + 20, y + 131 + j * 22, line, "b4", 16.5, MUTED)
        d.add(f'<g class="in" style="animation-delay:{.3 + i * .07:.2f}s">{g}</g>')

    # cadência
    lx0, lx1, ly = 250, 1120, cy0 + 34
    g = (f'<rect x="60" y="{cy0}" width="1080" height="100" rx="16" fill="{BG0}" fill-opacity=".55" '
         f'stroke="{LINE}" stroke-width="1.4"/>'
         + d.t(86, ly + 5, "CADÊNCIA", "m5", 13, MUTED, ls=2.4)
         + f'<path d="M{lx0} {ly}H{lx1}" stroke="{LINE}" stroke-width="2"/>'
         f'<path d="M{lx0} {ly}H{lx1}" stroke="{LIME}" stroke-opacity=".5" stroke-width="2" class="flow"/>'
         f'<g class="run"><circle cx="{lx0}" cy="{ly}" r="11" fill="{LIME}" opacity=".2"/>'
         f'<circle cx="{lx0}" cy="{ly}" r="5" fill="{LIME2}"/></g>')
    seg = (lx1 - lx0) / 4
    for i, (pill, text) in enumerate(cad):
        x = lx0 + i * seg
        w = FACES["m5"].width(pill, 12.5, 1.8) + 26
        g += (f'<rect x="{n(x)}" y="{ly - 14}" width="{n(w)}" height="28" rx="14" fill="{BG0}" stroke="{LIME}" '
              f'stroke-width="1.5"/>' + d.t(x + 13, ly + 4.5, pill, "m5", 12.5, LIME, ls=1.8)
              + d.t(x + 2, ly + 40, text, "b4", 15, TEXT))
        assert FACES["b4"].width(text, 15) < seg - 16, f"cadência longa demais: {text}"
    d.add(f'<g class="in" style="animation-delay:.9s">{g}</g>')
    d.save()


# ══════════════════════════════════════════════════════════════════════════
# 02 · FRENTES
# ══════════════════════════════════════════════════════════════════════════
def icon_painel():
    s = (f'<rect x="4" y="8" width="56" height="48" rx="9" fill="none" stroke="{LIME}" stroke-width="2.2"/>'
         f'<path d="M4 21H60" stroke="{LIME}" stroke-width="2.2"/>'
         f'<circle cx="12" cy="14.5" r="1.8" fill="{LIME}"/><circle cx="19" cy="14.5" r="1.8" fill="{LIME}"/>')
    for i, (x, hgt) in enumerate(((14, 14), (27, 24), (40, 18))):
        s += (f'<rect x="{x}" y="{50 - hgt}" width="9" height="{hgt}" rx="2.5" fill="{LIME2 if i == 1 else LIME}" '
              f'class="bar" style="animation-delay:{i * .35}s"/>')
    return s


def icon_integra():
    return (
        f'<rect x="3" y="5" width="24" height="24" rx="7" fill="none" stroke="{LIME}" stroke-width="2.2"/>'
        f'<rect x="37" y="35" width="24" height="24" rx="7" fill="{LIME}" fill-opacity=".18" stroke="{LIME}" stroke-width="2.2"/>'
        f'<path d="M27 15H41a8 8 0 0 1 8 8V35" fill="none" stroke="{LIME2}" stroke-width="2.2" stroke-linecap="round" class="flow"/>'
        f'<path d="M37 49H23a8 8 0 0 1 -8 -8V29" fill="none" stroke="{MINT}" stroke-width="2.2" stroke-linecap="round" class="flow"/>'
        f'<circle cx="15" cy="17" r="3" fill="{LIME}"/><circle cx="49" cy="47" r="3" fill="{LIME2}"/>'
    )


def icon_ia():
    star = "M0 -24C2 -8 8 -2 24 0C8 2 2 8 0 24C-2 8 -8 2 -24 0C-8 -2 -2 -8 0 -24Z"
    return (
        f'<g transform="translate(28 36)"><path d="{star}" fill="{LIME}" class="star"/></g>'
        f'<g transform="translate(52 12) scale(.4)"><path d="{star}" fill="{LIME2}" class="star" style="animation-delay:-1.3s"/></g>'
        f'<g transform="translate(56 54) scale(.22)"><path d="{star}" fill="{MINT}" class="star" style="animation-delay:-2.1s"/></g>'
    )


def icon_infra():
    s = ""
    for i, y in enumerate((42, 25, 8)):
        s += (f'<g class="drop" style="animation-delay:{i * .4}s"><rect x="6" y="{y}" width="52" height="13" rx="4.5" '
              f'fill="{LIME}" fill-opacity="{.12 + i * .1}" stroke="{LIME}" stroke-width="2.2"/>'
              f'<circle cx="14" cy="{y + 6.5}" r="2" fill="{LIME2}"/><path d="M22 {y + 6.5}H34" stroke="{LIME}" '
              f'stroke-width="2.2" stroke-linecap="round"/></g>')
    return s


def frentes():
    W, H = 1200, 540
    d = Doc("01-frentes", W, H, "O que eu faço: sistemas internos, integrações, automação e IA, infra e entrega",
            glow=(140, 560, 380))
    d.css = """
.bar{transform-box:fill-box;transform-origin:50% 100%;animation:bar 2.8s ease-in-out infinite}
@keyframes bar{0%,100%{transform:scaleY(.45)}50%{transform:scaleY(1)}}
.star{transform-box:fill-box;transform-origin:center;animation:star 3.4s ease-in-out infinite}
@keyframes star{0%,100%{transform:scale(1) rotate(0)}50%{transform:scale(.72) rotate(45deg)}}
.drop{opacity:0;animation:drop 5s cubic-bezier(.22,1,.36,1) infinite}
@keyframes drop{0%{opacity:0;transform:translateY(-12px)}12%,84%{opacity:1;transform:none}96%,100%{opacity:0}}
@media (prefers-reduced-motion:reduce){.drop{opacity:1}}
"""
    header(d, "02", "O QUE EU FAÇO", "Quatro frentes, um mesmo sistema",
           "Tecnologia, da regra de negócio até o deploy.")
    cards = [
        ("Sistemas internos", "Hubs, portais, painéis e gestão.", icon_painel),
        ("Integrações", "SAP Business One e HANA ligados a APIs, lojas e apps.", icon_integra),
        ("Automação e IA", "Fluxos n8n, agentes e LLMs que leem documentos e e-mails.", icon_ia),
        ("Infra e entrega", "Docker, NGINX, Portainer e CI para pôr tudo no ar.", icon_infra),
    ]
    cw, gap, y0, ch = 255, 20, 214, 276
    for i, (title, desc, icon) in enumerate(cards):
        x = 60 + i * (cw + gap)
        s = (f'<rect x="{x}" y="{y0}" width="{cw}" height="{ch}" rx="18" fill="{PANEL}" fill-opacity=".85" '
             f'stroke="{LINE}" stroke-width="1.4"/>'
             f'<rect x="{x + 22}" y="{y0 + 22}" width="84" height="84" rx="20" fill="{LIME}" fill-opacity=".08" '
             f'stroke="{LIME}" stroke-opacity=".3" stroke-width="1.2"/>'
             f'<g transform="translate({x + 32} {y0 + 32})">{icon()}</g>'
             + d.t(x + cw - 24, y0 + 48, f"0{i + 1}", "m5", 15, MUTED, anchor="end", ls=1.5)
             + d.t(x + 22, y0 + 150, title, "d6", 25, TEXT))
        for j, line in enumerate(FACES["b4"].wrap(desc, 18.5, cw - 44)):
            s += d.t(x + 22, y0 + 184 + j * 25, line, "b4", 18.5, MUTED)
        d.add(f'<g class="in" style="animation-delay:{.35 + i * .12:.2f}s">{s}</g>')
    d.save()


# ══════════════════════════════════════════════════════════════════════════
# 03 · STACK
# ══════════════════════════════════════════════════════════════════════════
def stack():
    rows = [
        ("LINGUAGENS", ["TypeScript", "JavaScript", "PHP", "Python", "Kotlin"]),
        ("FRONT-END", ["React", "Material UI", "HTML & CSS"]),
        ("BACK-END", ["Node.js", "Express", "APIs REST"]),
        ("DADOS E ERP", ["SAP Business One", "SAP HANA", "MySQL"]),
        ("AUTOMAÇÃO E IA", ["n8n", "LLMs", "OCR · Tesseract"]),
        ("INFRA", ["Docker", "NGINX", "Portainer", "Jenkins", "GitHub Actions"]),
    ]
    rh, y0 = 58, 168
    W, H = 1200, y0 + rh * len(rows) + 34
    d = Doc("02-stack", W, H, "Ferramentas: " + "; ".join(f"{k}: {', '.join(v)}" for k, v in rows),
            glow=(1100, 40, 360))
    d.css = f"""
.chip{{animation:lit 9s ease-in-out infinite}}
@keyframes lit{{0%,6%,100%{{stroke:{LINE};fill:{PANEL}}}2.5%{{stroke:{LIME};fill:{PANEL2}}}}}
"""
    header(d, "03", "FERRAMENTAS", "Stack do dia a dia")
    k = 0
    for i, (label, chips) in enumerate(rows):
        cy = y0 + i * rh + rh / 2
        s = f'<path d="M64 {n(cy - rh / 2)}H1136" stroke="{LINE}" stroke-width="1" stroke-opacity=".7"/>'
        s += d.t(64, cy + 5, label, "m5", 14, MUTED, ls=2.4)
        x = 300
        for chip in chips:
            w = FACES["m5"].width(chip, 16) + 46
            s += (f'<g class="in" style="animation-delay:{.3 + k * .05:.2f}s">'
                  f'<rect x="{n(x)}" y="{n(cy - 19)}" width="{n(w)}" height="38" rx="11" fill="{PANEL}" stroke="{LINE}" '
                  f'stroke-width="1.4" class="chip" style="animation-delay:{k * .38:.2f}s"/>'
                  f'<circle cx="{n(x + 17)}" cy="{n(cy)}" r="3.5" fill="{LIME}"/>'
                  + d.t(x + 30, cy + 5.5, chip, "m5", 16, TEXT) + "</g>")
            x += w + 12
            k += 1
        d.add(s)
    d.save()


# ══════════════════════════════════════════════════════════════════════════
# 04 · PROJETOS
# ══════════════════════════════════════════════════════════════════════════
def art_mensagens():
    s = (f'<rect x="8" y="20" width="96" height="68" rx="10" fill="{PANEL2}" stroke="{LIME}" stroke-width="1.8"/>'
         f'<path d="M11 27L56 60L101 27" fill="none" stroke="{LIME}" stroke-width="1.8" stroke-linejoin="round"/>'
         f'<circle cx="104" cy="20" r="9" fill="{LIME}" class="ring"/><circle cx="104" cy="20" r="9" fill="{LIME}"/>'
         f'<path d="M72 78H140a14 14 0 0 1 14 14V124a14 14 0 0 1 -14 14H138L146 154L122 138H72a14 14 0 0 1 -14 -14V92'
         f'a14 14 0 0 1 14 -14Z" fill="#0d5244" stroke="{LIME2}" stroke-width="1.8" stroke-linejoin="round"/>')
    for i, x in enumerate((86, 106, 126)):
        s += f'<circle cx="{x}" cy="108" r="5" fill="{LIME2}" class="dot" style="animation-delay:{i * .18:.2f}s"/>'
    return s


def art_documento():
    s = (f'<path d="M36 8H104L124 28V136a8 8 0 0 1 -8 8H44a8 8 0 0 1 -8 -8Z" fill="{PANEL2}" stroke="{LIME}" '
         f'stroke-width="1.8" stroke-linejoin="round"/><path d="M104 8V28H124" fill="none" stroke="{LIME}" '
         f'stroke-width="1.8" stroke-linejoin="round"/>')
    for i, (y, w) in enumerate(((46, 44), (62, 60), (78, 52), (94, 60), (110, 34))):
        s += (f'<path d="M50 {y}h{w}" stroke="{MUTED}" stroke-opacity=".5" stroke-width="4.5" stroke-linecap="round" '
              f'class="ln" style="animation-delay:{.55 + i * .4:.2f}s"/>')
    s += (f'<g class="scan"><rect x="26" y="-14" width="108" height="16" fill="url(#scan)"/>'
          f'<rect x="24" y="0" width="112" height="3" rx="1.5" fill="{LIME2}"/></g>')
    return s


def art_balancer():
    paths = ["M92 80C110 80 108 30 126 30", "M92 80H126", "M92 80C110 80 108 130 126 130"]
    s = f'<path d="M30 80H60" stroke="{LINE}" stroke-width="1.8"/>'
    s += f'<path d="M30 80H60" stroke="{LIME}" stroke-opacity=".6" stroke-width="1.8" class="flow"/>'
    for p in paths:
        s += (f'<path d="{p}" fill="none" stroke="{LINE}" stroke-width="1.8"/>'
              f'<path d="{p}" fill="none" stroke="{LIME}" stroke-opacity=".6" stroke-width="1.8" class="flow"/>')
    for i, p in enumerate(paths):
        s += pulse("M30 80H60", 3.6, i * 1.2, travel=.14, r=3.2)
        s += pulse(p, 3.6, i * 1.2 + .5, travel=.2, r=3.2)
        y = (16, 66, 116)[i]
        s += (f'<rect x="126" y="{y}" width="32" height="28" rx="7" fill="{LIME}" fill-opacity=".12" stroke="{LIME}" '
              f'stroke-width="1.8"><animate attributeName="fill-opacity" dur="3.6s" begin="{i * 1.2 + 1.2:.1f}s" '
              f'repeatCount="indefinite" values=".12;.75;.12;.12" keyTimes="0;.06;.3;1"/></rect>')
    s += (f'<circle cx="18" cy="80" r="12" fill="{PANEL2}" stroke="{MINT}" stroke-width="1.8"/>'
          f'<circle cx="18" cy="80" r="3.5" fill="{MINT}"/>'
          f'<rect x="60" y="62" width="32" height="36" rx="9" fill="{PANEL2}" stroke="{LIME}" stroke-width="1.8"/>'
          f'<path d="M69 74H83M69 80H83M69 86H83" stroke="{LIME2}" stroke-width="2" stroke-linecap="round"/>')
    return s


def projetos():
    d = Doc("03-projetos", 1200, 216, "Projetos — uma amostra do que já construí", glow=(1060, 240, 340))
    header(d, "04", "TRABALHOS", "Projetos", "Uma amostra do que já construí.")
    arrow = f'<g class="bob"><path d="M1108 96V150M1088 132L1108 152L1128 132" fill="none" stroke="{LIME}" ' \
            f'stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></g>'
    d.css = ".bob{animation:bob 2.2s ease-in-out infinite}@keyframes bob{50%{transform:translateY(8px)}}"
    d.add(arrow)
    d.save()

    cards = [
        ("E-mail e WhatsApp", "EVOLUTION API · MENSAGERIA",
         "Integração com e-mail e WhatsApp, via Evolution API, usada como canal de mensagens das minhas "
         "integrações.", art_mensagens),
        ("Document Interpreter", "NODE.JS · EXPRESS · OCR",
         "API que recebe PDFs e imagens e devolve o texto, com pdf-parse e Tesseract em português.",
         art_documento),
        ("Load Balancer", "DOCKER · NGINX",
         "Exemplo de balanceamento de carga entre dois ou mais containers Docker usando NGINX.",
         art_balancer),
    ]
    # os três lado a lado numa imagem só: ficam em linha em qualquer lugar que mostre o README
    cw, gap, y0 = 346, 21, 44
    tsize = min(min(30, 30 * (cw - 44) / FACES["d8"].width(c[0], 30)) for c in cards)
    wrapped = [FACES["b4"].wrap(c[2], 18.5, cw - 44) for c in cards]
    ch = 346 + max(len(w) for w in wrapped) * 25 + 4
    W, H = 1200, y0 * 2 + ch
    d = Doc("03-cards", W, H, "Projetos: " + "; ".join(f"{c[0]} — {c[2]}" for c in cards), glow=(600, H, 420))
    d.defs = (f'<linearGradient id="scan" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{LIME}" '
              f'stop-opacity="0"/><stop offset="1" stop-color="{LIME}" stop-opacity=".35"/></linearGradient>')
    d.css = Template("""
.scan{animation:scan 3.2s ease-in-out infinite alternate}@keyframes scan{from{transform:translateY(22px)}to{transform:translateY(132px)}}
.ln{animation:ln 6.4s ease-in-out infinite}@keyframes ln{0%,100%{stroke:$MUTED;stroke-opacity:.5}4%,48%{stroke:$LIME2;stroke-opacity:1}58%{stroke:$MUTED;stroke-opacity:.5}}
.dot{animation:dot 1.4s ease-in-out infinite}@keyframes dot{0%,60%,100%{transform:none;opacity:.45}30%{transform:translateY(-6px);opacity:1}}
.ring{transform-box:fill-box;transform-origin:center;animation:ring 2.4s ease-out infinite}
@keyframes ring{0%{transform:scale(1);opacity:.7}100%{transform:scale(2.6);opacity:0}}
""").substitute(MUTED=MUTED, LIME2=LIME2)
    for i, (title, tech, desc, art) in enumerate(cards):
        x = 60 + i * (cw + gap)
        g = (f'<rect x="{x}" y="{y0}" width="{cw}" height="{ch}" rx="18" fill="{PANEL}" fill-opacity=".85" '
             f'stroke="{LINE}" stroke-width="1.4"/>'
             f'<rect x="{x + 22}" y="{y0 + 22}" width="70" height="30" rx="15" fill="{LIME}"/>'
             + d.t(x + 57, y0 + 42.5, f"P/0{i + 1}", "m5", 14.5, BG0, anchor="middle", ls=.5)
             + f'<g transform="translate({x + (cw - 160) // 2} {y0 + 62})">{art()}</g>'
             f'<path d="M{x + 22} {y0 + 240}H{x + cw - 22}" stroke="{LINE}" stroke-width="1.2"/>'
             + d.t(x + 21, y0 + 284, title, "d8", tsize, TEXT)
             + d.t(x + 22, y0 + 312, tech, "m5", 14, LIME, ls=1.6))
        for j, line in enumerate(wrapped[i]):
            g += d.t(x + 22, y0 + 346 + j * 25, line, "b4", 18.5, MUTED)
        d.add(f'<g class="in" style="animation-delay:{.15 + i * .12:.2f}s">{g}</g>')
    d.save()


# ══════════════════════════════════════════════════════════════════════════
# 04 · DESTAQUE — Monitor HANA
# ══════════════════════════════════════════════════════════════════════════
def destaque():
    W, H = 1200, 470
    desc = ("Monitoramento do SAP HANA e do servidor Linux com olhar de DBA: memória, disco, backup, "
            "conexões, travas e consultas longas. Avisa por e-mail antes de o banco parar.")
    d = Doc("03-destaque", W, H, f"Projeto em destaque: Monitor HANA — {desc}", glow=(900, 230, 430))
    d.css = Template("""
.vA{animation:vA 10s infinite}@keyframes vA{0%,38%{opacity:1}42%,78%{opacity:0}82%,100%{opacity:1}}
.vB{opacity:0;animation:vB 10s infinite}@keyframes vB{0%,38%{opacity:0}42%,78%{opacity:1}82%,100%{opacity:0}}
.dk{animation:dk 10s infinite}@keyframes dk{0%,38%{stroke:$LINE}42%,78%{stroke:$LIME2}82%,100%{stroke:$LINE}}
.bar{transform-box:fill-box;transform-origin:0 50%}
.mbar{animation:mbar 6s ease-in-out infinite}@keyframes mbar{0%,100%{transform:scaleX(.55)}50%{transform:scaleX(.67)}}
.dbar{animation:dbar 10s ease-in-out infinite}
@keyframes dbar{0%,34%{transform:scaleX(.7);fill:$LIME}44%,76%{transform:scaleX(.94);fill:$LIME2}86%,100%{transform:scaleX(.7);fill:$LIME}}
.spark{stroke-dasharray:170;stroke-dashoffset:170;animation:spark 5s ease-in-out infinite}
@keyframes spark{0%{stroke-dashoffset:170;opacity:1}50%,88%{stroke-dashoffset:0;opacity:1}100%{stroke-dashoffset:0;opacity:0}}
.toast{opacity:0;animation:toast 10s infinite}
@keyframes toast{0%,46%{opacity:0;transform:translateY(10px)}50%,78%{opacity:1;transform:none}84%,100%{opacity:0}}
@media (prefers-reduced-motion:reduce){.spark{stroke-dashoffset:0}}
""").substitute(LINE=LINE, LIME=LIME, LIME2=LIME2)

    # ── texto ─────────────────────────────────────────────────────────────
    d.add(
        f'<rect x="64" y="58" width="122" height="32" rx="16" fill="{LIME}"/>',
        d.t(125, 79.5, "DESTAQUE", "m5", 14.5, BG0, anchor="middle", ls=1.5),
        d.t(202, 79.5, "LAB TI", "m5", 14, MUTED, ls=2),
        d.t(61, 156, "Monitor HANA", "d8", 56, TEXT, cls="in"),
        d.t(64, 192, "NODE.JS · PYTHON · SAP HANA · LINUX", "m5", 14.5, LIME, ls=1.8, cls="in",
            style="animation-delay:.1s"),
    )
    lines = FACES["b4"].wrap(desc, 21, 520)
    for j, line in enumerate(lines):
        d.add(d.t(64, 234 + j * 30, line, "b4", 21, MUTED, cls="in", style="animation-delay:.2s"))
    x, y = 64, 234 + len(lines) * 30 - 2
    for k, chip in enumerate(["leitura a cada 5 min", "alertas por e-mail", "agente no servidor Linux",
                              "painel para TV"]):
        w = FACES["m5"].width(chip, 14.5) + 44
        if x + w > 600:
            x, y = 64, y + 44
        d.add(f'<g class="in" style="animation-delay:{.35 + k * .08:.2f}s">'
              f'<rect x="{n(x)}" y="{y}" width="{n(w)}" height="34" rx="10" fill="{PANEL}" stroke="{LINE}" '
              f'stroke-width="1.4"/><path d="M{n(x + 13)} {y + 17}l4 4l7 -8" fill="none" stroke="{LIME}" '
              f'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
              + d.t(x + 32, y + 22, chip, "m5", 14.5, TEXT) + "</g>")
        x += w + 10

    # ── painel do monitor ────────────────────────────────────────────────
    g = (f'<rect x="640" y="60" width="500" height="346" rx="18" fill="{BG0}" fill-opacity=".62" stroke="{LINE}" '
         f'stroke-width="1.4"/>'
         f'<rect x="660" y="80" width="460" height="44" rx="12" fill="{PANEL2}" stroke="{LIME}" stroke-opacity=".5" '
         f'stroke-width="1.3"/><circle cx="682" cy="102" r="5" fill="{LIME}" class="beat"/>'
         + d.t(700, 107, "BANCO FOLGADO", "m5", 14.5, TEXT, ls=1.6, cls="vA")
         + d.t(700, 107, "DISCO PEDE ATENÇÃO", "m5", 14.5, LIME2, ls=1.6, cls="vB")
         + d.t(1102, 106.5, "A CADA 5 MIN", "m5", 12, MUTED, anchor="end", ls=1.6))
    spark = ("M0 22L14 18L28 24L42 12L56 16L70 6L84 14L100 9L116 13",
             "M0 10L14 14L28 8L42 18L56 13L70 20L84 11L100 16L116 7")
    cards = [("MEMÓRIA", "mbar"), ("PROCESSADOR", "spark0"), ("DISCO", "dbar"),
             ("BACKUP", "ok"), ("CONEXÕES", "spark1"), ("LINUX", "agente")]
    for i, (label, kind) in enumerate(cards):
        x, y = 660 + (i % 3) * 158, 138 + (i // 3) * 100
        g += (f'<rect x="{x}" y="{y}" width="144" height="88" rx="12" fill="{PANEL}" stroke="{LINE}" '
              f'stroke-width="1.3"{" class=" + chr(34) + "dk" + chr(34) if kind == "dbar" else ""}/>'
              + d.t(x + 14, y + 27, label, "m5", 11.5, MUTED, ls=1.3))
        if kind in ("mbar", "dbar"):
            g += (f'<rect x="{x + 14}" y="{y + 50}" width="116" height="12" rx="6" fill="{LINE}"/>'
                  f'<rect x="{x + 14}" y="{y + 50}" width="116" height="12" rx="6" fill="{LIME}" class="bar {kind}"/>')
        elif kind.startswith("spark"):
            j = int(kind[-1])
            g += (f'<g transform="translate({x + 14} {y + 42})"><path d="{spark[j]}" fill="none" stroke="{LINE}" '
                  f'stroke-width="2" stroke-linejoin="round"/><path d="{spark[j]}" fill="none" stroke="{LIME}" '
                  f'stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round" class="spark" '
                  f'style="animation-delay:{j * 1.3}s"/></g>')
        elif kind == "ok":
            g += (f'<circle cx="{x + 25}" cy="{y + 58}" r="11" fill="{LIME}" fill-opacity=".14" stroke="{LIME}" '
                  f'stroke-width="1.6"/><path d="M{x + 20} {y + 58}l3.6 3.6l6.6 -7.4" fill="none" stroke="{LIME2}" '
                  f'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
                  + d.t(x + 45, y + 63, "em dia", "m5", 13.5, TEXT))
        else:
            g += (f'<circle cx="{x + 20}" cy="{y + 58}" r="5" fill="{MINT}" class="beat"/>'
                  + d.t(x + 33, y + 63, "agente ativo", "m5", 13, TEXT))
    g += (f'<rect x="660" y="340" width="460" height="44" rx="12" fill="none" stroke="{LINE}" stroke-width="1.2" '
          f'stroke-dasharray="4 5"/>' + d.t(682, 367, "SEM ALERTAS ABERTOS", "m5", 12.5, MUTED, ls=1.6)
          + f'<g class="toast"><rect x="660" y="340" width="460" height="44" rx="12" fill="{LIME}"/>'
          f'<rect x="680" y="353" width="24" height="18" rx="3.5" fill="none" stroke="{BG0}" stroke-width="2"/>'
          f'<path d="M681 355l11 8.5l11 -8.5" fill="none" stroke="{BG0}" stroke-width="2" stroke-linejoin="round"/>'
          + d.t(718, 367.5, "ALERTA ENVIADO POR E-MAIL", "m5", 13.5, BG0, ls=1.5) + "</g>")
    d.add(f'<g class="in" style="animation-delay:.3s">{g}</g>')
    d.save()


# ══════════════════════════════════════════════════════════════════════════
# 04 · DESTAQUE — ClawdDesk (código aberto)
# ══════════════════════════════════════════════════════════════════════════
def clawddesk():
    W, H = 1200, 470
    desc = ("Transforma um celular antigo num monitor de mesa para o Claude Code: sessões em tempo real, "
            "limites de uso, tempo por projeto e aprovação de permissões pelo celular.")
    d = Doc("03-clawddesk", W, H, f"Projeto em destaque, código aberto: ClawdDesk — {desc}", glow=(900, 230, 430))
    d.css = Template("""
.s2,.s3,.perm,.okk{opacity:0}
.s1{animation:s1 12s infinite}.s2{animation:s2 12s infinite}.s3{animation:s3 12s infinite}
@keyframes s1{0%,28%{opacity:1}31%,94%{opacity:0}97%,100%{opacity:1}}
@keyframes s2{0%,30%{opacity:0}33%,70%{opacity:1}73%,100%{opacity:0}}
@keyframes s3{0%,72%{opacity:0}75%,93%{opacity:1}96%,100%{opacity:0}}
.rc{animation:rc 12s infinite}
@keyframes rc{0%,30%{stroke:$LIME}33%,70%{stroke:$LIME2}75%,94%{stroke:$MINT}97%,100%{stroke:$LIME}}
.ctx{animation:ctx 6s ease-in-out infinite alternate}@keyframes ctx{from{stroke-dashoffset:160}to{stroke-dashoffset:118}}
.perm{animation:perm 12s infinite}
@keyframes perm{0%,31%{opacity:0;transform:translateY(12px)}35%,70%{opacity:1;transform:none}73%,100%{opacity:0}}
.q{animation:q 12s infinite}@keyframes q{0%,58%{opacity:1}60%,100%{opacity:0}}
.okk{animation:okk 12s infinite}@keyframes okk{0%,58%{opacity:0}60%,100%{opacity:1}}
.pbtn{animation:pb 12s infinite}@keyframes pb{0%,54%,64%,100%{fill:$LIME}56%,62%{fill:$LIME2}}
.tap{opacity:0;transform-box:fill-box;transform-origin:center;animation:tap 12s infinite}
@keyframes tap{0%,54%{opacity:0;transform:scale(.4)}56%{opacity:.55;transform:scale(.7)}63%,100%{opacity:0;transform:scale(1.7)}}
.lb{transform-box:fill-box;transform-origin:0 50%}
.l5{animation:l5 7s ease-in-out infinite alternate}@keyframes l5{from{transform:scaleX(.38)}to{transform:scaleX(.46)}}
""").substitute(LIME=LIME, LIME2=LIME2, MINT=MINT)

    # ── texto ─────────────────────────────────────────────────────────────
    d.add(
        f'<rect x="64" y="58" width="122" height="32" rx="16" fill="{LIME}"/>',
        d.t(125, 79.5, "DESTAQUE", "m5", 14.5, BG0, anchor="middle", ls=1.5),
        d.t(202, 79.5, "CÓDIGO ABERTO · GITHUB ↗", "m5", 14, MUTED, ls=2),
        d.t(61, 156, "ClawdDesk", "d8", 56, TEXT, cls="in"),
        d.t(64, 192, "NODE.JS · PWA · WEBSOCKET · CLAUDE CODE", "m5", 14.5, LIME, ls=1.8, cls="in",
            style="animation-delay:.1s"),
    )
    lines = FACES["b4"].wrap(desc, 21, 520)
    assert len(lines) <= 4, lines
    for j, line in enumerate(lines):
        d.add(d.t(64, 234 + j * 30, line, "b4", 21, MUTED, cls="in", style="animation-delay:.2s"))
    x, y = 64, 234 + len(lines) * 30 - 2
    for k, chip in enumerate(["tempo real pelo Wi-Fi", "sem nuvem", "aprovação pelo celular", "tema claro e escuro"]):
        w = FACES["m5"].width(chip, 14.5) + 44
        if x + w > 600:
            x, y = 64, y + 44
        d.add(f'<g class="in" style="animation-delay:{.35 + k * .08:.2f}s">'
              f'<rect x="{n(x)}" y="{y}" width="{n(w)}" height="34" rx="10" fill="{PANEL}" stroke="{LINE}" '
              f'stroke-width="1.4"/><path d="M{n(x + 13)} {y + 17}l4 4l7 -8" fill="none" stroke="{LIME}" '
              f'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
              + d.t(x + 32, y + 22, chip, "m5", 14.5, TEXT) + "</g>")
        x += w + 10

    # ── celular no suporte ───────────────────────────────────────────────
    g = (f'<path d="M846 350L826 404H954L934 350Z" fill="{PANEL}" stroke="{LINE}" stroke-width="1.6" '
         f'stroke-linejoin="round"/><path d="M790 405H990" stroke="{LINE}" stroke-width="2" stroke-linecap="round"/>'
         f'<rect x="650" y="88" width="480" height="264" rx="34" fill="#010a09" stroke="{LINE}" stroke-width="2"/>'
         f'<circle cx="664" cy="220" r="3.5" fill="{LINE}"/>'
         f'<rect x="676" y="104" width="436" height="232" rx="16" fill="#000"/>'
         f'<circle cx="692" cy="121" r="3.5" fill="{LIME}" class="beat"/>'
         + d.t(702, 125, "CLAWDDESK", "m5", 10.5, TEXT, ls=2)
         + d.t(1098, 125, "21:49", "m5", 10.5, MUTED, anchor="end")
         + f'<path d="M688 136H1100M866 148V326" stroke="{LINE}" stroke-width="1"/>'
         # estado da sessão
         f'<circle cx="770" cy="200" r="40" fill="none" stroke="{LINE}" stroke-width="6"/>'
         f'<circle cx="770" cy="200" r="40" fill="none" stroke="{LIME}" stroke-width="6" stroke-linecap="round" '
         f'stroke-dasharray="251.3" class="rc ctx" transform="rotate(-90 770 200)"/>'
         + d.t(770, 207, "›_", "m5", 20, LIME, anchor="middle", cls="blink"))
    for cls, state, color, sub in (("s1", "TRABALHANDO", LIME, "editando app.js"),
                                   ("s2", "PRECISA DE VOCÊ", LIME2, "pedido de permissão"),
                                   ("s3", "CONCLUÍDO", MINT, "tarefa concluída")):
        g += (f'<g class="{cls}">' + d.t(770, 266, state, "m5", 13, color, anchor="middle", ls=1.2)
              + d.t(770, 286, sub, "b4", 12.5, MUTED, anchor="middle") + "</g>")
    # limites e sessões
    g += (d.t(882, 160, "LIMITES", "m5", 10, MUTED, ls=1.6)
          + d.t(882, 182, "SESSÃO 5H", "m5", 10.5, TEXT, ls=.6) + d.t(1098, 182, "42%", "m5", 11.5, TEXT, anchor="end")
          + f'<rect x="882" y="189" width="216" height="7" rx="3.5" fill="{LINE}"/>'
          f'<rect x="882" y="189" width="216" height="7" rx="3.5" fill="{LIME}" class="lb l5"/>'
          + d.t(882, 214, "SEMANA", "m5", 10.5, TEXT, ls=.6) + d.t(1098, 214, "23%", "m5", 11.5, TEXT, anchor="end")
          + f'<rect x="882" y="221" width="216" height="7" rx="3.5" fill="{LINE}"/>'
          f'<rect x="882" y="221" width="{216 * .23:.1f}" height="7" rx="3.5" fill="{LIME}"/>'
          + d.t(882, 250, "SESSÕES", "m5", 10, MUTED, ls=1.6))
    for row, (name, pill, color, beat) in enumerate((("loja-online", "TRABALHANDO", LIME, True),
                                                     ("api-pedidos", "PRONTO", MUTED, False))):
        yy = 272 + row * 28
        g += (f'<circle cx="886" cy="{yy - 4}" r="3.2" fill="{LIME if beat else MINT}"'
              f'{" class=" + chr(34) + "beat" + chr(34) if beat else ""}/>'
              + d.t(896, yy, name, "m5", 11, TEXT)
              + f'<rect x="1018" y="{yy - 12}" width="80" height="17" rx="8.5" fill="none" stroke="{color}" '
              f'stroke-width="1.1"/>' + d.t(1058, yy, pill, "m5", 8.5, color, anchor="middle", ls=.6))
    # pedido de permissão, aprovado pelo celular
    g += (f'<g class="perm"><rect x="876" y="236" width="228" height="94" rx="12" fill="{PANEL2}" stroke="{LIME2}" '
          f'stroke-width="1.4"/>'
          + f'<g class="q">' + d.t(890, 260, "Permitir rodar npm test?", "b4", 13.5, TEXT) + "</g>"
          + f'<g class="okk">' + d.t(890, 259, "✓ APROVADO PELO CELULAR", "m5", 11, LIME2, ls=.6) + "</g>"
          + f'<rect x="890" y="280" width="96" height="32" rx="9" fill="{LIME}" class="pbtn"/>'
          + d.t(938, 300.5, "PERMITIR", "m5", 11, BG0, anchor="middle", ls=.6)
          + f'<rect x="994" y="280" width="96" height="32" rx="9" fill="none" stroke="{LINE}" stroke-width="1.3"/>'
          + d.t(1042, 300.5, "NEGAR", "m5", 11, MUTED, anchor="middle", ls=.6)
          + f'<circle cx="938" cy="296" r="18" fill="{TEXT}" class="tap"/></g>')
    d.add(f'<g class="in" style="animation-delay:.3s">{g}</g>')
    d.save()


# ══════════════════════════════════════════════════════════════════════════
# 06 · RODAPÉ
# ══════════════════════════════════════════════════════════════════════════
def wave(y, amp, period, total=1700):
    half = period / 2
    p = f"M{-period} {y}Q{n(-period + half / 2)} {y - amp} {n(-period + half)} {y}"
    x = -period + half
    while x < total:
        x += half
        p += f"T{n(x)} {y}"
    return p + f"V400H{-period}Z"


def rodape():
    W, H = 1200, 230
    d = Doc("04-rodape", W, H, "Obrigado pela visita — Flávio R., Joinville, SC", dots=False, glow=(200, 0, 320))
    css = ""
    for i, (y, amp, period, dur, color, op) in enumerate((
        (156, 16, 300, 16, LIME, .14), (172, 12, 240, 11, MINT, .18), (190, 9, 200, 7, LIME, .30),
    )):
        css += (f".w{i}{{animation:w{i} {dur}s linear infinite}}"
                f"@keyframes w{i}{{to{{transform:translateX({period}px)}}}}")
        d.add(f'<path d="{wave(y, amp, period)}" fill="{color}" fill-opacity="{op}" class="w{i}"/>')
    d.css = css
    d.add(
        d.t(62, 92, "Obrigado pela visita.", "d8", 42, TEXT, cls="in"),
        d.t(64, 126, "JOINVILLE, SC · BRASIL", "m5", 14.5, MUTED, ls=2.5, cls="in", style="animation-delay:.2s"),
        f'<g class="in" style="animation-delay:.3s"><circle cx="1010" cy="84" r="5" fill="{LIME}" class="beat"/>'
        + d.t(1136, 89, "@flavio-r", "m5", 17, TEXT, anchor="end", ls=1) + "</g>",
    )
    d.save()


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for key in FONT_SPEC:
        FACES[key] = Face(key)
    hero()
    gestao()
    frentes()
    stack()
    projetos()
    destaque()
    clawddesk()
    rodape()
