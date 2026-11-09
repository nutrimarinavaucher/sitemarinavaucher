#!/usr/bin/env python3
"""Gera o site estático em site/ a partir de src/.

Uso:
  .venv/bin/python build.py          gera o site
  .venv/bin/python build.py serve    gera e abre um servidor local em http://localhost:8000
"""
import datetime
import hashlib
import html
import json
import re
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageFilter

SITE = "https://nutricionistamarina.com.br"
NOME = "Marina Vaucher Nutricionista"
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
OUT = ROOT / "site"
HOJE = datetime.date.today().isoformat()
WEBP_QUALIDADE = 80
LARGURA_PEQUENA = 480
OG_LARGURA_MAX = 1200

MESES = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def ler(p):
    return (SRC / p).read_text(encoding="utf-8")


def gravar(rel, texto):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texto, encoding="utf-8")


def esc(s):
    return html.escape(s, quote=True)


def sem_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def jsonld(obj):
    return '<script type="application/ld+json">%s</script>' % json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------- imagens

TAMANHOS = {}  # nome -> (largura, altura)


def otimizar_imagens():
    """Cada src/img/x.jpg vira site/img/x.webp (largura original) e x-480.webp."""
    destino = OUT / "img"
    destino.mkdir(parents=True, exist_ok=True)
    for jpg in sorted((SRC / "img").glob("*.jpg")):
        with Image.open(jpg) as im:
            im = im.convert("RGB")
            TAMANHOS[jpg.stem] = im.size
            alvos = [(destino / (jpg.stem + ".webp"), im.width)]
            if im.width > LARGURA_PEQUENA:
                alvos.append((destino / ("%s-%d.webp" % (jpg.stem, LARGURA_PEQUENA)), LARGURA_PEQUENA))
            for alvo, largura in alvos:
                if alvo.exists() and alvo.stat().st_mtime >= jpg.stat().st_mtime:
                    continue
                img = im if largura == im.width else im.resize((largura, round(im.height * largura / im.width)), Image.LANCZOS)
                img.save(alvo, "WEBP", quality=WEBP_QUALIDADE, method=6)


def posicao_y(pos):
    """'50% 32%' -> 0.32"""
    partes = pos.split()
    return float(partes[1].rstrip("%")) / 100 if len(partes) > 1 else 0.5


def imagem_og(nome_saida, foto, pos):
    """Recorte 1,91:1 (padrão do WhatsApp/Facebook) sem ampliar a foto."""
    alvo = OUT / "img" / "og" / (nome_saida + ".jpg")
    alvo.parent.mkdir(parents=True, exist_ok=True)
    origem = SRC / "img" / foto
    with Image.open(origem) as im:
        im = im.convert("RGB")
        w = min(im.width, OG_LARGURA_MAX)
        escala = w / im.width
        im = im.resize((w, round(im.height * escala)), Image.LANCZOS) if escala != 1 else im
        h = round(w / 1.91)
        topo = round((im.height - h) * posicao_y(pos))
        im.crop((0, topo, w, topo + h)).save(alvo, "JPEG", quality=84, optimize=True, progressive=True)
        return "%s/img/og/%s.jpg" % (SITE, nome_saida), w, h


def tamanhos_para(classe):
    if "post-card" in classe or classe == "art":
        return "(max-width: 520px) 100vw, (max-width: 980px) 50vw, 280px"
    if "thumb" in classe:
        return "(max-width: 600px) 100vw, (max-width: 1100px) 50vw, 280px"
    if "post-cover" in classe or "inline-photo" in classe:
        return "(max-width: 760px) 100vw, 720px"
    if "round" in classe:
        return "200px"
    return "(max-width: 900px) 100vw, 480px"


