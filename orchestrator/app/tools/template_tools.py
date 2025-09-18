"""Template and rendering tools for email generation."""

import json
from typing import Dict, Any
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from pathlib import Path
import httpx

class TokensLoaderInput(BaseModel):
    template_type: str = Field(..., description="Template type to load design tokens for")

class TokensLoaderTool(BaseTool):
    """Tool to load design tokens for a specific template type."""
    name: str = "tokens_loader"
    description: str = """
    Load design tokens (colors, fonts, spacing) for a specific template type.
    Returns styling configuration for consistent email design.
    """
    args_schema: type = TokensLoaderInput

    def _run(self, template_type: str) -> Dict[str, Any]:
        """Load design tokens from JSON file."""
        try:
            tokens_path = Path(f"../../tokens/{template_type}.json")
            if tokens_path.exists():
                with open(tokens_path, 'r') as f:
                    return json.load(f)
            else:
                # Fallback default tokens
                return {
                    "version": "1.0.0",
                    "colors": {
                        "primary": "#dc2626",
                        "secondary": "#64748b",
                        "surface": "#ffffff",
                        "background": "#f8fafc",
                        "text": "#1e293b",
                        "textSecondary": "#64748b"
                    },
                    "fonts": {
                        "primary": "Arial, sans-serif",
                        "heading": {
                            "size": "24px",
                            "weight": "700",
                            "lineHeight": "1.2"
                        },
                        "body": {
                            "size": "16px",
                            "weight": "400",
                            "lineHeight": "1.5"
                        }
                    },
                    "spacing": {
                        "xs": "4px",
                        "sm": "8px",
                        "md": "16px",
                        "lg": "24px",
                        "xl": "32px"
                    },
                    "radius": {
                        "card": "8px",
                        "button": "6px"
                    }
                }
        except Exception as e:
            return {"error": f"Failed to load tokens for {template_type}: {str(e)}"}

class MJMLRendererInput(BaseModel):
    mjml_content: str = Field(..., description="MJML content to render to HTML")

class MJMLRendererTool(BaseTool):
    """Tool to render MJML content to HTML using the renderer service."""
    name: str = "mjml_renderer"
    description: str = """
    Render MJML content to HTML using the external MJML renderer service.
    Returns the compiled HTML and any warnings.
    """
    args_schema: type = MJMLRendererInput

    def _run(self, mjml_content: str) -> Dict[str, Any]:
        """Render MJML to HTML via renderer service."""
        try:
            renderer_url = "http://localhost:3001"

            async def make_request():
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{renderer_url}/compile",
                        json={"mjml": mjml_content},
                        timeout=30.0
                    )
                    response.raise_for_status()
                    return response.json()

            # Run the async request
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(make_request())
            except RuntimeError:
                # Create new loop if none exists
                result = asyncio.run(make_request())

            return result

        except Exception as e:
            # Fallback: return basic HTML
            return {
                "html": f"<html><body><h1>Email Content</h1><p>MJML rendering failed: {str(e)}</p></body></html>",
                "warnings": [f"MJML rendering error: {str(e)}"],
                "mjml": mjml_content
            }

class TemplateValidatorInput(BaseModel):
    template_json: dict = Field(..., description="Email template JSON to validate")

class TemplateValidatorTool(BaseTool):
    """Tool to validate email template JSON structure."""
    name: str = "template_validator"
    description: str = """
    Validate that an email template JSON follows the correct schema structure.
    Checks for required fields and proper block structure.
    """
    args_schema: type = TemplateValidatorInput

    def _run(self, template_json: dict) -> Dict[str, Any]:
        """Validate template JSON structure."""
        try:
            errors = []
            warnings = []

            # Check required top-level fields
            required_fields = ["subject", "preheader", "blocks", "locale", "templateType"]
            for field in required_fields:
                if field not in template_json:
                    errors.append(f"Missing required field: {field}")

            # Validate blocks structure
            if "blocks" in template_json:
                blocks = template_json["blocks"]
                if not isinstance(blocks, list):
                    errors.append("Blocks must be a list")
                else:
                    valid_block_types = ["hero", "items", "recommendations", "footer"]
                    for i, block in enumerate(blocks):
                        if not isinstance(block, dict):
                            errors.append(f"Block {i} must be an object")
                            continue

                        if "type" not in block:
                            errors.append(f"Block {i} missing 'type' field")
                            continue

                        if block["type"] not in valid_block_types:
                            warnings.append(f"Block {i} has unknown type: {block['type']}")

                        # Type-specific validation
                        block_type = block["type"]
                        if block_type == "hero":
                            required = ["headline", "subcopy", "imageUrl"]
                            for field in required:
                                if field not in block:
                                    errors.append(f"Hero block {i} missing '{field}'")
                        elif block_type == "items":
                            if "items" not in block or not isinstance(block["items"], list):
                                errors.append(f"Items block {i} must have 'items' list")
                        elif block_type == "recommendations":
                            if "items" not in block or not isinstance(block["items"], list):
                                errors.append(f"Recommendations block {i} must have 'items' list")

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "summary": f"Validation {'passed' if len(errors) == 0 else 'failed'} with {len(errors)} errors and {len(warnings)} warnings"
            }

        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": [],
                "summary": f"Validation failed due to exception: {str(e)}"
            }

# Tool instances
tokens_loader_tool = TokensLoaderTool()
mjml_renderer_tool = MJMLRendererTool()
template_validator_tool = TemplateValidatorTool()