"""Asset selection and curation tools for images and design elements."""

import random
from typing import List, Dict, Any
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

class AssetSelectorInput(BaseModel):
    template_type: str = Field(..., description="Template type (cart_abandon, post_purchase, order_confirmation)")
    category: str = Field(default="general", description="Category for asset selection (outdoor, fashion, tech, etc.)")
    asset_type: str = Field(..., description="Type of asset needed: hero, grid, or product")
    count: int = Field(default=1, description="Number of assets to return")

class AssetSelectorTool(BaseTool):
    """Tool to select appropriate images for different email sections."""
    name: str = "asset_selector"
    description: str = """
    Select appropriate images for email templates based on template type and category.
    Returns curated image URLs for hero sections, grids, or product placements.
    """
    args_schema: type = AssetSelectorInput

    def _run(self, template_type: str, category: str = "general", asset_type: str = "hero", count: int = 1) -> List[Dict[str, Any]]:
        """Select assets based on template type and requirements."""

        # Hero images - large, impactful images for main sections
        hero_images = {
            "outdoor": [
                "https://images.unsplash.com/photo-1551524164-6cf96ac925fb?w=600&h=300&fit=crop&q=80",
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=600&h=300&fit=crop&q=80",
                "https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?w=600&h=300&fit=crop&q=80",
                "https://images.unsplash.com/photo-1537225228614-56cc3556d7ed?w=600&h=300&fit=crop&q=80"
            ],
            "fashion": [
                "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=600&h=300&fit=crop&q=80",
                "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=600&h=300&fit=crop&q=80",
                "https://images.unsplash.com/photo-1558769132-cb1aea458c5e?w=600&h=300&fit=crop&q=80"
            ],
            "general": [
                "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=600&h=300&fit=crop&q=80",
                "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=600&h=300&fit=crop&q=80",
                "https://images.unsplash.com/photo-1487014679447-9f8336841d58?w=600&h=300&fit=crop&q=80"
            ]
        }

        # Grid images - smaller images for product grids or decorative elements
        grid_images = {
            "outdoor": [
                "https://images.unsplash.com/photo-1544966503-7cc5ac882d5f?w=300&h=200&fit=crop&q=80",
                "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=300&h=200&fit=crop&q=80",
                "https://images.unsplash.com/photo-1586350977771-b3b0abd50c82?w=300&h=200&fit=crop&q=80"
            ],
            "fashion": [
                "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?w=300&h=200&fit=crop&q=80",
                "https://images.unsplash.com/photo-1467043237213-65f2da53396f?w=300&h=200&fit=crop&q=80",
                "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=300&h=200&fit=crop&q=80"
            ],
            "general": [
                "https://images.unsplash.com/photo-1560472354-b33ff0c44a43?w=300&h=200&fit=crop&q=80",
                "https://images.unsplash.com/photo-1556228453-efd6c1ff04f6?w=300&h=200&fit=crop&q=80",
                "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=300&h=200&fit=crop&q=80"
            ]
        }

        # Product placeholder images - for when specific product images aren't available
        product_placeholders = [
            "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=200&h=200&fit=crop&q=80",
            "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=200&h=200&fit=crop&q=80",
            "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=200&h=200&fit=crop&q=80",
            "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=200&h=200&fit=crop&q=80"
        ]

        # Template-specific adjustments
        template_context = {
            "cart_abandon": {"urgency": True, "focus": "product"},
            "post_purchase": {"celebration": True, "focus": "recommendations"},
            "order_confirmation": {"confirmation": True, "focus": "trust"}
        }

        # Select appropriate image pool
        if asset_type == "hero":
            image_pool = hero_images.get(category, hero_images["general"])
        elif asset_type == "grid":
            image_pool = grid_images.get(category, grid_images["general"])
        elif asset_type == "product":
            image_pool = product_placeholders
        else:
            image_pool = hero_images.get(category, hero_images["general"])

        # Select images
        selected_images = random.sample(image_pool, min(count, len(image_pool)))

        results = []
        for i, image_url in enumerate(selected_images):
            results.append({
                "url": image_url,
                "type": asset_type,
                "category": category,
                "template_type": template_type,
                "alt_text": f"{asset_type.title()} image for {template_type} email",
                "priority": i + 1
            })

        return results

class BrandGuidelineExtractorInput(BaseModel):
    file_content: str = Field(..., description="Content of uploaded brand guideline file")

class BrandGuidelineExtractorTool(BaseTool):
    """Tool to extract brand guidelines from uploaded files using OpenAI."""
    name: str = "brand_guideline_extractor"
    description: str = """
    Extract brand guidelines, style preferences, and design rules from uploaded files.
    Uses AI to analyze content and return structured brand information.
    """
    args_schema: type = BrandGuidelineExtractorInput

    def _run(self, file_content: str) -> Dict[str, Any]:
        """Extract brand guidelines from file content using OpenAI."""
        from langchain_openai import ChatOpenAI
        from langchain.prompts import ChatPromptTemplate
        import json

        try:
            llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.1
            )

            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a brand guideline analyzer. Extract key brand information from the provided content and return it as a JSON object with these fields:
                - tone: brand tone and voice (professional, casual, friendly, etc.)
                - colors: primary and secondary brand colors if mentioned
                - style: visual style preferences (modern, classic, minimal, etc.)
                - messaging: key messaging themes or values
                - restrictions: any specific restrictions or requirements
                - template_focus: what should be emphasized in email templates

                If the content doesn't contain brand guidelines, analyze the overall style and tone to infer brand characteristics."""),
                ("human", "Analyze this content for brand guidelines:\n\n{content}")
            ])

            chain = prompt | llm
            response = chain.invoke({"content": file_content[:3000]})  # Limit content length

            # Try to parse as JSON, fallback to structured text
            try:
                guidelines = json.loads(response.content)
            except:
                # Fallback: create structured response from text
                guidelines = {
                    "tone": "professional",
                    "colors": ["primary", "secondary"],
                    "style": "modern",
                    "messaging": "quality and reliability",
                    "restrictions": "none specified",
                    "template_focus": "product quality and brand trust",
                    "extracted_text": response.content
                }

            return guidelines

        except Exception as e:
            # Fallback: return basic brand guidelines
            return {
                "tone": "professional",
                "colors": ["brand primary", "brand secondary"],
                "style": "clean and modern",
                "messaging": "quality products and customer focus",
                "restrictions": "maintain brand consistency",
                "template_focus": "highlight product value and brand trust",
                "error": f"Could not fully analyze guidelines: {str(e)}"
            }

# Tool instances
asset_selector_tool = AssetSelectorTool()
brand_guideline_extractor_tool = BrandGuidelineExtractorTool()