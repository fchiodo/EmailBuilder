"""Asset Curator Agent for intelligent image selection and classification."""

from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import json

from app.tools.asset_tools import asset_selector_tool

class AssetCuratorAgent:
    """Agent responsible for selecting and curating images for email templates."""

    def __init__(self):
        try:
            import os
            self.llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.3,
                api_key=os.getenv("OPENAI_API_KEY", "dummy-key-for-testing")
            )
        except Exception:
            self.llm = None
            print("Warning: OpenAI not configured in AssetCuratorAgent, using fallback implementation")

    def curate_assets(self, template_type: str, category: str = "general", brand_guidelines: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Curate assets for email template based on type, category, and brand guidelines.

        Args:
            template_type: Type of email (cart_abandon, post_purchase, order_confirmation)
            category: Product category (outdoor, fashion, tech, general)
            brand_guidelines: Optional brand guidelines to influence selection

        Returns:
            Dictionary containing curated assets for different sections
        """
        try:
            # Determine asset requirements based on template type
            asset_requirements = self._get_asset_requirements(template_type, brand_guidelines)

            # Select hero image
            hero_assets = asset_selector_tool._run(
                template_type=template_type,
                category=category,
                asset_type="hero",
                count=asset_requirements["hero_count"]
            )

            # Select grid/decorative images
            grid_assets = asset_selector_tool._run(
                template_type=template_type,
                category=category,
                asset_type="grid",
                count=asset_requirements["grid_count"]
            )

            # Get product placeholder assets if needed
            product_assets = []
            if asset_requirements["product_placeholders"]:
                product_assets = asset_selector_tool._run(
                    template_type=template_type,
                    category=category,
                    asset_type="product",
                    count=asset_requirements["product_count"]
                )

            # Analyze and optimize asset selection
            optimized_selection = self._optimize_asset_selection(
                hero_assets,
                grid_assets,
                product_assets,
                template_type,
                brand_guidelines
            )

            return {
                "success": True,
                "assets": {
                    "hero": optimized_selection["hero"],
                    "grid": optimized_selection["grid"],
                    "products": optimized_selection["products"]
                },
                "metadata": {
                    "template_type": template_type,
                    "category": category,
                    "selection_strategy": optimized_selection["strategy"],
                    "brand_alignment": optimized_selection["brand_alignment"]
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Asset curation failed: {str(e)}",
                "assets": self._get_fallback_assets(template_type, category)
            }

    def _get_asset_requirements(self, template_type: str, brand_guidelines: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Determine asset requirements based on template type and brand guidelines."""

        base_requirements = {
            "cart_abandon": {
                "hero_count": 1,
                "grid_count": 1,
                "product_placeholders": True,
                "product_count": 2,
                "focus": "urgency_and_product"
            },
            "post_purchase": {
                "hero_count": 1,
                "grid_count": 2,
                "product_placeholders": True,
                "product_count": 3,
                "focus": "celebration_and_recommendations"
            },
            "order_confirmation": {
                "hero_count": 1,
                "grid_count": 1,
                "product_placeholders": True,
                "product_count": 1,
                "focus": "trust_and_confirmation"
            }
        }

        requirements = base_requirements.get(template_type, base_requirements["cart_abandon"])

        # Adjust based on brand guidelines
        if brand_guidelines:
            style = brand_guidelines.get("style", "modern")
            if "minimal" in style.lower():
                requirements["grid_count"] = max(1, requirements["grid_count"] - 1)
            elif "rich" in style.lower() or "luxury" in style.lower():
                requirements["grid_count"] = requirements["grid_count"] + 1

        return requirements

    def _optimize_asset_selection(
        self,
        hero_assets: List[Dict[str, Any]],
        grid_assets: List[Dict[str, Any]],
        product_assets: List[Dict[str, Any]],
        template_type: str,
        brand_guidelines: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Optimize asset selection using AI analysis."""

        try:
            # Prepare context for optimization
            context = {
                "template_type": template_type,
                "hero_options": len(hero_assets),
                "grid_options": len(grid_assets),
                "product_options": len(product_assets),
                "brand_style": brand_guidelines.get("style", "modern") if brand_guidelines else "modern",
                "brand_tone": brand_guidelines.get("tone", "professional") if brand_guidelines else "professional"
            }

            optimization_prompt = ChatPromptTemplate.from_messages([
                ("system", f"""You are an email design specialist optimizing image selection.
                Based on the template type and brand guidelines, select the best assets and provide reasoning.

                Template type: {template_type}
                Brand context: {context['brand_style']} style, {context['brand_tone']} tone

                Provide selection strategy as JSON with:
                - hero_selection: index of best hero image (0-based)
                - grid_selection: list of indices for grid images
                - product_selection: list of indices for product images
                - strategy_reasoning: explanation of choices
                - brand_alignment_score: 1-10 rating of brand alignment"""),
                ("human", f"""
                Available assets context: {json.dumps(context)}

                Select optimal assets for maximum email effectiveness.""")
            ])

            chain = optimization_prompt | self.llm
            response = chain.invoke({})

            try:
                optimization = json.loads(response.content)
            except:
                # Fallback to simple selection
                optimization = {
                    "hero_selection": 0,
                    "grid_selection": list(range(len(grid_assets))),
                    "product_selection": list(range(len(product_assets))),
                    "strategy_reasoning": "Default selection strategy",
                    "brand_alignment_score": 7
                }

            # Apply optimization
            selected_hero = hero_assets[optimization.get("hero_selection", 0)] if hero_assets else None

            selected_grid = []
            for idx in optimization.get("grid_selection", []):
                if idx < len(grid_assets):
                    selected_grid.append(grid_assets[idx])

            selected_products = []
            for idx in optimization.get("product_selection", []):
                if idx < len(product_assets):
                    selected_products.append(product_assets[idx])

            return {
                "hero": selected_hero,
                "grid": selected_grid,
                "products": selected_products,
                "strategy": optimization.get("strategy_reasoning", "Standard selection"),
                "brand_alignment": optimization.get("brand_alignment_score", 7)
            }

        except Exception as e:
            # Fallback to simple selection
            return {
                "hero": hero_assets[0] if hero_assets else None,
                "grid": grid_assets,
                "products": product_assets,
                "strategy": f"Fallback selection due to optimization error: {str(e)}",
                "brand_alignment": 5
            }

    def classify_image_suitability(self, image_url: str, template_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify image suitability for specific template context.

        Args:
            image_url: URL of the image to classify
            template_context: Context including template type, section, brand guidelines

        Returns:
            Classification results with suitability score and recommendations
        """
        try:
            classification_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an image classification specialist for email marketing.
                Analyze the image URL and context to determine suitability.

                Provide classification as JSON with:
                - suitability_score: 1-10 rating
                - recommended_usage: hero/grid/product/decorative
                - style_match: how well it matches the brand style
                - emotional_impact: expected emotional response
                - accessibility_notes: any accessibility considerations"""),
                ("human", f"""
                Image URL: {image_url}
                Context: {json.dumps(template_context)}

                Classify this image for email template usage.""")
            ])

            chain = classification_prompt | self.llm
            response = chain.invoke({})

            try:
                classification = json.loads(response.content)
            except:
                classification = {
                    "suitability_score": 7,
                    "recommended_usage": "general",
                    "style_match": "good",
                    "emotional_impact": "neutral positive",
                    "accessibility_notes": "ensure alt text is provided"
                }

            return {
                "success": True,
                "classification": classification,
                "image_url": image_url
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Image classification failed: {str(e)}",
                "classification": {
                    "suitability_score": 5,
                    "recommended_usage": "general",
                    "style_match": "unknown",
                    "emotional_impact": "neutral",
                    "accessibility_notes": "manual review needed"
                }
            }

    def _get_fallback_assets(self, template_type: str, category: str) -> Dict[str, Any]:
        """Provide fallback assets when curation fails."""
        return {
            "hero": {
                "url": "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=600&h=300&fit=crop&q=80",
                "type": "hero",
                "category": category,
                "template_type": template_type,
                "alt_text": f"Hero image for {template_type} email",
                "priority": 1,
                "fallback": True
            },
            "grid": [
                {
                    "url": "https://images.unsplash.com/photo-1560472354-b33ff0c44a43?w=300&h=200&fit=crop&q=80",
                    "type": "grid",
                    "category": category,
                    "template_type": template_type,
                    "alt_text": "Decorative image",
                    "priority": 1,
                    "fallback": True
                }
            ],
            "products": []
        }

# Create asset curator instance
asset_curator_agent = AssetCuratorAgent()