def trocar_imagens(doc, prioritarias):
    """Troca <img src="/img/x.jpg"> por WebP com srcset e carregamento tardio.

    prioritarias: quantas imagens do início da página carregam imediatamente
    (a primeira delas com fetchpriority="high")."""
    contador = [0]

    def troca(m):
        nome, resto = m.group(1), m.group(2)
        antes = doc[max(0, m.start() - 120):m.start()]
        classe = re.findall(r'class="([^"]*)"', antes)
        classe = classe[-1] if classe else ""
        w, _ = TAMANHOS[nome]
        srcset = "/img/%s.webp %dw" % (nome, w)
        if w > LARGURA_PEQUENA:
            srcset = "/img/%s-%d.webp %dw, " % (nome, LARGURA_PEQUENA, LARGURA_PEQUENA) + srcset
        i = contador[0]
        contador[0] += 1
        if i < prioritarias:
            carga = ' fetchpriority="high"' if i == 0 else ""
        else:
            carga = ' loading="lazy" decoding="async"'
        return '<img src="/img/%s.webp" srcset="%s" sizes="%s"%s%s>' % (nome, srcset, tamanhos_para(classe), resto, carga)

    return re.sub(r'<img src="/img/([a-z0-9-]+)\.jpg"([^>]*)>', troca, doc)


COR_MARCA = (0x92, 0x34, 0x00)  # marrom das logos da Marina (#923400)


def recortar_marca(arquivo):
    """Logo original (fundo branco) -> recorte justo com fundo transparente na cor da marca."""
    with Image.open(SRC / "marca" / arquivo) as im:
        azul = im.convert("RGB").getchannel("B")
    # Sobre fundo branco, o canal azul vai de 255 (fundo) a 0 (traço #923400): vira a transparência.
    alfa = azul.point(lambda v: 255 - v)
    x0, y0, x1, y1 = alfa.point(lambda v: 255 if v > 8 else 0).getbbox()
    folga = 3
    alfa = alfa.crop((x0 - folga, y0 - folga, x1 + folga, y1 + folga))
    out = Image.new("RGBA", alfa.size, COR_MARCA + (0,))
    out.putalpha(alfa)
    return out


