"""Template/Layout Agent for composing email JSON templates with structured output."""

from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import json

from app.tools.template_tools import tokens_loader_tool, template_validator_tool

class EmailBlock(BaseModel):
    """Base email block structure."""
    type: str = Field(description="Block type (hero, items, recommendations, footer)")

class HeroBlock(EmailBlock):
    """Hero block structure."""
    type: str = Field(default="hero")
    headline: str = Field(description="Main headline")
    subcopy: str = Field(description="Supporting copy")
    imageUrl: str = Field(description="Hero image URL")
    ctaLabel: str = Field(description="Call-to-action button text")
    ctaUrl: str = Field(description="Call-to-action URL")

class ItemBlock(BaseModel):
    """Individual item structure."""
    name: str = Field(description="Product name")
    sku: str = Field(description="Product SKU")
    price: float = Field(description="Product price")
    imageUrl: str = Field(description="Product image URL")
    description: str = Field(description="Product description")

class ItemsBlock(EmailBlock):
    """Items block structure."""
    type: str = Field(default="items")
    title: str = Field(description="Section title")
    items: List[ItemBlock] = Field(description="List of items")

class RecommendationsBlock(EmailBlock):
    """Recommendations block structure."""
    type: str = Field(default="recommendations")
    title: str = Field(description="Recommendations section title")
    items: List[ItemBlock] = Field(description="List of recommended items")

class FooterBlock(EmailBlock):
    """Footer block structure."""
    type: str = Field(default="footer")
    companyName: str = Field(description="Company name")
    address: str = Field(description="Company address")
    unsubscribeUrl: str = Field(description="Unsubscribe URL")
    socialLinks: List[Dict[str, str]] = Field(description="Social media links")

class EmailTemplate(BaseModel):
    """Complete email template structure."""
    subject: str = Field(description="Email subject line")
    preheader: str = Field(description="Email preheader text")
    locale: str = Field(description="Email locale")
    templateType: str = Field(description="Template type")
    blocks: List[Dict[str, Any]] = Field(description="Email content blocks")

