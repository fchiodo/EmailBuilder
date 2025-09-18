from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union, AsyncGenerator
from enum import Enum
import httpx
import json
import os
from pathlib import Path
import uuid
import shutil
import mimetypes
from PIL import Image
import base64
import io
import asyncio
import time

# Import LangChain agents (simplified to avoid import issues)
try:
    from app.agents.supervisor import supervisor_agent, EmailGenerationInput
    from app.langgraph_endpoint import generate_email_stream_langgraph
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("LangGraph agents not available - using fallback implementation")

    # Create fallback EmailGenerationInput
    class EmailGenerationInput(BaseModel):
        template_type: str
        locale: str = "en"
        primary_sku: str
        uploaded_file_content: Optional[str] = None
        category: str = "general"

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
    customHtml: Optional[str] = None

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
    customTemplateId: Optional[str] = None
    brandGuidelineFile: Optional[str] = None
    category: Optional[str] = "general"

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
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

def safe_json_dumps(data: Dict[str, Any]) -> str:
    """Safely serialize data to JSON for SSE streaming."""
    try:
        # First, clean any potential problematic data
        def clean_data(obj):
            if isinstance(obj, dict):
                return {k: clean_data(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_data(item) for item in obj]
            elif isinstance(obj, str):
                # Remove control characters and ensure valid UTF-8
                return ''.join(char for char in obj if ord(char) >= 32 or char in '\n\r\t')
            else:
                return obj

        cleaned_data = clean_data(data)
        return json.dumps(cleaned_data, ensure_ascii=True, separators=(',', ':'))
    except Exception as e:
        # Ultimate fallback
        return json.dumps({"error": f"JSON serialization failed: {str(e)}"}, ensure_ascii=True)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "orchestrator"}

@app.post("/upload-template")
async def upload_template(file: UploadFile = File(...)):
    try:
        file_id = str(uuid.uuid4())
        file_extension = Path(file.filename or "template").suffix
        file_path = UPLOAD_DIR / f"{file_id}{file_extension}"

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {
            "success": True,
            "fileId": file_id,
            "filename": file.filename,
            "message": "Template file uploaded successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/templates")
async def list_templates():
    templates = []
    if UPLOAD_DIR.exists():
        for file_path in UPLOAD_DIR.iterdir():
            if file_path.is_file():
                templates.append({
                    "fileId": file_path.stem,
                    "filename": file_path.name,
                    "uploadedAt": os.path.getmtime(file_path)
                })
    return {"templates": templates}

@app.get("/tokens/{template_type}")
async def get_tokens(template_type: TemplateType):
    tokens_path = Path(f"../../tokens/{template_type}.json")
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