def icones():
    """Logo do cabeçalho e ícones (favicon, iPhone, Android) a partir das logos da Marina em src/marca/."""
    destino = OUT / "img" / "marca"
    destino.mkdir(parents=True, exist_ok=True)
    logo = recortar_marca("logo-original.png")
    logo.save(destino / "logo.png", optimize=True)
    mono = recortar_marca("monograma-original.png")
    mono.save(destino / "monograma.png", optimize=True)

    # Na aba do navegador (16 a 64 px) os traços finos somem: só ali o monograma ganha traço mais grosso.
    mono_aba = mono.copy()
    mono_aba.putalpha(mono.getchannel("A").filter(ImageFilter.MaxFilter(9)))

    def icone(tam, ocupacao, m=mono):
        fundo = Image.new("RGBA", (tam, tam), (255, 255, 255, 255))
        largura = round(tam * ocupacao)
        m = m.resize((largura, round(m.height * largura / m.width)), Image.LANCZOS)
        fundo.alpha_composite(m, ((tam - m.width) // 2, (tam - m.height) // 2))
        return fundo

    icone(256, 0.9, mono_aba).save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    icone(64, 0.9, mono_aba).save(OUT / "favicon-64.png")
    icone(180, 0.62).convert("RGB").save(OUT / "apple-touch-icon.png")
    icone(192, 0.62).convert("RGB").save(OUT / "icon-192.png")
    icone(512, 0.62).convert("RGB").save(OUT / "icon-512.png")
    gravar("site.webmanifest", json.dumps({
        "name": NOME, "short_name": "Marina Vaucher", "lang": "pt-BR", "start_url": "/",
        "display": "browser", "background_color": "#ffffff", "theme_color": "#ffffff",
        "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}],
    }, ensure_ascii=False, indent=2) + "\n")


# ---------------------------------------------------------------- páginas

def pagina(caminho, titulo, descricao, conteudo, og, ld=(), tipo="website", extra_head="",
           prioritarias=1, indexar=True, artigo=None):
    url = SITE + caminho
    og_url, og_w, og_h, og_alt = og
    head = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
        "<title>%s</title>" % esc(titulo),
        '<meta name="description" content="%s">' % esc(descricao),
    ]
    if indexar:
        head.append('<link rel="canonical" href="%s">' % url)
    else:
        head.append('<meta name="robots" content="noindex">')
    head += [
        '<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">',
        '<meta name="theme-color" content="#1a1512" media="(prefers-color-scheme: dark)">',
        '<link rel="icon" href="/favicon.ico" sizes="any">',
        '<link rel="icon" href="/favicon-64.png" type="image/png" sizes="64x64">',
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
        '<link rel="manifest" href="/site.webmanifest">',
        '<meta property="og:locale" content="pt_BR">',
        '<meta property="og:site_name" content="%s">' % NOME,
        '<meta property="og:type" content="%s">' % tipo,
        '<meta property="og:title" content="%s">' % esc(titulo.split(" | ")[0]),
        '<meta property="og:description" content="%s">' % esc(descricao),
        '<meta property="og:url" content="%s">' % url,
        '<meta property="og:image" content="%s">' % og_url,
        '<meta property="og:image:type" content="image/jpeg">',
        '<meta property="og:image:width" content="%d">' % og_w,
        '<meta property="og:image:height" content="%d">' % og_h,
        '<meta property="og:image:alt" content="%s">' % esc(og_alt),
        '<meta name="twitter:card" content="summary_large_image">',
    ]
    if artigo:
        head += ['<meta property="article:published_time" content="%s">' % artigo["data"],
                 '<meta property="article:author" content="Marina Vaucher">',
                 '<meta property="article:section" content="%s">' % esc(artigo["categoria"])]
    head += [
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;1,400;1,500&family=Poppins:wght@300;400;500&display=swap">',
        '<link rel="stylesheet" href="%s">' % CSS_URL,
    ]
    head += [jsonld(x) for x in ld]
    if extra_head:
        head.append(extra_head)
    corpo = trocar_imagens(conteudo, prioritarias)
    doc = ("<!doctype html>\n<html lang=\"pt-BR\">\n<head>\n%s\n</head>\n<body>\n\n%s\n<main id=\"inicio\">\n%s\n\n%s</main>\n\n%s\n\n</body>\n</html>\n"
           % ("\n".join(head), CABECALHO, corpo, CONTATO, RODAPE))
    arquivo = "index.html" if caminho == "/" else caminho.strip("/") + ("/index.html" if caminho.endswith("/") else ".html")
    gravar(arquivo, doc)
    if indexar:
        MAPA.append((url, artigo["data"] if artigo else HOJE))


def migalhas(*itens):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": nome, "item": SITE + caminho}
        for i, (nome, caminho) in enumerate(itens)]}


def card(p):
    return ('        <a class="post-card" href="/blog/%s"><div class="art"><img src="/img/%s" alt="" style="object-position:%s"></div>'
            '<span class="meta">%s</span><h3>%s</h3><span class="more">Ler artigo &rarr;</span></a>'
            % (p["slug"], p["imagem_card"], p["posicao_card"], p["categoria"], p["titulo"]))


def carregar_posts():
    posts = json.loads(ler("posts.json"))
    for p in posts:
        corpo = ler("posts/%s.html" % p["slug"])
        p["corpo"] = corpo
        p["titulo"] = re.search(r"<h1>(.*?)</h1>", corpo).group(1)
        p["resumo"] = sem_tags(re.search(r'class="standfirst">(.*?)</p>', corpo, re.S).group(1))
        capa = re.search(r'<div class="art post-cover"><img src="/img/([^"]+)" alt="([^"]*)" style="object-position:([^"]+)"', corpo)
        p["capa"], p["capa_alt"], p["capa_pos"] = capa.groups()
        ano, mes = int(p["data"][:4]), int(p["data"][5:7])
        esperado = "%s de %d" % (MESES[mes], ano)
        if esperado.lower() not in corpo.lower():
            print("AVISO: a data de %s (%s) não bate com a linha de autoria do artigo" % (p["slug"], p["data"]))
    return posts


