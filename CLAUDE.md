# Site da Marina Vaucher, nutricionista

Site estático da clínica de nutrição de Marina Vaucher, nutricionista em Porto Alegre (CRN 15651).
Domínio: https://nutricionistamarina.com.br · Hospedagem: GitHub Pages, repositório `nutrimarinavaucher/sitemarinavaucher`
(o ramo `gh-pages` contém só a pasta `site/`). A cópia em sitemarinavaucher.netlify.app é antiga e não é mais atualizada.

## Como o projeto funciona

- **Edita só o que está em `src/`.** A pasta `site/` é gerada e será sobrescrita.
- Para gerar o site: `.venv/bin/python build.py`
- Para gerar e ver localmente: `.venv/bin/python build.py serve` → http://localhost:8000
- Se a pasta `.venv` não existir: `python3 -m venv .venv && .venv/bin/pip install Pillow`
- `original/index.html` é a versão antiga de página única, guardada só como referência. Não é publicada.

```
src/
  inicio.html          página inicial ({{cards}} recebe os cards do blog)
  posts.json           lista dos artigos, na ordem em que aparecem no blog
  posts/<slug>.html    conteúdo de cada artigo (capa, título, autoria, texto, rodapé)
  areas.json           páginas de áreas de atuação (texto do card, tags, seções “Para quem é / Como eu trabalho /
                       O que esperar”, artigos relacionados, SEO). Textos aprovados pela Marina em 05/11/2026.
  partes/              cabeçalho, seção de contato e rodapé, iguais em todas as páginas
  schema/              dados estruturados do negócio (MedicalBusiness) e das dúvidas (FAQPage)
  assets/site.css      todo o estilo do site
  marca/               logos originais da Marina (logo-original.png e monograma-original.png, fundo branco);
                       o build recorta, deixa o fundo transparente e gera a logo do cabeçalho, o favicon e os ícones
  img/                 fotos originais em JPG (o build gera WebP, versões de 480 px e imagens de compartilhamento)
rascunhos/             textos em revisão; nada aqui é publicado
build.py               gera site/: páginas, WebP, Open Graph, favicon, sitemap.xml, robots.txt, 404
```

Endereços: `/`, `/blog/`, `/blog/<slug>`, `/areas/<slug>`. Os links antigos (`/#artigo-...`) são redirecionados para o artigo novo por um script na página inicial (mapa em `id_antigo` de `posts.json`).

### Publicar um artigo novo

1. Coloca a foto de capa em `src/img/` (JPG, nome em minúsculas com hífens, por exemplo `nome-da-foto.jpg`).
2. Cria `src/posts/<slug>.html` copiando a estrutura de um artigo existente (link de voltar, capa, eyebrow, `<h1>`, linha de autoria, `standfirst`, `post-body`, `post-foot`).
3. Acrescenta o artigo em `src/posts.json` (a posição na lista define a ordem no blog). `data` no formato AAAA-MM-DD deve bater com o mês da linha de autoria. `descricao` vazia usa o `standfirst` como descrição para o Google.
4. Se fizer sentido, inclui o slug em `artigos` da área correspondente em `src/areas.json`.
5. Roda `.venv/bin/python build.py` e confere localmente.

### Publicar no ar

```
.venv/bin/python build.py
git add -A && git commit -m "descrição da mudança"
git push
git subtree push --prefix site origin gh-pages
```

O push usa a chave de publicação `.git/deploy_key` (deploy key do repositório). O GitHub Pages leva 1 a 2 minutos para atualizar.
O build grava `site/CNAME` (domínio) e `site/.nojekyll`.

O título, a descrição, o Open Graph, os dados estruturados Article e BreadcrumbList e a entrada no sitemap são gerados automaticamente.

## Regras de conteúdo

