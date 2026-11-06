"""
Gera os cards de estatísticas do perfil (stats, linguagens, atividade e troféus)
a partir da API do GitHub, no mesmo visual do README: preto, azul e rosa.

Roda dentro do GitHub Actions (workflow "Gerar cards do perfil"), usando o
GITHUB_TOKEN do próprio workflow. Só usa a biblioteca padrão do Python.

Uso:
    python gerar_cards.py <usuario> <pasta_de_saida>
    python gerar_cards.py <usuario> <pasta_de_saida> --dados dados.json   # renderiza a partir de um JSON
"""
import json
import os
import sys
import urllib.request
from datetime import date, timedelta
from html import escape

BG, BORDA, TEXTO, SUAVE, BRANCO = "#0D1117", "#30363D", "#C9D1D9", "#8B949E", "#E6EDF3"
AZUL, AZUL_FORTE, ROSA = "#58A6FF", "#1F6FEB", "#F472B6"
SANS = "'Segoe UI',Ubuntu,'Helvetica Neue',Arial,sans-serif"
MONO = "Consolas,'SFMono-Regular',Menlo,'Courier New',monospace"
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, first: 100, isFork: false) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


# ----------------------------------------------------------------- dados
def buscar(login: str) -> dict:
    token = os.environ["GITHUB_TOKEN"]
    corpo = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=corpo,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.load(r)
    if "errors" in resp:
        raise SystemExit(f"Erro da API: {resp['errors']}")
    u = resp["data"]["user"]

    linguagens: dict[str, list] = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            nome = e["node"]["name"]
            atual = linguagens.setdefault(nome, [0, e["node"]["color"] or SUAVE])
            atual[0] += e["size"]

    cal = u["contributionsCollection"]["contributionCalendar"]
    dias = [d for w in cal["weeks"] for d in w["contributionDays"]]
    return {
        "repos": u["repositories"]["totalCount"],
        "estrelas": sum(r["stargazerCount"] for r in u["repositories"]["nodes"]),
        "seguidores": u["followers"]["totalCount"],
        "prs": u["pullRequests"]["totalCount"],
        "issues": u["issues"]["totalCount"],
        "commits_ano": u["contributionsCollection"]["totalCommitContributions"],
        "contrib_ano": cal["totalContributions"],
        "linguagens": {k: {"bytes": v[0], "cor": v[1]} for k, v in linguagens.items()},
        "dias": [{"data": d["date"], "n": d["contributionCount"]} for d in dias],
    }


