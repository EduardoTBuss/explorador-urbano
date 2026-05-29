# 🗺️ Explorador Urbano

> **Aplicação web de rastreamento de percursos urbanos em tempo real, com ranking multiusuário e atualização via WebSocket.**

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)](https://flask.palletsprojects.com)
[![SQLite](https://img.shields.io/badge/SQLite-WAL_mode-003B57?logo=sqlite)](https://sqlite.org)
[![Leaflet](https://img.shields.io/badge/Leaflet.js-1.9.4-199900?logo=leaflet)](https://leafletjs.com)
[![Socket.IO](https://img.shields.io/badge/Socket.IO-realtime-010101?logo=socket.io)](https://socket.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 Contexto Acadêmico

Projeto desenvolvido para a disciplina optativa **"Uso de Inteligência Artificial no Desenvolvimento de Software"** do curso de **Engenharia de Computação — UFPel (2026)**.

O objetivo da disciplina era aprender a utilizar ferramentas de IA generativa (vibecoding) de forma estruturada e consciente: não apenas como gerador de código, mas como acelerador técnico onde as decisões de arquitetura, requisitos e revisão crítica partiram integralmente do aluno.

**Modelo utilizado:** Claude (Anthropic) via claude.ai  
**Metodologia:** Documentada em [`relatorio_explorador.pdf`](relatorio_explorador.pdf)

---

## 📸 Preview

> *GPS ao vivo no celular → trilha desenhada em tempo real → ranking atualizado instantaneamente*

```
Aba Mapa          Aba Histórico     Aba Ranking       Aba Ao Vivo
┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐
│  🗺️ mapa   │    │ 📊 gráfico │    │ 🥇 Eduardo │    │ 🟢 Eduardo │
│  com       │    │ distância  │    │ 🥈 Maria   │    │ andando    │
│  trilhas   │    │ diária     │    │ 🥉 João    │    │ 4.2 km/h   │
│  coloridas │    │            │    │            │    │            │
└────────────┘    └────────────┘    └────────────┘    └────────────┘
```

---

## ✨ Funcionalidades

### 📍 Rastreamento GPS
- Captura de posição via `navigator.geolocation.watchPosition` no browser do celular
- Modo simulação por clique no mapa (para testes no desktop)
- Fallback automático GPS → simulação em caso de erro
- Trilha atual desenhada em tempo real (polilinha vermelha)
- Trilhas históricas de sessões anteriores em cores distintas

### 👤 Usuários
- Cadastro por nome e apelido (sistema simples, sem senha — foco em demo)
- Login por apelido
- Sessão salva em `localStorage` para não logar novamente

### 📊 Estatísticas por Sessão
- Distância percorrida (m / km)
- Duração (hh:mm:ss)
- Pace (min/km)
- Velocidade média e atual (km/h)
- Calorias estimadas (~60 kcal/km para 70 kg)
- Status de movimento: `andando` · `devagar` · `parado`

### 🏆 Ranking
- Ranking diário por distância total com medalhas para o top 3
- Calculado por query SQL direta — sem loop sobre pontos

### 📡 Tempo Real (WebSocket)
- Atualização ao vivo via Socket.IO: posições, sessões iniciadas/encerradas
- Lista de usuários ativos nos últimos 5 minutos com status e velocidade
- Feed de eventos na aba "Ao Vivo"

---

## 🛠️ Stack Técnica

| Camada    | Tecnologia                            |
|-----------|---------------------------------------|
| Backend   | Python 3.10+ · Flask                  |
| WebSocket | Flask-SocketIO (async threading)      |
| Banco     | SQLite3 (stdlib) · WAL mode           |
| Frontend  | HTML5 · CSS3 · JavaScript ES6+        |
| Mapa      | Leaflet.js 1.9.4 · OpenStreetMap      |
| Gráfico   | Chart.js                              |
| GPS       | Web Geolocation API                   |
| SSL       | `cryptography` (geração programática) |

**Zero dependências externas de serviço:** sem banco externo, sem cloud, sem ORM.

---

## 🚀 Como Rodar

### 1. Clonar e instalar dependências

```bash
git clone https://github.com/EduardoTBuss/explorador-urbano
cd explorador-urbano
pip install -r requirements.txt
```

### 2. Rodar o servidor

```bash
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

> O banco `explorador.db` e o certificado SSL são criados automaticamente na primeira execução.

---

## 📱 Usando no Celular (GPS Real)

Para capturar GPS real do celular, notebook e celular precisam estar na **mesma rede**. A forma mais confiável em rede universitária (que isola dispositivos) é usar o **hotspot do celular**:

```
1. Ativa o hotspot no celular
2. Conecta o notebook no Wi-Fi do hotspot
3. Roda: python main.py
4. No Chrome do celular: https://192.168.x.x:8443
5. Aceita o aviso de "conexão não confiável"
   (certificado autoassinado — necessário para liberar GPS via HTTPS)
```

### Por que HTTPS é necessário para GPS?

Browsers modernos bloqueiam o `navigator.geolocation` em páginas HTTP fora do `localhost`. Para contornar isso sem depender de serviços externos, a aplicação **gera automaticamente um certificado SSL autoassinado** com o IP local da máquina incluído no campo SAN (Subject Alternative Name). Isso permite que o celular acesse via `https://` e o browser libere a API de geolocalização.

---

## 🔌 Endpoints da API

### Autenticação

| Método | Rota             | Body               | Descrição         |
|--------|------------------|--------------------|-------------------|
| POST   | `/auth/register` | `{name, nickname}` | Cria usuário      |
| POST   | `/auth/login`    | `{nickname}`       | Login             |
| GET    | `/users`         | —                  | Lista usuários    |

### Sessões & Localização

| Método | Rota                        | Body                     | Descrição              |
|--------|-----------------------------|--------------------------|------------------------|
| POST   | `/session/start`            | `{user_id}`              | Inicia sessão          |
| POST   | `/session/stop/<id>`        | —                        | Encerra sessão         |
| POST   | `/location`                 | `{session_id, lat, lon}` | Registra ponto GPS     |
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
  "lat": -31.7707,
  "lon": -52.3414,
  "status": "andando",
  "current_speed_kmh": 4.2,
  "distance_m": 380,
  "pace_min_km": 13.7,
  "calories": 23
}
```

---

## 🗄️ Banco de Dados

Criado automaticamente em `explorador.db` na primeira execução.

```sql
users        → id, name, nickname, created_at
sessions     → id, user_id, started_at, ended_at, distance_m
points       → id, session_id, lat, lon, ts
online_status→ user_id, session_id, last_lat, last_lon, last_seen, status
```

**Distância acumulada incremental:** a coluna `distance_m` é atualizada a cada ponto recebido somando apenas o delta em relação ao ponto anterior (via fórmula de Haversine). Evita recalcular sobre todos os pontos — operação O(n) que travaria sessões longas.

**WAL mode:** `PRAGMA journal_mode=WAL` permite leituras simultâneas sem bloquear escrita — necessário com Flask threading.

---

## 🏗️ Arquitetura

```
Celular (browser)
  │  navigator.geolocation.watchPosition()
  │  POST /location  (a cada ~3–5 s)
  ▼
Flask + Flask-SocketIO  (main.py)
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

## 🤖 Uso de Inteligência Artificial

Este projeto foi desenvolvido com uso extensivo de IA generativa como parte dos objetivos da disciplina. O processo completo está documentado em **[`relatorio_ia.pdf`](relatorio_ia.pdf)**.

**Resumo do processo:**

| Etapa | O que foi feito |
|-------|----------------|
| 1 | Envio de proposta PDF estruturada com motivação, fluxo de uso e escolhas técnicas |
| 2 | Análise do código base pelo modelo (ZIP) para compreender arquitetura existente |
| 3 | Especificação de 10 requisitos detalhados → plano + código gerado |
| 4 | Revisão do código final pelo modelo sem modificações → 5 bugs identificados |
| 5 | Correção cirúrgica dos bugs identificados |

**O diferencial da abordagem:** ao invés de pedir código diretamente, a IA recebeu uma proposta estruturada com contexto completo — motivação, público-alvo, escolhas técnicas já pensadas. As decisões de arquitetura e requisitos partiram integralmente do aluno; a IA foi utilizada como ferramenta de aceleração.

---

## 🔮 Melhorias Futuras

- [ ] Validação de input nos endpoints (`lat/lon` fora de range, campos obrigatórios)
- [ ] Mover `SECRET_KEY` para variável de ambiente (`.env`)
- [ ] Mapa de calor das ruas mais percorridas (heatmap Leaflet)
- [ ] Exportar percurso como GPX (compatível com Strava / Garmin)
- [ ] PWA para instalar no celular como app nativo
- [ ] Separar rotas em Blueprints Flask (`auth`, `sessions`, `ranking`)

---

## 📁 Estrutura do Repositório

```
explorador-urbano/
├── README.md
├── relatorio_explorador.pdf
└── src/
    ├── main.py              # Servidor Flask: rotas, WebSocket, SSL, lógica
    ├── requirements.txt     # Dependências Python
    └── static/
        └── index.html       # Frontend completo (HTML + CSS + JS em arquivo único)
```

> `explorador.db`, `cert.pem` e `key.pem` são gerados automaticamente e não estão versionados.

---

## 📄 Licença

MIT — veja [LICENSE](LICENSE).

---

*Desenvolvido para a disciplina de Uso de IA — Engenharia de Computação, UFPel (2026)*