- **Português do Brasil, tratando o leitor por “tu”** (“o teu corpo”, “se tiveres exames”, “agenda”). Exceção: os títulos “Tentando engravidar? O que você precisa saber (e fazer)” e “Alimentação no climatério: o que você deve saber” ficam como estão, por decisão da Marina.
- **Nenhuma promessa de resultado** (Código de Ética e de Conduta do Nutricionista). Nada de “perca X kg”, “garantido”, “cura”, prazos de resultado ou antes e depois. Usar formulações como “pode ajudar”, “costuma”, “a evidência associa”. Depoimentos sempre acompanhados de “Relatos individuais... os resultados variam de caso para caso”.
- Todo artigo termina com o `post-foot`: “Este conteúdo é informativo e não substitui avaliação individual.” mais o convite para a consulta.
- Conteúdo baseado em evidência. Deixar claro quando um estudo é observacional ou quando a diretriz oficial difere da conduta da Marina.
- Dose e forma de suplemento nunca são indicadas para o leitor decidir por conta própria: “definidas na consulta”.
- **Artigos nunca usam fotos com o rosto da Marina.** As fotos dela (`hero.jpg`, `sobre.jpg`, `consulta.jpg`, `sorriso.jpg`) são só da página inicial. Isso vale para a capa, as fotos internas e as imagens de compartilhamento.
- Toda imagem com conteúdo tem `alt` descritivo em português. Imagens decorativas dos cards usam `alt=""`.
- Antes de publicar, a Marina revisa todo texto clínico novo. Rascunhos ficam em `rascunhos/`.

## Condutas clínicas da Marina (manter consistência entre os textos)

- **Folato:** recomenda **metilfolato** (forma ativa, independente da MTHFR), iniciado **cerca de 3 meses antes das tentativas** (ou o quanto antes) e mantido **durante toda a gestação e a amamentação**. Mencionar que as diretrizes oficiais pedem ao menos 30 dias antes até o fim do 1º trimestre e que os grandes estudos usaram ácido fólico. Doses maiores em casos específicos são definidas individualmente.
- **Pré-concepção:** o preparo começa cerca de 3 meses antes, para a mulher e para o homem (a espermatogênese dura cerca de 70 a 75 dias). Casais podem ser acompanhados juntos (plano Em dupla).
- **Ganho de peso na gestação:** não usa uma curva isolada. Compara mais de uma referência e acompanha o ritmo do ganho junto com exames, sintomas e bem-estar.
- **Acompanhamento:** recomenda pelo menos 3 meses. Uma consulta isolada raramente basta.
- **Medicamentos anti-obesidade (GLP-1):** são aliados da nutrição, não concorrentes. Foco em proteína, preservação de massa muscular e qualidade da alimentação.
- **Composição corporal:** olhar além do peso e do IMC (gordura, músculo, distribuição de gordura).
- A nutrição soma ao tratamento médico. Ela conversa com a equipe que acompanha a paciente.

## Identidade visual (não alterar sem pedido explícito)

- Paleta: bege (`--surface #f7f1ea`, `--peach #f1e6da`, `--sage #ebe0d3`), branco (`--bg #ffffff`) e marrom terracota `#ae6647` (`--accent`). Texto `#3b2a21`. Há modo escuro automático em `site.css`.
- Logos: a logo “marina vaucher · nutricionista” fica no cabeçalho e o monograma “mv” nos ícones (aba do navegador, iPhone, Android). A cor das logos é `#923400`; no modo escuro a logo do cabeçalho fica clara (`--logo` em `site.css`). Nunca redesenhar as logos com fontes: usar sempre os arquivos de `src/marca/`. Se chegarem versões em maior resolução ou SVG, substituir os arquivos mantendo os nomes.
- Fontes: **Lora** (títulos, itálico nos destaques `<em>`) e **Poppins** (texto, peso 300), via Google Fonts.
- Molduras de imagem em arco, círculo e cantos arredondados (`.art`). Botões em pílula (`.btn`).
- Usar sempre as classes existentes. Não introduzir frameworks, bibliotecas nem outras fontes.

## SEO

- Google Search Console: propriedade de domínio `nutricionistamarina.com.br` na conta nutrimvaucher@gmail.com, verificada por TXT no Registro.br (não remover). Sitemap enviado em 09/11/2026.

- Palavra-chave principal: “nutricionista em Porto Alegre”. Cada página tem `<title>` e descrição próprios (definidos em `build.py`, `posts.json` e `areas.json`).
- Dados estruturados: MedicalBusiness, FAQPage e WebSite (início); Blog (blog); Article e BreadcrumbList (artigos); Service e BreadcrumbList (áreas).
- Se as perguntas de “Antes de agendar” em `inicio.html` mudarem, atualizar também `src/schema/faq.json`.
- Imagens: o build gera WebP com `srcset`. As primeiras imagens da página carregam com prioridade e as outras com `loading="lazy"`.