def construir():
    global CABECALHO, CONTATO, RODAPE, CSS_URL, MAPA
    for item in OUT.glob("*") if OUT.exists() else []:
        if item.name != "img":
            shutil.rmtree(item) if item.is_dir() else item.unlink()
    OUT.mkdir(exist_ok=True)
    MAPA = []

    css = ler("assets/site.css")
    nome_css = "site.%s.css" % hashlib.sha1(css.encode()).hexdigest()[:8]
    gravar("assets/" + nome_css, css)
    CSS_URL = "/assets/" + nome_css
    CABECALHO = ler("partes/cabecalho.html").strip()
    CONTATO = ler("partes/contato.html")
    RODAPE = ler("partes/rodape.html").strip()

    otimizar_imagens()
    icones()
    posts = carregar_posts()
    por_slug = {p["slug"]: p for p in posts}
    areas = json.loads(ler("areas.json"))
    cards = "\n".join(card(p) for p in posts)
    negocio = json.loads(ler("schema/negocio.json"))
    faq = json.loads(ler("schema/faq.json"))
    ref_negocio = {"@type": "MedicalBusiness", "@id": SITE + "/#negocio", "name": NOME,
                   "logo": {"@type": "ImageObject", "url": SITE + "/icon-512.png"}}
    autora = {"@type": "Person", "@id": SITE + "/#marina", "name": "Marina Vaucher",
              "jobTitle": "Nutricionista", "url": SITE + "/"}

    # Início
    inicio = ler("inicio.html").replace("{{cards}}", cards)
    og_inicio = imagem_og("inicio", "hero.jpg", "50% 32%") + ("Marina Vaucher, nutricionista em Porto Alegre",)
    antigos = {p["id_antigo"]: p["slug"] for p in posts}
    redireciona = ("<script>(function(){var m=%s,h=location.hash.slice(1);if(m[h])location.replace('/blog/'+m[h]);})();</script>"
                   % json.dumps(antigos, separators=(",", ":")))
    site_ld = {"@context": "https://schema.org", "@type": "WebSite", "@id": SITE + "/#site", "name": NOME,
               "url": SITE + "/", "inLanguage": "pt-BR", "publisher": {"@id": SITE + "/#negocio"}}
    pagina("/", "Nutricionista em Porto Alegre | Marina Vaucher · CRN 15651",
           "Marina Vaucher, nutricionista em Porto Alegre (CRN 15651). Fertilidade feminina e masculina, FIV, gestação, emagrecimento e composição corporal. Atendimento presencial e online.",
           inicio, og_inicio, ld=[negocio, faq, site_ld], extra_head=redireciona, prioritarias=2)

    # Blog
    secao_blog = re.search(r'  <section id="blog".*?</section>', inicio, re.S).group(0)
    secao_blog = re.sub(r'<h2 id="blog-title">(.*?)</h2>', r'<h1 id="blog-title">\1</h1>', secao_blog)
    og_blog = imagem_og("blog", "frutas.jpg", "50% 45%") + ("Tigela com morangos, melão e banana",)
    blog_ld = {"@context": "https://schema.org", "@type": "Blog", "name": "Blog " + NOME, "url": SITE + "/blog/",
               "inLanguage": "pt-BR", "publisher": {"@id": SITE + "/#negocio"},
               "blogPost": [{"@type": "Article", "headline": sem_tags(p["titulo"]), "url": "%s/blog/%s" % (SITE, p["slug"]),
                             "datePublished": p["data"]} for p in posts]}
    pagina("/blog/", "Blog de nutrição | Marina Vaucher, nutricionista em Porto Alegre",
           "Textos baseados em evidência sobre fertilidade, gestação, saúde hormonal e metabolismo, por Marina Vaucher, nutricionista em Porto Alegre (CRN 15651).",
           secao_blog, og_blog, ld=[blog_ld, migalhas(("Início", "/"), ("Blog", "/blog/"))], prioritarias=4)

    # Artigos
    for p in posts:
        titulo = sem_tags(p["titulo"])
        descricao = p.get("descricao") or p["resumo"]
        caminho = "/blog/" + p["slug"]
        og = imagem_og(p["slug"], p["capa"], p["capa_pos"]) + (p["capa_alt"],)
        artigo_ld = {"@context": "https://schema.org", "@type": "Article", "headline": titulo, "description": descricao,
                     "image": [og[0], "%s/img/%s" % (SITE, p["capa"].replace(".jpg", ".webp"))],
                     "datePublished": p["data"], "dateModified": p.get("atualizado") or p["data"],
                     "inLanguage": "pt-BR", "articleSection": p["categoria"], "author": autora,
                     "publisher": ref_negocio, "mainEntityOfPage": SITE + caminho}
        pagina(caminho, "%s | Marina Vaucher" % titulo, descricao,
               '<article class="post">\n%s\n</article>\n' % p["corpo"].rstrip(), og,
               ld=[artigo_ld, migalhas(("Início", "/"), ("Blog", "/blog/"), (titulo, caminho))],
               tipo="article", artigo=p)

    # Áreas de atuação
    zap = re.search(r'href="(https://wa\.me/[^"]+)"', inicio).group(1)
    for a in areas:
        caminho = "/areas/" + a["slug"]
        relacionados = "\n".join(card(por_slug[s]) for s in a["artigos"])
        # Seções de texto da área (opcionais): lista de {"titulo", "texto"} em areas.json
        corpo_area = ""
        if a.get("secoes"):
            corpo_area = '\n    <div class="post-body">\n%s\n    </div>' % "\n".join(
                "      <h2>%s</h2>\n      <p>%s</p>" % (esc(s["titulo"]), esc(s["texto"])) for s in a["secoes"])
        conteudo = """<article class="post">
  <div class="wrap"><div class="post-inner">
    <a class="back" href="/#atuacao">&larr; Voltar para as áreas de atuação</a>
    <div class="art post-cover"><img src="/img/{imagem}" alt="{alt}" style="object-position:{posicao}"></div>
    <p class="eyebrow">Áreas de atuação</p>
    <h1>{titulo}</h1>
    <p class="standfirst">{texto}</p>
    <p class="tags">{tags}</p>{corpo_area}
  </div></div>
</article>

  <section class="band alt related" aria-labelledby="relacionados-title">
    <div class="wrap">
      <div class="band-head">
        <p class="eyebrow">Blog</p>
        <h2 id="relacionados-title">Leituras <em>relacionadas</em></h2>
      </div>
      <div class="posts">
{cards}
      </div>
      <div class="section-cta">
        <p>Na primeira consulta, a gente define juntos o melhor caminho.</p>
        <a class="btn" href="{zap}" target="_blank" rel="noopener">Agendar consulta <span class="arrow" aria-hidden="true">&rarr;</span></a>
      </div>
    </div>
  </section>
""".format(cards=relacionados, zap=zap, corpo_area=corpo_area, **a)
        og = imagem_og("area-" + a["slug"], a["imagem"], a["posicao"]) + (a["alt"],)
        servico = {"@context": "https://schema.org", "@type": "Service", "name": sem_tags(a["titulo"]),
                   "description": a["texto"], "url": SITE + caminho, "provider": {"@id": SITE + "/#negocio"},
                   "areaServed": [{"@type": "City", "name": "Porto Alegre"}, {"@type": "Country", "name": "Brasil"}]}
        pagina(caminho, a["titulo_seo"], a["descricao"], conteudo, og,
               ld=[servico, migalhas(("Início", "/"), (sem_tags(a["titulo"]), caminho))])

    # 404
    nao_encontrada = """  <section class="band notfound" aria-labelledby="erro-title">
    <div class="wrap">
      <div class="band-head center">
        <p class="eyebrow">Erro 404</p>
        <h1 id="erro-title">Página não <em>encontrada</em></h1>
        <p class="lead">O endereço que procuraste não existe ou mudou de lugar. Os artigos do blog agora têm endereços próprios.</p>
        <div class="hero-actions"><a class="btn" href="/">Ir para o início</a><a class="btn ghost" href="/blog/">Ver o blog</a></div>
      </div>
    </div>
  </section>
"""
    # Pré-consulta: formulários para novos pacientes (fora do menu, mas pode aparecer no Google)
    pre_consulta = """  <section class="band" aria-labelledby="pre-title">
    <div class="wrap">
      <div class="band-head center">
        <p class="eyebrow">Novos pacientes</p>
        <h1 id="pre-title">Formulário de <em>pré-consulta</em></h1>
        <p class="lead">Antes da primeira consulta, preenche o formulário que combina contigo. Com as tuas respostas, eu chego à consulta já conhecendo a tua história, e o nosso tempo juntos rende mais.</p>
      </div>
      <div class="notes3 notes2">
        <div><h3>Gestantes</h3><p>Se estás grávida, este é o teu formulário.</p><a class="btn" href="https://bit.ly/consultagestante" target="_blank" rel="noopener">Preencher formulário de gestante</a></div>
        <div><h3>Primeira consulta</h3><p>Para todos os outros objetivos, inclusive tentantes e casais.</p><a class="btn" href="https://bit.ly/primeiraconsultaMV" target="_blank" rel="noopener">Preencher formulário de primeira consulta</a></div>
      </div>
    </div>
  </section>
"""
    pagina("/preconsulta", "Pré-consulta | " + NOME,
           "Formulários de pré-consulta para novos pacientes da nutricionista Marina Vaucher, em Porto Alegre e online.",
           pre_consulta, og_inicio)

    # Consulta online: página oculta (sem link no site, fora do sitemap, noindex) que leva ao Google Meet
    MEET = "https://meet.google.com/obu-qgec-cki"
    consulta_online = """  <section class="band notfound" aria-labelledby="online-title">
    <div class="wrap">
      <div class="band-head center">
        <p class="eyebrow">Consulta online</p>
        <h1 id="online-title">Abrindo a <em>sala da consulta</em>…</h1>
        <p class="lead">Se o Google Meet não abrir sozinho em alguns segundos, clica no botão abaixo.</p>
        <div class="hero-actions"><a class="btn" href="%s">Entrar na consulta</a></div>
      </div>
    </div>
  </section>
""" % MEET
    pagina("/consultaonline", "Consulta online | " + NOME, "Sala da consulta online.",
           consulta_online, og_inicio, indexar=False,
           extra_head='<meta name="referrer" content="no-referrer">\n<meta http-equiv="refresh" content="0; url=%s">\n'
                      '<script>location.replace("%s")</script>' % (MEET, MEET))

    pagina("/404", "Página não encontrada | " + NOME, "Esta página não existe ou mudou de endereço.",
           nao_encontrada, og_inicio, indexar=False)

    # sitemap.xml e robots.txt
    linhas = "\n".join("  <url><loc>%s</loc><lastmod>%s</lastmod></url>" % u for u in MAPA)
    gravar("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s\n</urlset>\n' % linhas)
    gravar("robots.txt", "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % SITE)
    # Cabeçalhos de cache do Netlify (vale também para publicação por upload manual)
    gravar("_headers", "/assets/*\n  Cache-Control: public, max-age=31536000, immutable\n\n/img/*\n  Cache-Control: public, max-age=604800\n")
    # GitHub Pages: domínio próprio e publicação dos arquivos como estão
    gravar("CNAME", "nutricionistamarina.com.br\n")
    gravar(".nojekyll", "")
    print("Site gerado em site/: %d páginas no sitemap." % len(MAPA))


def servir(porta=8000):
    """Servidor local que imita o Netlify: /blog/x serve blog/x.html e erros mostram 404.html."""
    import functools
    import http.server

    class Handler(http.server.SimpleHTTPRequestHandler):
        def send_head(self):
            caminho = self.path.split("?")[0].split("#")[0]
            alvo = OUT / caminho.lstrip("/")
            if not caminho.endswith("/") and not alvo.exists() and alvo.with_suffix(".html").exists():
                self.path = caminho + ".html"
            return super().send_head()

        def send_error(self, code, message=None, explain=None):
            if code == 404:
                corpo = (OUT / "404.html").read_bytes()
                self.send_response(404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)
            else:
                super().send_error(code, message, explain)

    handler = functools.partial(Handler, directory=str(OUT))
    print("Servindo em http://localhost:%d (Ctrl+C para parar)" % porta)
    http.server.ThreadingHTTPServer(("127.0.0.1", porta), handler).serve_forever()


if __name__ == "__main__":
    construir()
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        servir()
