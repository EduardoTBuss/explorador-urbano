# 🗺️ Explorador Urbano

> **Aplicação web de rastreamento de percursos urbanos em tempo real, com ranking multiusuário e atualização via WebSocket.**

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-black?logo=flask)](https://flask.palletsprojects.com)
[![SQLite](https://img.shields.io/badge/SQLite-WAL_mode-003B57?logo=sqlite)](https://sqlite.org)
[![Leaflet](https://img.shields.io/badge/Leaflet.js-1.9.4-199900?logo=leaflet)](https://leafletjs.com)
[![Socket.IO](https://img.shields.io/badge/Socket.IO-realtime-010101?logo=socket.io)](https://socket.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 🇬🇧 English version: [`README.md`](README.md)

---

## 📌 Contexto Acadêmico

Projeto desenvolvido para a disciplina optativa **"Uso de Inteligência Artificial no Desenvolvimento de Software"** do curso de **Engenharia de Computação — UFPel (2026)**.

O objetivo da disciplina era aprender a utilizar ferramentas de IA generativa (vibecoding) de forma estruturada e consciente: não apenas como gerador de código, mas como acelerador técnico onde as decisões de arquitetura, requisitos e revisão crítica partiram integralmente do aluno.

**Modelo utilizado:** Claude (Anthropic) via claude.ai
**Metodologia:** documentada em [`relatorio_explorador.pdf`](relatorio_explorador.pdf)

---

## 📸 Preview

<!-- TODO: substituir pelo screenshot real do mapa + ranking em docs/demo.png -->
![demo](docs/demo.png)

> *GPS ao vivo no celular → trilha desenhada em tempo real → ranking atualizado instantaneamente*

---

## ✨ Funcionalidades

### 📍 Rastreamento GPS
- Captura de posição via `navigator.geolocation.watchPosition` no browser do celular
- Modo simulação por clique no mapa (para testes no desktop)
- Fallback automático GPS → simulação em caso de erro
- Trilha atual desenhada em tempo real (polilinha vermelha)
- Trilhas históricas de sessões anteriores em cores distintas (até 30 sessões)

### 👤 Usuários
- Cadastro por nome e apelido (sistema simples, sem senha — foco em demo)
- Login por apelido
- Sessão salva em `localStorage` para não logar novamente

### 📊 Estatísticas por Sessão
- Distância percorrida (m / km)
- Duração (hh:mm:ss)
- Pace (min/km)
- Velocidade média e atual (km/h)
- Calorias estimadas (~60 kcal/km)
- Status de movimento: `andando` · `devagar` · `parado`

### 🏆 Ranking
- Ranking diário por distância total com medalhas para o top 3
- Calculado por query SQL agregada — sem loop sobre todos os pontos

### 📡 Tempo Real (WebSocket)
- Atualização ao vivo via Socket.IO: posições, sessões iniciadas/encerradas
- Lista de usuários ativos nos últimos 5 minutos com status e velocidade
- Feed de eventos na aba "Ao Vivo"

---

## 🛠️ Stack Técnica

| Camada    | Tecnologia                            |
|-----------|---------------------------------------|
| Backend   | Python 3.10+ · Flask                  |
| WebSocket | Flask-SocketIO (async mode `threading`)|
| Banco     | SQLite3 (stdlib) · WAL mode           |
| Frontend  | HTML5 · CSS3 · JavaScript ES6+ (arquivo único) |
| Mapa      | Leaflet.js 1.9.4 · OpenStreetMap (via CDN) |
| Gráfico   | Chart.js (via CDN)                    |
| GPS       | Web Geolocation API                   |
| SSL       | `cryptography` (geração programática) com fallback para `openssl` |

**Sem dependências externas de serviço:** sem banco externo, sem cloud, sem ORM.

---

## 🚀 Como Rodar

O código-fonte vive em `src/`. Todos os comandos abaixo partem da raiz do repositório.

### 1. Clonar e instalar dependências

```bash
git clone https://github.com/EduardoTBuss/explorador-urbano
cd explorador-urbano
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# Linux/macOS:          source .venv/bin/activate
pip install -r src/requirements.txt
```

> ⚠️ A geração programática do certificado SSL usa o pacote `cryptography`, que **não está**
> listado em `requirements.txt`. Se ele não estiver instalado, a aplicação cai no fallback
> via `openssl` na linha de comando. Para garantir o caminho programático:
> `pip install cryptography`.

### 2. Rodar o servidor

```bash
cd src
python main.py
```

Saída esperada:

```
====================================================
  Explorador Urbano — HTTPS
====================================================
  Notebook : https://localhost:8443
  Celular  : https://192.168.x.x:8443
====================================================
```

### 3. Acessar no browser

```
https://localhost:8443
```

> O banco `explorador.db` e o certificado SSL (`cert.pem` / `key.pem`) são criados
> automaticamente na primeira execução, dentro de `src/`.

---

## 📱 Usando no Celular (GPS Real)

Para capturar GPS real, notebook e celular precisam estar na **mesma rede**. A forma mais
confiável em rede universitária (que isola dispositivos) é o **hotspot do celular**:

```
1. Ativa o hotspot no celular
2. Conecta o notebook no Wi-Fi do hotspot
3. Roda: cd src && python main.py
4. No Chrome do celular: https://192.168.x.x:8443
5. Aceita o aviso de "conexão não confiável"
   (certificado autoassinado — necessário para liberar GPS via HTTPS)
```

### Por que HTTPS é necessário para GPS?

Browsers modernos bloqueiam o `navigator.geolocation` em páginas HTTP fora do `localhost`.
Para contornar sem depender de serviços externos, a aplicação **gera automaticamente um
certificado autoassinado** com o IP local incluído no campo SAN (Subject Alternative Name).
Isso permite o acesso via `https://` e o browser libera a API de geolocalização.

---

## 🔌 Endpoints da API

### Autenticação

| Método | Rota             | Body               | Descrição         |
|--------|------------------|--------------------|-------------------|
| POST   | `/auth/register` | `{name, nickname}` | Cria usuário      |
| POST   | `/auth/login`    | `{nickname}`       | Login (apenas apelido) |
| GET    | `/users`         | —                  | Lista usuários    |

### Sessões & Localização

| Método | Rota                        | Body                     | Descrição              |
|--------|-----------------------------|--------------------------|------------------------|
| POST   | `/session/start`            | `{user_id}`              | Inicia sessão          |
| POST   | `/session/stop/<id>`        | —                        | Encerra sessão         |
| POST   | `/location`                 | `{session_id, lat, lon}` | Registra ponto GPS     |
| GET    | `/sessions`                 | —                        | Todas as sessões       |
| GET    | `/users/<user_id>/sessions` | —                        | Histórico do usuário   |
| GET    | `/session/<id>/track`       | —                        | Pontos GPS da sessão   |

### Ranking

| Método | Rota             | Descrição                         |
|--------|------------------|-----------------------------------|
| GET    | `/ranking/daily` | Ranking de hoje por distância     |
| GET    | `/ranking/live`  | Usuários ativos (últimos 5 min)   |

### Evento WebSocket — `location_update`

```json
{
  "user_id": 1,
  "nickname": "edu",
  "name": "Eduardo",
  "lat": -31.7707,
  "lon": -52.3414,
  "status": "andando",
  "current_speed_kmh": 4.2,
  "distance_m": 380,
  "pace_min_km": 13.7,
  "calories": 23
}
```

Eventos adicionais emitidos: `session_start` e `session_stop`.

---

## 🗄️ Banco de Dados

```sql
users         → id, name, nickname, created_at
sessions      → id, user_id, started_at, ended_at, distance_m
points        → id, session_id, lat, lon, ts
online_status → user_id, session_id, last_lat, last_lon, last_seen, status
```

**Distância acumulada incremental:** a coluna `distance_m` é atualizada a cada ponto
recebido somando apenas o delta em relação ao ponto anterior (Haversine). Evita recalcular
sobre todos os pontos a cada atualização.

**WAL mode:** `PRAGMA journal_mode=WAL` permite leituras simultâneas sem bloquear a escrita —
desejável com Flask em modo threading, onde várias requisições tocam o mesmo arquivo.

---

## 🏗️ Arquitetura

```
Celular (browser)
  │  navigator.geolocation.watchPosition()
  │  POST /location
  ▼
Flask + Flask-SocketIO  (src/main.py)
  │  salva ponto no SQLite
  │  atualiza distance_m (delta incremental + Haversine)
  │  calcula velocidade atual (últimos 6 pontos)
  │  emite location_update → todos os clientes via Socket.IO
  ▼
SQLite WAL  (explorador.db)

Outros browsers conectados
  recebem location_update via WebSocket
  atualizam aba "Ao Vivo" e Ranking em tempo real
```

---

## ⚠️ Status & Limitações Conhecidas

Projeto de demonstração / portfólio. Não endurecido para produção:

- **Sem autenticação real:** login só por apelido, sem senha nem token de sessão. Qualquer
  pessoa que saiba um apelido entra como aquele usuário.
- **`SECRET_KEY` hardcoded** em `main.py` — deveria vir de variável de ambiente.
- **Sem validação de input** nos endpoints (`lat`/`lon` fora de faixa, campos ausentes em
  `/location` podem gerar `KeyError`).
- **`cryptography` não está em `requirements.txt`** (ver nota em "Como Rodar"); a linha
  `-e flask` do arquivo também é atípica.
- **CORS liberado para `*`** no Socket.IO.
- **Servidor de desenvolvimento** (`socketio.run`), sem WSGI de produção.
- **Calorias** são uma estimativa grosseira (`km × 60`), sem considerar peso/ritmo.
- **Tudo em um arquivo:** rotas, WebSocket, SSL e lógica em `main.py`; frontend inteiro em
  `static/index.html`.

### 🔮 Melhorias Futuras
- [ ] Validação de input nos endpoints
- [ ] Mover `SECRET_KEY` para `.env` e fixar `cryptography` em `requirements.txt`
- [ ] Mapa de calor das ruas mais percorridas (heatmap Leaflet)
- [ ] Exportar percurso como GPX (Strava / Garmin)
- [ ] PWA para instalar como app
- [ ] Separar rotas em Blueprints Flask (`auth`, `sessions`, `ranking`)

---

## 📁 Estrutura do Repositório

```
explorador-urbano/
├── README.md                # versão em inglês (vitrine)
├── README.pt.md             # este arquivo
├── LICENSE                  # MIT
├── relatorio_explorador.pdf # metodologia / uso de IA
└── src/
    ├── main.py              # Servidor Flask: rotas, WebSocket, SSL, lógica
    ├── requirements.txt     # Dependências Python
    └── static/
        └── index.html       # Frontend completo (HTML + CSS + JS em arquivo único)
```

> `explorador.db`, `cert.pem` e `key.pem` são gerados automaticamente e não são versionados.

---

## 📄 Licença

MIT — veja [LICENSE](LICENSE).

---

*Desenvolvido para a disciplina de Uso de IA — Engenharia de Computação, UFPel (2026)*