class TemplateLayoutAgent:
    """Agent responsible for composing structured email templates."""

    def __init__(self):
        try:
            import os
            self.llm = ChatOpenAI(
                model="gpt-4",
                temperature=0.1,
                api_key=os.getenv("OPENAI_API_KEY", "dummy-key-for-testing")
            )
        except Exception:
            self.llm = None
            print("Warning: OpenAI not configured in TemplateLayoutAgent, using fallback implementation")
        self.output_parser = PydanticOutputParser(pydantic_object=EmailTemplate)

    def compose_template(
        self,
        template_type: str,
        copy_data: Dict[str, Any],
        product_data: Dict[str, Any],
        asset_data: Dict[str, Any],
        locale: str = "en"
    ) -> Dict[str, Any]:
        """
        Compose complete email template JSON using structured output.

        Args:
            template_type: Type of email template
            copy_data: Generated copy from copywriter agent
            product_data: Product information from retriever agent
            asset_data: Asset information from curator agent
            locale: Target locale

        Returns:
            Dictionary containing composed template and validation results
        """
        try:
            # Load design tokens for template type
            design_tokens = tokens_loader_tool._run(template_type)

            # Compose template structure
            template_json = self._compose_structured_template(
                template_type, copy_data, product_data, asset_data, locale, design_tokens
            )

            # Validate template structure
            validation_result = template_validator_tool._run(template_json)

            # Apply design tokens and optimizations
            optimized_template = self._apply_design_optimizations(
                template_json, design_tokens, template_type
            )

            return {
                "success": True,
                "template": optimized_template,
                "design_tokens": design_tokens,
                "validation": validation_result,
                "composition_method": "structured_output"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Template composition failed: {str(e)}",
                "template": self._get_fallback_template(template_type, copy_data, product_data)
            }

    def _compose_structured_template(
        self,
        template_type: str,
        copy_data: Dict[str, Any],
        product_data: Dict[str, Any],
        asset_data: Dict[str, Any],
        locale: str,
        design_tokens: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compose template using structured approach."""

        # Initialize template structure
        template = {
            "subject": copy_data.get("subject", "Email Subject"),
            "preheader": copy_data.get("preheader", "Email preview text"),
            "locale": locale,
            "templateType": template_type,
            "blocks": []
        }

        # Compose blocks based on template type and available data
        blocks = self._compose_blocks(template_type, copy_data, product_data, asset_data)
        template["blocks"] = blocks

        return template

    def _compose_blocks(
        self,
        template_type: str,
        copy_data: Dict[str, Any],
        product_data: Dict[str, Any],
        asset_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Compose email blocks based on data and template type."""

        blocks = []

        # Hero block - always included
        hero_block = self._create_hero_block(copy_data, asset_data)
        if hero_block:
            blocks.append(hero_block)

        # Items block - primary product
        if product_data.get("primary_product") and not product_data["primary_product"].get("error"):
            items_block = self._create_items_block(product_data["primary_product"], template_type)
            if items_block:
                blocks.append(items_block)

        # Recommendations block - related products
        if product_data.get("related_products") and len(product_data["related_products"]) > 0:
            recommendations_block = self._create_recommendations_block(
                product_data["related_products"], template_type
            )
            if recommendations_block:
                blocks.append(recommendations_block)

        # Footer block - always included
        footer_block = self._create_footer_block(template_type)
        blocks.append(footer_block)

        return blocks

    def _create_hero_block(self, copy_data: Dict[str, Any], asset_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create hero block from copy and asset data."""

        hero_asset = None
        if asset_data.get("assets") and asset_data["assets"].get("hero"):
            hero_asset = asset_data["assets"]["hero"]

        return {
            "type": "hero",
            "headline": copy_data.get("headline", "Welcome"),
            "subcopy": copy_data.get("subcopy", "Discover our products"),
            "imageUrl": hero_asset.get("url", "") if hero_asset else "",
            "ctaLabel": copy_data.get("cta_primary", "Shop Now"),
            "ctaUrl": "#"
        }

    def _create_items_block(self, primary_product: Dict[str, Any], template_type: str) -> Optional[Dict[str, Any]]:
        """Create items block for primary product."""

        # Determine section title based on template type
        title_map = {
            "cart_abandon": "Your Item",
            "post_purchase": "Your Purchase",
            "order_confirmation": "Your Order"
        }

        return {
            "type": "items",
            "title": title_map.get(template_type, "Featured Item"),
            "items": [{
                "name": primary_product.get("name", "Product"),
                "sku": primary_product.get("sku", ""),
                "price": primary_product.get("price", 0),
                "imageUrl": primary_product.get("image_placeholder", ""),
                "description": primary_product.get("description", "")
            }]
        }

    def _create_recommendations_block(self, related_products: List[Dict[str, Any]], template_type: str) -> Optional[Dict[str, Any]]:
        """Create recommendations block from related products."""

        # Filter out products with errors
        valid_products = [p for p in related_products if not p.get("error")]

        if not valid_products:
            return None

        # Convert products to items format
        items = []
        for product in valid_products:
            items.append({
                "name": product.get("name", "Product"),
                "sku": product.get("sku", ""),
                "price": product.get("price", 0),
                "imageUrl": product.get("image_placeholder", ""),
                "description": product.get("description", "")
            })

        # Determine title based on template type
        title_map = {
            "cart_abandon": "Complete your look",
            "post_purchase": "You might also like",
            "order_confirmation": "Recommended for you"
        }

        return {
            "type": "recommendations",
            "title": title_map.get(template_type, "Recommendations"),
            "items": items
        }

    def _create_footer_block(self, template_type: str) -> Dict[str, Any]:
        """Create footer block."""

        return {
            "type": "footer",
            "companyName": "Your Company",
            "address": "123 Main St, City, State 12345",
            "unsubscribeUrl": "#unsubscribe",
            "socialLinks": [
                {"platform": "facebook", "url": "#"},
                {"platform": "instagram", "url": "#"},
                {"platform": "twitter", "url": "#"}
            ]
        }

    def _apply_design_optimizations(
        self,
        template_json: Dict[str, Any],
        design_tokens: Dict[str, Any],
        template_type: str
    ) -> Dict[str, Any]:
        """Apply design tokens and template-specific optimizations."""

        try:
            # Create optimization prompt
            optimization_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an email template optimizer. Apply design tokens and template-specific
                optimizations to improve the email structure and effectiveness.

                Design tokens available: {design_tokens}
                Template type: {template_type}

                Optimize for:
                1. Visual hierarchy and spacing
                2. Template-specific best practices
                3. Mobile responsiveness considerations
                4. Brand consistency

                Return the optimized template JSON with design considerations applied."""),
                ("human", f"Optimize this template: {json.dumps(template_json)}")
            ])

            chain = optimization_prompt | self.llm
            response = chain.invoke({
                "design_tokens": json.dumps(design_tokens),
                "template_type": template_type
            })

            try:
                optimized_template = json.loads(response.content)
                return optimized_template
            except:
                # Return original if parsing fails
                return template_json

        except Exception:
            # Return original template if optimization fails
            return template_json

    def generate_layout_variations(self, base_template: Dict[str, Any], variation_count: int = 2) -> List[Dict[str, Any]]:
        """
        Generate layout variations for A/B testing.

        Args:
            base_template: Base template to create variations from
            variation_count: Number of variations to generate

        Returns:
            List of template variations with different layouts
        """
        try:
            variations_prompt = ChatPromptTemplate.from_messages([
                ("system", f"""Generate {variation_count} layout variations of the email template.
                Each variation should:
                - Keep the same content but rearrange block order
                - Test different visual hierarchies
                - Maintain template effectiveness
                - Follow email design best practices

                Return as JSON array with each variation."""),
                ("human", f"Create layout variations: {json.dumps(base_template)}")
            ])

            chain = variations_prompt | self.llm
            response = chain.invoke({})

            try:
                variations = json.loads(response.content)
                if isinstance(variations, list):
                    return variations[:variation_count]
                else:
                    return [variations]
            except:
                return [base_template]

        except Exception:
            return [base_template]

    def _get_fallback_template(
        self,
        template_type: str,
        copy_data: Dict[str, Any],
        product_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Provide fallback template when composition fails."""

        fallback_template = {
            "subject": copy_data.get("subject", "Email Subject"),
            "preheader": copy_data.get("preheader", "Email preview"),
            "locale": "en",
            "templateType": template_type,
            "blocks": [
                {
                    "type": "hero",
                    "headline": copy_data.get("headline", "Welcome"),
                    "subcopy": copy_data.get("subcopy", "Discover our products"),
                    "imageUrl": "",
                    "ctaLabel": copy_data.get("cta_primary", "Shop Now"),
                    "ctaUrl": "#"
                },
                {
                    "type": "footer",
                    "companyName": "Your Company",
                    "address": "123 Main St, City, State 12345",
                    "unsubscribeUrl": "#unsubscribe",
                    "socialLinks": []
                }
            ],
            "fallback": True
        }

        # Add items block if primary product exists
        if product_data.get("primary_product") and not product_data["primary_product"].get("error"):
            items_block = {
                "type": "items",
                "title": "Featured Item",
                "items": [{
                    "name": product_data["primary_product"].get("name", "Product"),
                    "sku": product_data["primary_product"].get("sku", ""),
                    "price": product_data["primary_product"].get("price", 0),
                    "imageUrl": product_data["primary_product"].get("image_placeholder", ""),
                    "description": product_data["primary_product"].get("description", "")
                }]
            }
            fallback_template["blocks"].insert(-1, items_block)

        return fallback_template

# Create template layout instance
template_layout_agent = TemplateLayoutAgent()