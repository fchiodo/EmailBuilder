"""LangGraph-based streaming endpoint for multi-agent email generation."""

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import json
import asyncio
from langchain_core.messages import HumanMessage

from app.agents.supervisor import supervisor_agent, EmailGenerationInput, AgentState


async def generate_email_stream_langgraph(request, UPLOAD_DIR):
    """Stream endpoint using LangGraph multi-agent workflow."""

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

            # Create input for LangGraph workflow
            generation_input = EmailGenerationInput(
                template_type=request.templateType.value,
                locale=request.locale,
                primary_sku=primary_sku,
                uploaded_file_content=brand_guideline_content,
                category=request.category or "general"
            )

            # Map agent steps to Italian messages
            agent_messages = {
                "supervisor": "Inizializzazione workflow multi-agent LangGraph...",
                "retriever": "Recupero prodotti e analisi brand guidelines con OpenAI...",
                "asset_curator": "Selezione deterministica delle immagini...",
                "copywriter": "Generazione copy intelligente con OpenAI...",
                "template_layout": "Composizione template JSON strutturata...",
                "render": "Rendering MJML→HTML finale..."
            }

            # Initialize LangGraph state
            initial_state = AgentState(
                messages=[HumanMessage(content=f"Generate {generation_input.template_type} email template")],
                template_request=generation_input,
                current_agent="",
                progress=0,
                step="init",
                agent_results={},
                brand_guidelines=None,
                primary_product=None,
                related_products=[],
                assets={},
                copy_content={},
                design_tokens={},
                template_json=None,
                final_result=None
            )

            # Execute the workflow step by step with streaming updates
            state = initial_state

            # Supervisor step
            yield f"data: {json.dumps({'step': 'supervisor', 'agent': 'supervisor', 'message': agent_messages['supervisor'], 'progress': 10})}\n\n"
            await asyncio.sleep(0.5)

            state = supervisor_agent._supervisor_node(state)

            # Retriever step
            yield f"data: {json.dumps({'step': 'retriever', 'agent': 'retriever', 'message': agent_messages['retriever'], 'progress': 25})}\n\n"
            await asyncio.sleep(1)

            state = supervisor_agent._retriever_node(state)

            # Asset Curator step
            yield f"data: {json.dumps({'step': 'asset_curator', 'agent': 'asset_curator', 'message': agent_messages['asset_curator'], 'progress': 45})}\n\n"
            await asyncio.sleep(1)

            state = supervisor_agent._asset_curator_node(state)

            # Copywriter step
            yield f"data: {json.dumps({'step': 'copywriter', 'agent': 'copywriter', 'message': agent_messages['copywriter'], 'progress': 65})}\n\n"
            await asyncio.sleep(2)  # Longer for AI generation

            state = supervisor_agent._copywriter_node(state)

            # Template Layout step
            yield f"data: {json.dumps({'step': 'template_layout', 'agent': 'template_layout', 'message': agent_messages['template_layout'], 'progress': 80})}\n\n"
            await asyncio.sleep(1)

            state = supervisor_agent._template_layout_node(state)

            # Render step
            yield f"data: {json.dumps({'step': 'render', 'agent': 'render', 'message': agent_messages['render'], 'progress': 95})}\n\n"
            await asyncio.sleep(1)

            state = supervisor_agent._render_node(state)

            # Complete
            yield f"data: {json.dumps({'step': 'complete', 'agent': 'supervisor', 'message': 'Email generata con successo con LangGraph Multi-Agent!', 'progress': 100})}\n\n"

            # Final result
            result = state.get("final_result", {})
            if result.get("error"):
                yield f"data: {json.dumps({'step': 'error', 'message': f'Errore: {result[\"error\"]}', 'progress': 0})}\n\n"
            else:
                # Format result for frontend
                formatted_result = {
                    "success": True,
                    "jsonTemplate": result.get("jsonTemplate", {}),
                    "html": result.get("html", ""),
                    "mjml": result.get("mjml", ""),
                    "tokensVersion": result.get("tokensVersion", "1.0")
                }
                yield f"data: {json.dumps({'step': 'result', 'result': formatted_result})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'step': 'error', 'message': f'Errore LangGraph: {str(e)}', 'progress': 0})}\n\n"

    return StreamingResponse(
        generate_with_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )