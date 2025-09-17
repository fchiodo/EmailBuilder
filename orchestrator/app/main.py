from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
from enum import Enum
import httpx
import json
import os
from pathlib import Path

app = FastAPI(title="EmailBuilder Orchestrator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TemplateType(str, Enum):
    POST_PURCHASE = "post_purchase"
    CART_ABANDON = "cart_abandon"
    ORDER_CONFIRMATION = "order_confirmation"

class TemplateBlock(BaseModel):
    type: str

class HeroBlock(TemplateBlock):
    type: str = "hero"
    headline: str
    subcopy: str
    imageUrl: str

class ItemsBlock(TemplateBlock):
    type: str = "items"
    title: str
    items: List[Dict[str, str]]

class RecommendationsBlock(TemplateBlock):
    type: str = "recommendations"
    title: str
    items: List[Dict[str, str]]

class FooterBlock(TemplateBlock):
    type: str = "footer"
    legal: str
    preferencesUrl: str
    unsubscribeUrl: str

class TemplateRequest(BaseModel):
    templateType: TemplateType
    locale: str
    skus: List[str]
    customerContext: Optional[Dict[str, Any]] = None

class TemplateSchema(BaseModel):
    locale: str
    templateType: TemplateType
    subject: str
    preheader: str
    blocks: List[Union[HeroBlock, ItemsBlock, RecommendationsBlock, FooterBlock]]

class GenerateResponse(BaseModel):
    jsonTemplate: TemplateSchema
    mjml: str
    html: str
    tokensVersion: str

RENDERER_URL = os.getenv("RENDERER_URL", "http://localhost:3001")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "orchestrator"}

@app.get("/tokens/{template_type}")
async def get_tokens(template_type: TemplateType):
    tokens_path = Path(f"../tokens/{template_type}.json")
    if tokens_path.exists():
        with open(tokens_path, 'r') as f:
            return json.load(f)
    return {"error": "Tokens not found", "templateType": template_type}

@app.get("/history/{template_type}/examples")
async def get_examples(template_type: TemplateType):
    examples = {
        "cart_abandon": [
            {"subject": "Hai dimenticato qualcosa nel carrello!", "preheader": "Completa il tuo acquisto prima che sia troppo tardi"},
            {"subject": "I tuoi articoli ti aspettano", "preheader": "Solo per te: sconto del 10% sul tuo carrello"}
        ],
        "post_purchase": [
            {"subject": "Grazie per il tuo acquisto!", "preheader": "Ordine confermato - spedizione in corso"},
            {"subject": "Il tuo ordine è in viaggio", "preheader": "Traccia la spedizione e scopri prodotti correlati"}
        ],
        "order_confirmation": [
            {"subject": "Conferma ordine #12345", "preheader": "Tutti i dettagli del tuo acquisto"},
            {"subject": "Ordine ricevuto - preparazione in corso", "preheader": "Grazie per aver scelto il nostro store"}
        ]
    }
    return examples.get(template_type, [])

@app.post("/generate", response_model=GenerateResponse)
async def generate_email(request: TemplateRequest):
    try:
        # 1. Load Design Tokens
        tokens_response = await get_tokens(request.templateType)

        # 2. Generate JSON Template using AI (mock for now)
        json_template = await generate_json_template(request, tokens_response)

        # 3. Render MJML and HTML
        render_response = await render_template(json_template)

        return GenerateResponse(
            jsonTemplate=json_template,
            mjml=render_response["mjml"],
            html=render_response["html"],
            tokensVersion=tokens_response.get("version", "1.0.0")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def generate_json_template(request: TemplateRequest, tokens: Dict) -> TemplateSchema:
    # Mock AI generation - in production this would use LangGraph + OpenAI
    mock_templates = {
        "cart_abandon": {
            "subject": "Hai dimenticato qualcosa nel carrello!",
            "preheader": "Completa il tuo acquisto prima che sia troppo tardi",
            "blocks": [
                {
                    "type": "hero",
                    "headline": "I tuoi articoli ti aspettano",
                    "subcopy": "Non perdere l'occasione di completare il tuo acquisto",
                    "imageUrl": "https://via.placeholder.com/600x300"
                },
                {
                    "type": "items",
                    "title": "Articoli nel tuo carrello",
                    "items": [
                        {
                            "sku": sku,
                            "name": f"Prodotto {sku}",
                            "price": "€29.99",
                            "imageUrl": "https://via.placeholder.com/150x150",
                            "url": f"https://shop.example.com/product/{sku}"
                        } for sku in request.skus[:3]
                    ]
                },
                {
                    "type": "footer",
                    "legal": "© 2024 EmailBuilder. Tutti i diritti riservati.",
                    "preferencesUrl": "https://shop.example.com/preferences",
                    "unsubscribeUrl": "https://shop.example.com/unsubscribe"
                }
            ]
        },
        "post_purchase": {
            "subject": "Grazie per il tuo acquisto!",
            "preheader": "Ordine confermato - spedizione in corso",
            "blocks": [
                {
                    "type": "hero",
                    "headline": "Ordine confermato!",
                    "subcopy": "Grazie per aver scelto il nostro store",
                    "imageUrl": "https://via.placeholder.com/600x300"
                },
                {
                    "type": "recommendations",
                    "title": "Prodotti che potrebbero interessarti",
                    "items": [
                        {
                            "sku": f"REC-{i}",
                            "name": f"Prodotto Consigliato {i}",
                            "price": "€39.99",
                            "imageUrl": "https://via.placeholder.com/150x150",
                            "url": f"https://shop.example.com/product/REC-{i}"
                        } for i in range(1, 4)
                    ]
                }
            ]
        }
    }

    template_data = mock_templates.get(request.templateType, mock_templates["cart_abandon"])

    return TemplateSchema(
        locale=request.locale,
        templateType=request.templateType,
        **template_data
    )

async def render_template(template: TemplateSchema) -> Dict[str, str]:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{RENDERER_URL}/render",
                json=template.dict(),
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError:
            # Fallback mock response if renderer is not available
            return {
                "mjml": f"<mjml><mj-body><mj-section><mj-column><mj-text>{template.subject}</mj-text></mj-column></mj-section></mj-body></mjml>",
                "html": f"<html><body><h1>{template.subject}</h1><p>{template.preheader}</p></body></html>"
            }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)