# ----------------------------------------------------------------- helpers
def svg(w, h, corpo, titulo):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(titulo)}">
  <defs>
    <linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="{AZUL}"/><stop offset="1" stop-color="{ROSA}"/></linearGradient>
    <radialGradient id="glow" cx="100%" cy="0%" r="70%"><stop offset="0" stop-color="{AZUL_FORTE}" stop-opacity=".2"/><stop offset="1" stop-color="{AZUL_FORTE}" stop-opacity="0"/></radialGradient>
    <style>.s{{font-family:{SANS}}}.m{{font-family:{MONO}}}
    .in{{animation:in .8s ease-out both}}@keyframes in{{from{{opacity:0}}to{{opacity:1}}}}</style>
  </defs>
  <rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="14" fill="{BG}" stroke="{BORDA}"/>
  <rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="14" fill="url(#glow)"/>
{corpo}
</svg>
"""


def cabecalho(titulo, x=24, y=40):
    return (f'  <rect x="{x}" y="{y-17}" width="4" height="22" rx="2" fill="url(#g)"/>\n'
            f'  <text x="{x+14}" y="{y}" class="s" font-size="17" font-weight="700" fill="{BRANCO}">{escape(titulo)}</text>')


def fmt(n):
    return f"{n:,}".replace(",", ".")


# ----------------------------------------------------------------- cards
def card_stats(d):
    w, h = 460, 200
    linhas = [
        ("Repositórios públicos", d["repos"]),
        ("Commits no último ano", d["commits_ano"]),
        ("Pull requests", d["prs"]),
        ("Issues", d["issues"]),
        ("Estrelas recebidas", d["estrelas"]),
    ]
    p = [cabecalho("Números no GitHub")]
    for i, (rot, val) in enumerate(linhas):
        y = 78 + i * 24
        p.append(f'  <circle cx="30" cy="{y-5}" r="3" fill="{ROSA}"/>')
        p.append(f'  <text x="44" y="{y}" class="s" font-size="14" fill="{TEXTO}">{rot}</text>')
        p.append(f'  <text x="290" y="{y}" text-anchor="end" class="m" font-size="14" font-weight="700" fill="{AZUL}">{fmt(val)}</text>')
    # anel com contribuições do ano
    cx, cy, r = 380, 110, 46
    p.append(f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{BORDA}" stroke-width="6"/>')
    p.append(f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#g)" stroke-width="6" stroke-linecap="round" '
             f'transform="rotate(-90 {cx} {cy})" class="in"/>')
    p.append(f'  <text x="{cx}" y="{cy+4}" text-anchor="middle" class="m" font-size="22" font-weight="700" fill="{BRANCO}">{fmt(d["contrib_ano"])}</text>')
    p.append(f'  <text x="{cx}" y="{cy+24}" text-anchor="middle" class="s" font-size="11" fill="{SUAVE}">contribuições</text>')
    p.append(f'  <text x="{cx}" y="{cy+70}" text-anchor="middle" class="s" font-size="11" fill="{SUAVE}">no último ano</text>')
    return svg(w, h, "\n".join(p), "Números no GitHub")


def card_linguagens(d):
    w, h = 340, 200
    total = sum(v["bytes"] for v in d["linguagens"].values()) or 1
    top = sorted(d["linguagens"].items(), key=lambda kv: -kv[1]["bytes"])[:6]
    p = [cabecalho("Linguagens mais usadas")]
    # barra segmentada
    x, largura = 24, w - 48
    p.append(f'  <clipPath id="barra"><rect x="24" y="58" width="{largura}" height="10" rx="5"/></clipPath>')
    p.append('  <g clip-path="url(#barra)">')
    if not top:
        p.append(f'    <rect x="24" y="58" width="{largura}" height="10" fill="{BORDA}"/>')
    for nome, v in top:
        seg = largura * v["bytes"] / total
        p.append(f'    <rect x="{x:.1f}" y="58" width="{seg:.1f}" height="10" fill="{v["cor"]}"/>')
        x += seg
    p.append('  </g>')
    for i, (nome, v) in enumerate(top):
        col, lin = i % 2, i // 2
        lx, ly = 24 + col * 150, 100 + lin * 30
        pct = 100 * v["bytes"] / total
        p.append(f'  <circle cx="{lx+5}" cy="{ly-4}" r="5" fill="{v["cor"]}"/>')
        p.append(f'  <text x="{lx+16}" y="{ly}" class="s" font-size="13" fill="{TEXTO}">{escape(nome)}</text>')
        p.append(f'  <text x="{lx+138}" y="{ly}" text-anchor="end" class="m" font-size="12" fill="{SUAVE}">{pct:.1f}%</text>')
    if not top:
        p.append(f'  <text x="24" y="104" class="s" font-size="13" fill="{SUAVE}">Nenhuma linguagem detectada ainda.</text>')
    return svg(w, h, "\n".join(p), "Linguagens mais usadas")


def card_atividade(d, n_dias=31):
    w, h = 820, 300
    dias = d["dias"][-n_dias:]
    if not dias:
        hoje = date.today()
        dias = [{"data": (hoje - timedelta(days=n_dias - 1 - i)).isoformat(), "n": 0} for i in range(n_dias)]
    valores = [x["n"] for x in dias]
    topo = max(4, -(-max(valores) // 4) * 4)  # múltiplo de 4: eixo só com inteiros
    x0, x1, y0, y1 = 64, w - 32, 250, 74
    passo = (x1 - x0) / (len(dias) - 1)
    pts = [(x0 + i * passo, y0 - (v / topo) * (y0 - y1)) for i, v in enumerate(valores)]

    p = [cabecalho("Contribuições nos últimos 31 dias")]
    total = sum(valores)
    p.append(f'  <text x="{w-32}" y="40" text-anchor="end" class="m" font-size="13" fill="{ROSA}">{total} no período</text>')
    # grade
    for k in range(5):
        gy = y0 - k * (y0 - y1) / 4
        val = topo * k / 4
        p.append(f'  <line x1="{x0}" x2="{x1}" y1="{gy:.1f}" y2="{gy:.1f}" stroke="{BORDA}" stroke-dasharray="3 5"/>')
        p.append(f'  <text x="{x0-12}" y="{gy+4:.1f}" text-anchor="end" class="m" font-size="11" fill="{SUAVE}">{int(val)}</text>')
    # área + linha
    linha = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    p.append('  <defs><linearGradient id="area" x1="0" x2="0" y1="0" y2="1">'
             f'<stop offset="0" stop-color="{AZUL_FORTE}" stop-opacity=".45"/><stop offset="1" stop-color="{AZUL_FORTE}" stop-opacity="0"/></linearGradient></defs>')
    p.append(f'  <polygon points="{x0},{y0} {linha} {x1},{y0}" fill="url(#area)" class="in"/>')
    p.append(f'  <polyline points="{linha}" fill="none" stroke="{AZUL}" stroke-width="2.5" stroke-linejoin="round" class="in"/>')
    for (x, y), v in zip(pts, valores):
        p.append(f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="{3.5 if v else 2.5}" fill="{ROSA if v else BORDA}"/>')
    # rótulos de data (a cada 5 dias)
    for i, dia in enumerate(dias):
        if i % 5 == 0 or i == len(dias) - 1:
            dt = date.fromisoformat(dia["data"])
            ancora = "end" if i == len(dias) - 1 else "middle"
            p.append(f'  <text x="{x0 + i*passo + (6 if ancora == "end" else 0):.1f}" y="{y0+24}" text-anchor="{ancora}" class="m" font-size="11" fill="{SUAVE}">{dt.day:02d} {MESES[dt.month-1]}</text>')
    return svg(w, h, "\n".join(p), "Contribuições nos últimos 31 dias")


NIVEIS = ["C", "B", "A", "S"]
TROFEUS = [
    ("Repositórios", "repos", [1, 5, 10, 20]),
    ("Commits", "commits_ano", [1, 50, 150, 300]),
    ("Contribuições", "contrib_ano", [1, 100, 250, 500]),
    ("Linguagens", "n_linguagens", [1, 3, 5, 8]),
    ("Estrelas", "estrelas", [1, 10, 30, 100]),
    ("Seguidores", "seguidores", [1, 10, 30, 100]),
]


def card_trofeus(d):
    d = dict(d, n_linguagens=len(d["linguagens"]))
    cw, ch, gap, colunas = 132, 132, 12, 3
    linhas = -(-len(TROFEUS) // colunas)
    w = colunas * cw + (colunas - 1) * gap
    h = linhas * ch + (linhas - 1) * gap
    p = []
    for i, (nome, chave, limites) in enumerate(TROFEUS):
        val = d[chave]
        nivel = sum(val >= l for l in limites)  # 0..4
        ativo = nivel > 0
        x = (i % colunas) * (cw + gap)
        y = (i // colunas) * (ch + gap)
        cor = ROSA if nivel == 4 else AZUL if ativo else BORDA
        p.append(f'  <g transform="translate({x} {y})">')
        p.append(f'    <rect x=".5" y=".5" width="{cw-1}" height="{ch-1}" rx="12" fill="{BG}" stroke="{BORDA}"/>')
        # taça
        op = "1" if ativo else ".35"
        p.append(f'    <g transform="translate({cw/2-16} 18)" opacity="{op}">'
                 f'<path d="M6 0h20v10a10 10 0 0 1-20 0z" fill="{cor}"/>'
                 f'<path d="M6 3H1v4a6 6 0 0 0 6 6M26 3h5v4a6 6 0 0 1-6 6" fill="none" stroke="{cor}" stroke-width="2"/>'
                 f'<rect x="13" y="20" width="6" height="6" fill="{cor}"/><rect x="8" y="26" width="16" height="4" rx="1" fill="{cor}"/></g>')
        rot = NIVEIS[nivel - 1] if ativo else "—"
        p.append(f'    <text x="{cw/2}" y="74" text-anchor="middle" class="m" font-size="16" font-weight="700" fill="{cor if ativo else SUAVE}">{rot}</text>')
        p.append(f'    <text x="{cw/2}" y="96" text-anchor="middle" class="s" font-size="12.5" fill="{TEXTO}">{nome}</text>')
        p.append(f'    <text x="{cw/2}" y="116" text-anchor="middle" class="m" font-size="11.5" fill="{SUAVE}">{fmt(val)}</text>')
        p.append('  </g>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Troféus do GitHub">
  <style>.s{{font-family:{SANS}}}.m{{font-family:{MONO}}}</style>
{chr(10).join(p)}
</svg>
"""


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    login, saida = sys.argv[1], sys.argv[2]
    if "--dados" in sys.argv:
        with open(sys.argv[sys.argv.index("--dados") + 1], encoding="utf-8") as f:
            d = json.load(f)
    else:
        d = buscar(login)
    os.makedirs(saida, exist_ok=True)
    for nome, conteudo in [
        ("stats.svg", card_stats(d)),
        ("top-langs.svg", card_linguagens(d)),
        ("activity.svg", card_atividade(d)),
        ("trophies.svg", card_trofeus(d)),
    ]:
        with open(os.path.join(saida, nome), "w", encoding="utf-8") as f:
            f.write(conteudo)
        print("gerado:", nome)


if __name__ == "__main__":
    main()
