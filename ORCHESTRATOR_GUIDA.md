# 📧 EmailBuilder Orchestrator - Guida Dettagliata

## 🎯 Panoramica

L'**Orchestrator** è il cervello del sistema EmailBuilder. È un servizio FastAPI che coordina la generazione di email personalizzate, gestisce i template personalizzati e orchestra la comunicazione tra frontend e renderer.

## 📁 Struttura del Progetto

```
orchestrator/
├── app/
│   └── main.py           # Core del servizio orchestrator
├── uploads/              # Directory per template personalizzati
├── venv/                 # Ambiente virtuale Python
└── requirements.txt      # Dipendenze Python
```

## 🔧 File main.py - Analisi Dettagliata

### Importazioni e Setup Iniziale

```python
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
```

**Tecnologie Utilizzate:**
- **FastAPI**: Framework web moderno per API REST
- **Pydantic**: Validazione e serializzazione dati
- **CORS**: Gestione richieste cross-origin dal frontend
- **Static Files**: Servizio file statici per template caricati

### Modelli Dati (Pydantic Models)

#### TemplateType (Enum)
```python
class TemplateType(str, Enum):
    POST_PURCHASE = "post_purchase"
    CART_ABANDON = "cart_abandon"
    ORDER_CONFIRMATION = "order_confirmation"
```
**Scopo**: Definisce i 3 tipi di email supportati dal sistema.

#### Blocchi Template

##### HeroBlock
```python
class HeroBlock(TemplateBlock):
    type: str = "hero"
    headline: str           # Titolo principale
    subcopy: str           # Sottotitolo descrittivo
    imageUrl: str          # URL immagine hero
    customHtml: Optional[str] = None  # HTML personalizzato
```
**Funzione**: Sezione hero dell'email con immagine e testi principali.

##### ItemsBlock
```python
class ItemsBlock(TemplateBlock):
    type: str = "items"
    title: str
    items: List[Dict[str, str]]  # Lista prodotti nel carrello
```
**Funzione**: Visualizza prodotti (es. carrello abbandonato).

##### RecommendationsBlock
```python
class RecommendationsBlock(TemplateBlock):
    type: str = "recommendations"
    title: str
    items: List[Dict[str, str]]  # Prodotti consigliati
```
**Funzione**: Mostra prodotti correlati/consigliati.

##### FooterBlock
```python
class FooterBlock(TemplateBlock):
    type: str = "footer"
    legal: str                    # Testo legale
    preferencesUrl: str          # Link preferenze
    unsubscribeUrl: str          # Link disiscrizione
```
**Funzione**: Footer con informazioni legali e link di gestione.

## 🛣️ Endpoint API