@app.post("/test-agents")
async def test_agents(request: TemplateRequest):
    """Test endpoint for multi-agent system with detailed response."""
    try:
        result = await generate_email_with_agents(request)

        return {
            "success": result["success"],
            "workflow_state": result.get("workflow_state", {}),
            "error": result.get("error"),
            "agent_results": {
                "brand_guidelines": result.get("workflow_state", {}).get("brand_guidelines"),
                "primary_product": result.get("workflow_state", {}).get("primary_product"),
                "related_products": result.get("workflow_state", {}).get("related_products"),
                "assets": result.get("workflow_state", {}).get("assets"),
                "copy": result.get("workflow_state", {}).get("copy"),
                "template_json": result.get("workflow_state", {}).get("template_json"),
                "final_output": result.get("workflow_state", {}).get("final_output")
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "workflow_state": {},
            "agent_results": {}
        }

@app.post("/generate-stream")
async def generate_email_stream(request: TemplateRequest):
    """Stream endpoint showing real-time progress through agents."""

    async def generate_with_progress() -> AsyncGenerator[str, None]:
        try:
            # Prepare input
            primary_sku = request.skus[0] if request.skus else "DEFAULT-SKU"

            # Load brand guideline file content if provided
            brand_guideline_content = None
            if request.brandGuidelineFile:
                brand_file_path = UPLOAD_DIR / f"{request.brandGuidelineFile}"
                if brand_file_path.exists():
                    with open(brand_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        brand_guideline_content = f.read()

            # Create input for email generation
            generation_input = EmailGenerationInput(
                template_type=request.templateType.value,
                locale=request.locale,
                primary_sku=primary_sku,
                uploaded_file_content=brand_guideline_content,
                category=request.category or "general"
            )

            # Stream progress updates
            yield f"data: {safe_json_dumps({'step': 'start', 'agent': 'supervisor', 'message': 'Inizializzazione workflow multi-agent...', 'progress': 0})}\n\n"
            await asyncio.sleep(0.5)

            yield f"data: {safe_json_dumps({'step': 'brand_analysis', 'agent': 'retriever', 'message': 'Analisi linee guida del brand...', 'progress': 15})}\n\n"

            # Step 1: Brand Analysis (simplified for demo without OpenAI)
            brand_guidelines = {
                "tone": "professional and friendly",
                "colors": ["#dc2626", "#64748b"],
                "style": "modern and clean",
                "messaging": "customer-focused and trustworthy",
                "template_focus": "clear product presentation"
            } if generation_input.uploaded_file_content else None
            await asyncio.sleep(1)

            yield f"data: {safe_json_dumps({'step': 'product_retrieval', 'agent': 'retriever', 'message': 'Recupero prodotti e correlazioni SKU...', 'progress': 30})}\n\n"

            # Step 2: Product Retrieval (using mock data for now)
            try:
                from app.tools.product_tools import product_lookup_tool, related_products_tool
                primary_product = product_lookup_tool._run(generation_input.primary_sku)
                related_products = related_products_tool._run(generation_input.primary_sku, max_results=3)
            except ImportError:
                # Fallback mock data
                primary_product = {
                    "sku": generation_input.primary_sku,
                    "name": f"Product {generation_input.primary_sku}",
                    "price": "29.99",
                    "description": "Premium quality product",
                    "image_placeholder": f"https://via.placeholder.com/300x200?text={generation_input.primary_sku}"
                }
                related_products = [
                    {
                        "sku": "REL-001", "name": "Related Product 1", "price": "19.99",
                        "description": "Related item", "image_placeholder": "https://via.placeholder.com/300x200?text=REL-001"
                    },
                    {
                        "sku": "REL-002", "name": "Related Product 2", "price": "24.99",
                        "description": "Another related item", "image_placeholder": "https://via.placeholder.com/300x200?text=REL-002"
                    }
                ]

            product_data = {
                "primary_product": primary_product,
                "related_products": related_products
            }
            await asyncio.sleep(1)

            yield f"data: {safe_json_dumps({'step': 'asset_curation', 'agent': 'asset_curator', 'message': 'Selezione e curatela delle immagini...', 'progress': 45})}\n\n"

            # Step 3: Asset Curation
            from app.tools.asset_tools import asset_selector_tool
            hero_assets = asset_selector_tool._run(
                template_type=generation_input.template_type,
                category=generation_input.category,
                asset_type="hero",
                count=1
            )
            grid_assets = asset_selector_tool._run(
                template_type=generation_input.template_type,
                category=generation_input.category,
                asset_type="grid",
                count=2
            )
            assets = {
                "hero": hero_assets[0] if hero_assets else None,
                "grid": grid_assets
            }
            await asyncio.sleep(1)

            yield f"data: {safe_json_dumps({'step': 'copywriting', 'agent': 'copywriter', 'message': 'Generazione copy e microcopy...', 'progress': 60})}\n\n"

            # Step 4: Copywriting (simplified for demo without OpenAI)
            copy_templates = {
                "cart_abandon": {
                    "subject": "Non dimenticare il tuo carrello!",
                    "preheader": "Completa il tuo acquisto prima che sia troppo tardi",
                    "headline": "I tuoi articoli ti stanno aspettando",
                    "subcopy": "Non perdere l'occasione di completare il tuo acquisto con prodotti selezionati.",
                    "cta_primary": "Completa Acquisto"
                },
                "post_purchase": {
                    "subject": "Grazie per il tuo acquisto!",
                    "preheader": "Il tuo ordine è stato confermato",
                    "headline": "Ordine confermato con successo!",
                    "subcopy": "Grazie per aver scelto i nostri prodotti. Il tuo ordine sarà spedito a breve.",
                    "cta_primary": "Traccia Ordine"
                },
                "order_confirmation": {
                    "subject": "Conferma ordine - I tuoi articoli sono in preparazione",
                    "preheader": "Dettagli ordine all'interno",
                    "headline": "Il tuo ordine è confermato!",
                    "subcopy": "Stiamo preparando i tuoi articoli per la spedizione.",
                    "cta_primary": "Visualizza Dettagli"
                }
            }
            copy = copy_templates.get(generation_input.template_type, copy_templates["cart_abandon"])
            await asyncio.sleep(1)

            yield f"data: {safe_json_dumps({'step': 'template_composition', 'agent': 'template_layout', 'message': 'Composizione template JSON...', 'progress': 75})}\n\n"

            # Step 5: Template Composition
            workflow_state = {
                "input": generation_input.dict(),
                "brand_guidelines": brand_guidelines,
                "primary_product": product_data.get("primary_product"),
                "related_products": product_data.get("related_products", []),
                "assets": assets,
                "copy": copy
            }

            # Step 5: Template Composition
            from app.tools.template_tools import tokens_loader_tool
            design_tokens = tokens_loader_tool._run(generation_input.template_type)

            template_json = {
                "subject": copy["subject"],
                "preheader": copy["preheader"],
                "locale": generation_input.locale,
                "templateType": generation_input.template_type,
                "blocks": []
            }

            # Hero block
            hero_block = {
                "type": "hero",
                "headline": copy["headline"],
                "subcopy": copy["subcopy"],
                "imageUrl": assets["hero"]["url"] if assets["hero"] else "",
                "ctaLabel": copy["cta_primary"],
                "ctaUrl": "#"
            }
            template_json["blocks"].append(hero_block)

            # Items block
            if not primary_product.get("error"):
                items_block = {
                    "type": "items",
                    "title": "Il Tuo Articolo",
                    "items": [{
                        "name": primary_product["name"],
                        "sku": primary_product["sku"],
                        "price": primary_product["price"],
                        "imageUrl": primary_product["image_placeholder"],
                        "description": primary_product["description"]
                    }]
                }
                template_json["blocks"].append(items_block)

            # Recommendations block
            if related_products and len(related_products) > 0:
                valid_products = [p for p in related_products if not p.get("error")]
                if valid_products:
                    recommendations_block = {
                        "type": "recommendations",
                        "title": "Potrebbe interessarti anche",
                        "items": [{
                            "name": p["name"],
                            "sku": p["sku"],
                            "price": p["price"],
                            "imageUrl": p["image_placeholder"],
                            "description": p["description"]
                        } for p in valid_products[:3]]
                    }
                    template_json["blocks"].append(recommendations_block)

            # Footer block
            footer_block = {
                "type": "footer",
                "companyName": "EmailBuilder",
                "address": "Via Example 123, Milano, Italia",
                "unsubscribeUrl": "#unsubscribe",
                "socialLinks": []
            }
            template_json["blocks"].append(footer_block)

            template_result = {"template_json": template_json, "design_tokens": design_tokens}
            await asyncio.sleep(1)

            yield f"data: {safe_json_dumps({'step': 'rendering', 'agent': 'render', 'message': 'Rendering MJML e HTML...', 'progress': 90})}\n\n"

            # Step 6: Rendering
            # Simple MJML generation
            mjml_content = f'''
<mjml>
  <mj-head>
    <mj-title>{template_json["subject"]}</mj-title>
    <mj-preview>{template_json["preheader"]}</mj-preview>
  </mj-head>
  <mj-body>
    <mj-section>
      <mj-column>
        <mj-text font-size="24px" font-weight="bold">{copy["headline"]}</mj-text>
        <mj-text>{copy["subcopy"]}</mj-text>
        <mj-button href="#">{copy["cta_primary"]}</mj-button>
      </mj-column>
    </mj-section>
  </mj-body>
</mjml>'''

            # Try to render via MJML service, fallback to simple HTML
            try:
                from app.tools.template_tools import mjml_renderer_tool
                render_result = mjml_renderer_tool._run(mjml_content)
                final_html = render_result.get("html", "")
            except:
                final_html = f'''
<!DOCTYPE html>
<html>
<head><title>{template_json["subject"]}</title></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h1>{copy["headline"]}</h1>
  <p>{copy["subcopy"]}</p>
  <a href="#" style="background: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px;">{copy["cta_primary"]}</a>
</body>
</html>'''

            final_output = {
                "html": final_html,
                "mjml": mjml_content
            }
            await asyncio.sleep(1)

            yield f"data: {safe_json_dumps({'step': 'complete', 'agent': 'supervisor', 'message': 'Email generata con successo!', 'progress': 100})}\n\n"

            # Final result - ensure all strings are properly handled
            result = {
                "success": True,
                "template_json": template_result["template_json"],
                "html": final_output.get("html", "").strip(),
                "mjml": final_output.get("mjml", "").strip(),
                "tokens_version": template_result.get("design_tokens", {}).get("version", "1.0.0")
            }

            # Use proper JSON encoding with ensure_ascii=True for safety
            yield f"data: {safe_json_dumps({'step': 'result', 'result': result})}\n\n"

        except Exception as e:
            yield f"data: {safe_json_dumps({'step': 'error', 'message': f'Errore: {str(e)}', 'progress': 0})}\n\n"

    return StreamingResponse(
        generate_with_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

@app.post("/generate", response_model=GenerateResponse)
async def generate_email(request: TemplateRequest):
    try:
        # Use LangChain multi-agent system for email generation
        result = await generate_email_with_agents(request)

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Email generation failed"))

        # Extract the generated content
        workflow_state = result["workflow_state"]
        final_output = result["final_output"]
        template_json = result["template_json"]

        # Convert to expected response format
        template_schema = TemplateSchema(
            locale=template_json.get("locale", request.locale),
            templateType=request.templateType,
            subject=template_json.get("subject", "Email Subject"),
            preheader=template_json.get("preheader", "Email Preview"),
            blocks=template_json.get("blocks", [])
        )

        return GenerateResponse(
            jsonTemplate=template_schema,
            mjml=final_output.get("mjml", ""),
            html=final_output.get("html", ""),
            tokensVersion=workflow_state.get("design_tokens", {}).get("version", "1.0.0")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def generate_email_with_agents(request: TemplateRequest) -> Dict[str, Any]:
    """Generate email using LangChain multi-agent system."""
    try:
        # Prepare input for supervisor agent
        primary_sku = request.skus[0] if request.skus else "DEFAULT-SKU"

        # Load brand guideline file content if provided
        brand_guideline_content = None
        if request.brandGuidelineFile:
            brand_file_path = UPLOAD_DIR / f"{request.brandGuidelineFile}"
            if brand_file_path.exists():
                with open(brand_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    brand_guideline_content = f.read()

        # Create input for email generation
        generation_input = EmailGenerationInput(
            template_type=request.templateType.value,
            locale=request.locale,
            primary_sku=primary_sku,
            uploaded_file_content=brand_guideline_content,
            category=request.category or "general"
        )

        # Run the supervisor agent workflow
        result = await supervisor_agent.process_template_request(generation_input)

        # Format the result to match expected structure
        if result:
            return {
                "success": True,
                "workflow_state": {},
                "final_output": result,
                "template_json": result.get("jsonTemplate", {})
            }
        else:
            return {
                "success": False,
                "error": "No result from supervisor agent",
                "workflow_state": {},
                "final_output": {},
                "template_json": {}
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"Multi-agent generation failed: {str(e)}"
        }

async def generate_json_template_fallback(request: TemplateRequest, tokens: Dict) -> TemplateSchema:
    # Check if custom template is provided
    if request.customTemplateId:
        custom_template = await load_custom_template(request.customTemplateId, request.templateType)
        if custom_template:
            return TemplateSchema(
                locale=request.locale,
                templateType=request.templateType,
                **custom_template
            )

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
                    "imageUrl": "https://images.unsplash.com/photo-1551524164-6cf96ac925fb?w=600&h=300&fit=crop&q=80"
                },
                {
                    "type": "items",
                    "title": "Articoli nel tuo carrello",
                    "items": [
                        {
                            "sku": sku,
                            "name": f"Prodotto {sku}",
                            "price": "€29.99",
                            "imageUrl": "https://images.unsplash.com/photo-1544966503-7cc5ac882d5f?w=150&h=150&fit=crop&q=80",
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
                    "imageUrl": "https://images.unsplash.com/photo-1551524164-6cf96ac925fb?w=600&h=300&fit=crop&q=80"
                },
                {
                    "type": "recommendations",
                    "title": "Prodotti che potrebbero interessarti",
                    "items": [
                        {
                            "sku": f"REC-{i}",
                            "name": f"Prodotto Consigliato {i}",
                            "price": "€39.99",
                            "imageUrl": "https://images.unsplash.com/photo-1544966503-7cc5ac882d5f?w=150&h=150&fit=crop&q=80",
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
                json=template.model_dump(),
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

async def parse_template_content(template_file: Path) -> Dict[str, Any]:
    """Parse different file types and extract template content"""
    file_extension = template_file.suffix.lower()
    content = {}

    try:
        if file_extension in ['.html', '.htm']:
            # Parse HTML file
            with open(template_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            content = {
                "type": "html",
                "content": html_content,
                "parsed": True
            }

        elif file_extension in ['.txt', '.md']:
            # Parse text/markdown file
            with open(template_file, 'r', encoding='utf-8') as f:
                text_content = f.read()
            content = {
                "type": "text",
                "content": text_content,
                "parsed": True
            }

        elif file_extension in ['.json']:
            # Parse JSON template file
            with open(template_file, 'r', encoding='utf-8') as f:
                json_content = json.load(f)
            content = {
                "type": "json",
                "content": json_content,
                "parsed": True
            }

        elif file_extension in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
            # For images, we'll use them as template background/content
            file_url = f"http://localhost:8000/uploads/{template_file.name}"
            content = {
                "type": "image",
                "url": file_url,
                "parsed": True
            }

        else:
            # Default handling for unknown file types
            file_url = f"http://localhost:8000/uploads/{template_file.name}"
            content = {
                "type": "file",
                "url": file_url,
                "parsed": False
            }

    except Exception as e:
        print(f"Error parsing template content: {e}")
        content = {
            "type": "error",
            "error": str(e),
            "parsed": False
        }

    return content

async def load_custom_template(template_id: str, template_type: TemplateType) -> Optional[Dict]:
    try:
        # Look for the uploaded template file
        template_files = list(UPLOAD_DIR.glob(f"{template_id}.*"))
        if not template_files:
            return None

        template_file = template_files[0]

        # Parse the template content
        parsed_content = await parse_template_content(template_file)

        # Generate template based on parsed content
        if parsed_content.get("type") == "html" and parsed_content.get("parsed"):
            # If it's HTML content, use it directly in the email
            return await create_html_based_template(parsed_content["content"], template_type)

        elif parsed_content.get("type") == "json" and parsed_content.get("parsed"):
            # If it's JSON, try to use it as template structure
            return await create_json_based_template(parsed_content["content"], template_type)

        elif parsed_content.get("type") == "text" and parsed_content.get("parsed"):
            # If it's text content, create a text-based email
            return await create_text_based_template(parsed_content["content"], template_type)

        else:
            # Fallback: use file as image/asset
            file_url = f"http://localhost:8000/uploads/{template_file.name}"
            return await create_asset_based_template(file_url, template_type)

    except Exception as e:
        print(f"Error loading custom template: {e}")
        return None

async def create_html_based_template(html_content: str, template_type: TemplateType) -> Dict:
    """Create template using HTML content directly"""
    # Extract title from HTML if possible
    title_match = None
    try:
        import re
        title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
        title = title_match.group(1) if title_match else f"Custom {template_type.replace('_', ' ').title()}"
    except:
        title = f"Custom {template_type.replace('_', ' ').title()}"

    return {
        "subject": title,
        "preheader": "Created from your HTML template",
        "blocks": [
            {
                "type": "hero",
                "headline": title,
                "subcopy": "Generated from your uploaded HTML template",
                "imageUrl": "https://images.unsplash.com/photo-1551524164-6cf96ac925fb?w=600&h=300&fit=crop&q=80",
                "customHtml": html_content
            }
        ]
    }

async def create_json_based_template(json_content: Dict, template_type: TemplateType) -> Dict:
    """Create template using JSON structure"""
    # Try to use the JSON as a template if it has the right structure
    if "subject" in json_content and "blocks" in json_content:
        return {
            "subject": json_content.get("subject", f"Custom {template_type.replace('_', ' ').title()}"),
            "preheader": json_content.get("preheader", "Created from your JSON template"),
            "blocks": json_content.get("blocks", [])
        }
    else:
        return {
            "subject": f"Custom {template_type.replace('_', ' ').title()} Email",
            "preheader": "Created from your JSON template",
            "blocks": [
                {
                    "type": "hero",
                    "headline": json_content.get("title", f"Custom {template_type.replace('_', ' ').title()}"),
                    "subcopy": json_content.get("description", "Generated from your uploaded JSON template"),
                    "imageUrl": json_content.get("image", "https://images.unsplash.com/photo-1551524164-6cf96ac925fb?w=600&h=300&fit=crop&q=80")
                },
                {
                    "type": "footer",
                    "legal": "© 2024 EmailBuilder. All rights reserved.",
                    "preferencesUrl": "https://shop.example.com/preferences",
                    "unsubscribeUrl": "https://shop.example.com/unsubscribe"
                }
            ]
        }

async def create_text_based_template(text_content: str, template_type: TemplateType) -> Dict:
    """Create template using text content"""
    lines = text_content.strip().split('\n')
    title = lines[0] if lines else f"Custom {template_type.replace('_', ' ').title()}"
    description = '\n'.join(lines[1:]) if len(lines) > 1 else "Generated from your uploaded text template"

    return {
        "subject": title,
        "preheader": "Created from your text template",
        "blocks": [
            {
                "type": "hero",
                "headline": title,
                "subcopy": description,
                "imageUrl": "https://images.unsplash.com/photo-1551524164-6cf96ac925fb?w=600&h=300&fit=crop&q=80"
            },
            {
                "type": "footer",
                "legal": "© 2024 EmailBuilder. All rights reserved.",
                "preferencesUrl": "https://shop.example.com/preferences",
                "unsubscribeUrl": "https://shop.example.com/unsubscribe"
            }
        ]
    }

async def create_asset_based_template(file_url: str, template_type: TemplateType) -> Dict:
    """Create template using uploaded file as asset"""
    return {
        "subject": f"Custom {template_type.replace('_', ' ').title()} Email",
        "preheader": "Designed with your custom template",
        "blocks": [
            {
                "type": "hero",
                "headline": f"Custom {template_type.replace('_', ' ').title()}",
                "subcopy": "This email uses your uploaded template design",
                "imageUrl": file_url
            },
            {
                "type": "footer",
                "legal": "© 2024 EmailBuilder. All rights reserved.",
                "preferencesUrl": "https://shop.example.com/preferences",
                "unsubscribeUrl": "https://shop.example.com/unsubscribe"
            }
        ]
    }

@app.post("/generate-stream-langgraph")
async def generate_email_stream_langgraph_endpoint(request: TemplateRequest):
    """LangGraph-powered streaming endpoint for multi-agent email generation."""
    if not LANGGRAPH_AVAILABLE:
        raise HTTPException(status_code=503, detail="LangGraph multi-agent system not available")
    return await generate_email_stream_langgraph(request, UPLOAD_DIR)

# Mount static files for uploaded templates (must be after route definitions)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)