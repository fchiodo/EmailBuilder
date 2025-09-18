"""Copywriter Agent for generating email copy, subject lines, and microcopy."""

from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import json

class EmailCopy(BaseModel):
    """Structured output for email copy generation."""
    subject: str = Field(description="Email subject line")
    preheader: str = Field(description="Preheader text")
    headline: str = Field(description="Main headline")
    subcopy: str = Field(description="Supporting copy/subtitle")
    cta_primary: str = Field(description="Primary call-to-action text")
    cta_secondary: Optional[str] = Field(description="Secondary CTA text if needed")
    body_text: Optional[str] = Field(description="Additional body text if needed")
    footer_text: Optional[str] = Field(description="Footer copy")

class CopywriterAgent:
    """Agent responsible for generating all email copy and microcopy."""

    def __init__(self):
        try:
            import os
            self.llm = ChatOpenAI(
                model="gpt-4",
                temperature=0.7,
                api_key=os.getenv("OPENAI_API_KEY", "dummy-key-for-testing")
            )
        except Exception:
            self.llm = None
            print("Warning: OpenAI not configured in CopywriterAgent, using fallback implementation")
        self.output_parser = PydanticOutputParser(pydantic_object=EmailCopy)

    def generate_copy(
        self,
        template_type: str,
        primary_product: Dict[str, Any],
        brand_guidelines: Optional[Dict[str, Any]] = None,
        locale: str = "en"
    ) -> Dict[str, Any]:
        """
        Generate comprehensive copy for email template.

        Args:
            template_type: Type of email (cart_abandon, post_purchase, order_confirmation)
            primary_product: Primary product information
            brand_guidelines: Brand guidelines and tone
            locale: Target locale for copy

        Returns:
            Dictionary containing all generated copy elements
        """
        try:
            # Prepare context for copy generation
            copy_context = self._prepare_copy_context(
                template_type, primary_product, brand_guidelines, locale
            )

            # Generate structured copy
            generated_copy = self._generate_structured_copy(copy_context)

            # Generate microcopy elements
            microcopy = self._generate_microcopy(copy_context)

            # Optimize copy for template type
            optimized_copy = self._optimize_copy_for_template(
                generated_copy, microcopy, template_type, copy_context
            )

            return {
                "success": True,
                "copy": optimized_copy,
                "context": copy_context,
                "generation_method": "structured_ai"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Copy generation failed: {str(e)}",
                "copy": self._get_fallback_copy(template_type, primary_product)
            }

    def _prepare_copy_context(
        self,
        template_type: str,
        primary_product: Dict[str, Any],
        brand_guidelines: Optional[Dict[str, Any]],
        locale: str
    ) -> Dict[str, Any]:
        """Prepare context for copy generation."""

        # Extract product details
        product_name = primary_product.get("name", "Product")
        product_category = primary_product.get("category", "General")
        product_price = primary_product.get("price", "")
        product_description = primary_product.get("description", "")

        # Extract brand context
        brand_tone = "professional"
        brand_messaging = "quality and reliability"
        brand_restrictions = []

        if brand_guidelines:
            brand_tone = brand_guidelines.get("tone", "professional")
            brand_messaging = brand_guidelines.get("messaging", "quality and reliability")
            brand_restrictions = brand_guidelines.get("restrictions", [])

        # Template-specific context
        template_context = {
            "cart_abandon": {
                "urgency_level": "medium",
                "primary_goal": "conversion",
                "emotional_tone": "helpful urgency",
                "key_message": "complete your purchase"
            },
            "post_purchase": {
                "urgency_level": "low",
                "primary_goal": "engagement",
                "emotional_tone": "gratitude and excitement",
                "key_message": "thank you and next steps"
            },
            "order_confirmation": {
                "urgency_level": "low",
                "primary_goal": "information",
                "emotional_tone": "professional and reassuring",
                "key_message": "confirmation and details"
            }
        }

        return {
            "template_type": template_type,
            "template_context": template_context.get(template_type, template_context["cart_abandon"]),
            "product": {
                "name": product_name,
                "category": product_category,
                "price": product_price,
                "description": product_description
            },
            "brand": {
                "tone": brand_tone,
                "messaging": brand_messaging,
                "restrictions": brand_restrictions
            },
            "locale": locale,
            "target_audience": "customers"
        }

    def _generate_structured_copy(self, context: Dict[str, Any]) -> EmailCopy:
        """Generate structured copy using Pydantic output parser."""

        copy_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert email copywriter specializing in e-commerce emails.
            Generate compelling, brand-aligned copy that drives action while maintaining authenticity.

            Brand tone: {brand_tone}
            Brand messaging: {brand_messaging}
            Template type: {template_type}
            Template goal: {template_goal}
            Product: {product_name} ({product_category})

            Requirements:
            - Subject line: 30-50 characters, compelling and clear
            - Preheader: 80-100 characters, complements subject
            - Headline: Clear, benefit-focused, matches brand tone
            - Subcopy: Supporting details, create desire
            - Primary CTA: 2-4 words, action-oriented
            - Keep all copy concise and scannable
            - No CSS or formatting, just text content

            {format_instructions}"""),
            ("human", """Generate email copy for:
            Template: {template_type}
            Product: {product_name} - {product_description}
            Brand tone: {brand_tone}
            Goal: {template_goal}
            Emotional tone: {emotional_tone}""")
        ])

        formatted_prompt = copy_prompt.format_messages(
            brand_tone=context["brand"]["tone"],
            brand_messaging=context["brand"]["messaging"],
            template_type=context["template_type"],
            template_goal=context["template_context"]["primary_goal"],
            product_name=context["product"]["name"],
            product_category=context["product"]["category"],
            product_description=context["product"]["description"],
            emotional_tone=context["template_context"]["emotional_tone"],
            format_instructions=self.output_parser.get_format_instructions()
        )

        chain = copy_prompt | self.llm | self.output_parser
        response = chain.invoke(context)

        return response

    def _generate_microcopy(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate microcopy elements (buttons, labels, etc.)."""

        microcopy_prompt = ChatPromptTemplate.from_messages([
            ("system", """Generate microcopy elements for email template.
            Return as JSON with specific microcopy for buttons, links, and labels.

            Template type: {template_type}
            Brand tone: {brand_tone}

            Provide microcopy for:
            - view_product: Link text to view product details
            - add_to_cart: Add to cart button text
            - shop_now: General shopping CTA
            - learn_more: Learn more link text
            - unsubscribe: Unsubscribe link text
            - view_online: View online version text
            - contact_support: Contact support link
            - social_follow: Social media follow text"""),
            ("human", "Generate appropriate microcopy for {template_type} email with {brand_tone} tone.")
        ])

        chain = microcopy_prompt | self.llm
        response = chain.invoke(context)

        try:
            microcopy = json.loads(response.content)
        except:
            # Fallback microcopy
            microcopy = {
                "view_product": "View Product",
                "add_to_cart": "Add to Cart",
                "shop_now": "Shop Now",
                "learn_more": "Learn More",
                "unsubscribe": "Unsubscribe",
                "view_online": "View Online",
                "contact_support": "Contact Support",
                "social_follow": "Follow Us"
            }

        return microcopy

    def _optimize_copy_for_template(
        self,
        generated_copy: EmailCopy,
        microcopy: Dict[str, Any],
        template_type: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize copy specifically for template type and context."""

        # Template-specific optimizations
        optimizations = {
            "cart_abandon": {
                "subject_prefix": "",
                "urgency_words": ["Don't miss out", "Still interested", "Complete"],
                "primary_cta": microcopy.get("add_to_cart", "Complete Purchase")
            },
            "post_purchase": {
                "subject_prefix": "",
                "gratitude_words": ["Thank you", "Thanks", "Appreciate"],
                "primary_cta": microcopy.get("view_product", "View Order")
            },
            "order_confirmation": {
                "subject_prefix": "",
                "confirmation_words": ["Confirmed", "Processing", "Received"],
                "primary_cta": microcopy.get("view_product", "Track Order")
            }
        }

        template_optimization = optimizations.get(template_type, optimizations["cart_abandon"])

        # Apply optimizations
        optimized_copy = {
            "subject": generated_copy.subject,
            "preheader": generated_copy.preheader,
            "headline": generated_copy.headline,
            "subcopy": generated_copy.subcopy,
            "cta_primary": template_optimization["primary_cta"],
            "cta_secondary": generated_copy.cta_secondary,
            "body_text": generated_copy.body_text,
            "footer_text": generated_copy.footer_text,
            "microcopy": microcopy,
            "optimizations_applied": template_optimization
        }

        return optimized_copy

    def generate_variations(self, base_copy: Dict[str, Any], variation_count: int = 3) -> List[Dict[str, Any]]:
        """
        Generate copy variations for A/B testing.

        Args:
            base_copy: Base copy to create variations from
            variation_count: Number of variations to generate

        Returns:
            List of copy variations
        """
        try:
            variations_prompt = ChatPromptTemplate.from_messages([
                ("system", f"""Generate {variation_count} variations of the provided email copy.
                Each variation should:
                - Maintain the same core message and brand tone
                - Use different wording and approaches
                - Test different emotional appeals or urgency levels
                - Keep the same structure but vary the language

                Return as JSON array with each variation containing all copy elements."""),
                ("human", f"Create variations of this copy: {json.dumps(base_copy)}")
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
                return [base_copy]  # Return original if parsing fails

        except Exception as e:
            return [base_copy]  # Return original if generation fails

    def _get_fallback_copy(self, template_type: str, primary_product: Dict[str, Any]) -> Dict[str, Any]:
        """Provide fallback copy when generation fails."""

        product_name = primary_product.get("name", "Product")

        fallback_copy = {
            "cart_abandon": {
                "subject": f"Don't forget about {product_name}",
                "preheader": "Complete your purchase today",
                "headline": f"Still thinking about {product_name}?",
                "subcopy": "Complete your purchase now and enjoy fast shipping.",
                "cta_primary": "Complete Purchase",
                "cta_secondary": "View Product",
                "body_text": None,
                "footer_text": None
            },
            "post_purchase": {
                "subject": "Thank you for your purchase!",
                "preheader": "Your order is confirmed",
                "headline": f"Thanks for choosing {product_name}!",
                "subcopy": "Your order is being processed and will ship soon.",
                "cta_primary": "Track Order",
                "cta_secondary": "Shop More",
                "body_text": None,
                "footer_text": None
            },
            "order_confirmation": {
                "subject": "Order confirmed - We're preparing your items",
                "preheader": "Order details inside",
                "headline": "Your order is confirmed!",
                "subcopy": f"We're preparing {product_name} for shipment.",
                "cta_primary": "View Order Details",
                "cta_secondary": "Contact Support",
                "body_text": None,
                "footer_text": None
            }
        }

        copy = fallback_copy.get(template_type, fallback_copy["cart_abandon"])
        copy["microcopy"] = {
            "view_product": "View Product",
            "add_to_cart": "Add to Cart",
            "shop_now": "Shop Now",
            "learn_more": "Learn More",
            "unsubscribe": "Unsubscribe",
            "view_online": "View Online",
            "contact_support": "Contact Support",
            "social_follow": "Follow Us"
        }
        copy["fallback"] = True

        return copy

# Create copywriter instance
copywriter_agent = CopywriterAgent()