### 1. Health Check
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "orchestrator"}
```
**Funzione**: Verifica stato del servizio.

### 2. Upload Template Personalizzato
```python
@app.post("/upload-template")
async def upload_template(file: UploadFile = File(...)):
```
**Processo**:
1. Riceve file multipart dal frontend
2. Genera UUID univoco per il file
3. Salva in `/orchestrator/uploads/`
4. Ritorna ID file per uso successivo

### 3. Lista Template
```python
@app.get("/templates")
async def list_templates():
```
**Funzione**: Elenca tutti i template personalizzati caricati.

### 4. Caricamento Token Design
```python
@app.get("/tokens/{template_type}")
async def get_tokens(template_type: TemplateType):
```
**Processo**:
1. Cerca file JSON con token design per tipo template
2. Carica colori, font, spaziature specifiche
3. Ritorna configurazione styling

### 5. Esempi Storici
```python
@app.get("/history/{template_type}/examples")
async def get_examples(template_type: TemplateType):
```
**Contenuto**: Oggetti e preheader di esempio per ogni tipo di email.

### 6. Generazione Email (PRINCIPALE)
```python
@app.post("/generate", response_model=GenerateResponse)
async def generate_email(request: TemplateRequest):
```

**Flusso Completo**:

1. **Caricamento Token Design**
   ```python
   tokens_response = await get_tokens(request.templateType)
   ```

2. **Generazione Template JSON**
   ```python
   json_template = await generate_json_template(request, tokens_response)
   ```

3. **Rendering MJML/HTML**
   ```python
   render_response = await render_template(json_template)
   ```

4. **Risposta Completa**
   ```python
   return GenerateResponse(
       jsonTemplate=json_template,
       mjml=render_response["mjml"],
       html=render_response["html"],
       tokensVersion=tokens_response.get("version", "1.0.0")
   )
   ```

## 🎨 Sistema Template Personalizzati

### Parsing Intelligente dei File

#### `parse_template_content()`
Analizza diversi tipi di file:

**HTML/HTM**:
- Estrae contenuto HTML completo
- Preserva styling CSS inline
- Identifica tag `<title>` per oggetto email

**JSON**:
- Parsifica strutture dati template
- Supporta schema template completi
- Validazione formato

**Testo/Markdown**:
- Prima riga = titolo
- Resto = contenuto descrittivo
- Conversione automatica in struttura email

**Immagini**:
- PNG, JPG, GIF, WebP
- Utilizzate come hero image o prodotti
- URL servito via endpoint `/uploads/`

### Generatori Template Specializzati

#### `create_html_based_template()`
```python
async def create_html_based_template(html_content: str, template_type: TemplateType):
```
**Processo**:
1. Estrae `<title>` da HTML per oggetto email
2. Incorpora HTML completo nel blocco hero
3. Utilizza `customHtml` per rendering diretto

#### `create_json_based_template()`
```python
async def create_json_based_template(json_content: Dict, template_type: TemplateType):
```
**Logica**:
- Se JSON contiene `subject` e `blocks` → usa direttamente
- Altrimenti → estrae `title`, `description`, `image` e crea struttura

#### `create_text_based_template()`
```python
async def create_text_based_template(text_content: str, template_type: TemplateType):
```
**Conversione**:
- Prima riga → headline
- Righe successive → subcopy
- Genera struttura email completa

## 🔄 Integrazione con Renderer

### Chiamata API Renderer
```python
async def render_template(template: TemplateSchema) -> Dict[str, str]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{RENDERER_URL}/render",
            json=template.model_dump(),
            timeout=30.0
        )
```

**Comunicazione**:
1. Invia schema JSON al renderer (porta 3001)
2. Renderer converte in MJML
3. MJML compilato in HTML finale
4. Ritorna MJML + HTML + warnings

### Fallback di Sicurezza
```python
except httpx.RequestError:
    return {
        "mjml": f"<mjml>...",  # MJML base
        "html": f"<html>..."   # HTML semplice
    }
```

## 📂 Gestione File Statici

```python
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
```

**Funzione**: Serve template caricati via URL `http://localhost:8000/uploads/filename`

## 🛡️ Sicurezza e Validazione

### CORS Policy
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Validazione Pydantic
- Tutti i dati in input/output validati automaticamente
- Prevenzione errori di tipo
- Documentazione API automatica

### Gestione Errori
```python
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

## 🚀 Flusso Operativo Completo

1. **Frontend** carica template personalizzato
2. **Orchestrator** salva file e genera ID univoco
3. **Usuario** configura email (tipo, locale, SKU)
4. **Orchestrator** riceve richiesta generazione
5. **Sistema** carica token design appropriati
6. **Parser** analizza template personalizzato se presente
7. **Generatore** crea schema JSON strutturato
8. **Renderer** converte schema in MJML/HTML
9. **Orchestrator** ritorna email completa al frontend
10. **Frontend** visualizza preview finale

## 🔧 Configurazione Ambiente

### Variabili d'Ambiente
- `RENDERER_URL`: URL servizio renderer (default: http://localhost:3001)
- `PORT`: Porta orchestrator (default: 8000)

### Dipendenze Python
- `fastapi`: Framework web
- `uvicorn`: Server ASGI
- `pydantic`: Validazione dati
- `httpx`: Client HTTP asincrono
- `Pillow`: Elaborazione immagini

## 📈 Monitoraggio e Logging

### Logging Applicativo
```python
print(f"Error loading custom template: {e}")
```

### Metriche Disponibili
- Health check endpoint per monitoring
- Timeout configurabili per chiamate esterne
- Gestione errori strutturata

## 🎯 Conclusioni

L'orchestrator rappresenta il cuore dell'architettura EmailBuilder, fornendo:

- **Flessibilità**: Supporto multipli formati template
- **Scalabilità**: Architettura asincrona FastAPI
- **Robustezza**: Gestione errori e fallback
- **Estendibilità**: Facile aggiunta nuovi tipi template
- **Sicurezza**: Validazione dati completa

Il sistema è progettato per essere **production-ready** con gestione completa del ciclo di vita delle email personalizzate.