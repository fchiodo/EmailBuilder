# EmailBuilder

Sistema di generazione email automatizzato basato su Design Tokens estratti da template storici.

## 🧱 Architettura

- **Frontend**: Next.js + TypeScript (UI per selezione template, preview HTML)
- **Orchestrator**: FastAPI + LangGraph (workflow AI per generazione contenuti)
- **Renderer**: Node.js + Express + MJML (compilazione template → HTML)
- **Style Mining**: Pipeline per estrazione Design Tokens da HTML/PDF/immagini

## 🚀 Quick Start

```bash
# Avvia tutti i servizi
docker-compose up -d

# Accedi alla UI
open http://localhost:3000
```

## 🏗️ Struttura Progetto

```
/frontend          # Next.js UI
/orchestrator      # FastAPI + LangGraph
/renderer          # MJML Service
/style-mining      # Pipeline estrazione tokens
/tokens           # Design Tokens (DTCG)
/templates        # Sorgenti storici (HTML/PDF/IMG)
```

## 🔧 Sviluppo

Ogni servizio ha il proprio README con istruzioni specifiche.

Roadmap: 8 settimane (W1-W8) come da specifica.