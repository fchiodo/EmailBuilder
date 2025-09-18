"""Retriever Agent for product SKU correlation and brand guideline extraction."""

from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import json

from app.tools.product_tools import product_lookup_tool, related_products_tool
from app.tools.asset_tools import brand_guideline_extractor_tool

class RetrieverAgent:
    """Agent responsible for retrieving product information and extracting brand guidelines."""

    def __init__(self):
        try:
            import os
            self.llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.1,
                api_key=os.getenv("OPENAI_API_KEY", "dummy-key-for-testing")
            )
        except Exception:
            self.llm = None
            print("Warning: OpenAI not configured in RetrieverAgent, using fallback implementation")

    def retrieve_products(self, primary_sku: str) -> Dict[str, Any]:
        """
        Retrieve primary product and related products from CSV.

        Args:
            primary_sku: The main product SKU to look up

        Returns:
            Dictionary containing primary product and related products information
        """
        try:
            # Get primary product details
            primary_product = product_lookup_tool._run(primary_sku)

            if primary_product.get("error"):
                return {
                    "success": False,
                    "error": f"Failed to find primary product: {primary_product['error']}",
                    "primary_product": None,
                    "related_products": []
                }

            # Get related products
            related_products = related_products_tool._run(primary_sku, max_results=3)

            # Filter out any errors from related products
            valid_related_products = [
                product for product in related_products
                if not product.get("error")
            ]

            return {
                "success": True,
                "primary_product": primary_product,
                "related_products": valid_related_products,
                "recommendation_count": len(valid_related_products)
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Retriever agent error: {str(e)}",
                "primary_product": None,
                "related_products": []
            }

    def extract_brand_guidelines(self, file_content: str) -> Dict[str, Any]:
        """
        Extract brand guidelines from uploaded file content using OpenAI.

        Args:
            file_content: The content of the uploaded brand guideline file

        Returns:
            Dictionary containing extracted brand guidelines
        """
        try:
            # Use the brand guideline extractor tool
            guidelines = brand_guideline_extractor_tool._run(file_content)

            # Enhance the guidelines with additional context using LLM
            enhanced_guidelines = self._enhance_guidelines(guidelines, file_content)

            return {
                "success": True,
                "guidelines": enhanced_guidelines,
                "extraction_method": "openai_analysis"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Brand guideline extraction failed: {str(e)}",
                "guidelines": self._get_fallback_guidelines()
            }

    def _enhance_guidelines(self, initial_guidelines: Dict[str, Any], file_content: str) -> Dict[str, Any]:
        """Enhance extracted guidelines with additional AI analysis."""

        try:
            enhancement_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a brand analyst. Based on the initial guidelines and file content,
                provide enhanced insights for email template generation. Focus on:
                1. Email-specific tone recommendations
                2. Key messaging priorities for different email types (cart abandon, post-purchase, order confirmation)
                3. Visual style preferences that translate to email design
                4. Customer communication preferences

                Return your analysis as a JSON object with enhanced insights."""),
                ("human", f"""
                Initial guidelines: {json.dumps(initial_guidelines)}

                File content sample: {file_content[:1000]}

                Provide enhanced email-specific recommendations.""")
            ])

            chain = enhancement_prompt | self.llm
            response = chain.invoke({})

            try:
                enhanced_data = json.loads(response.content)

                # Merge with initial guidelines
                enhanced_guidelines = {
                    **initial_guidelines,
                    "email_specific": enhanced_data,
                    "enhanced": True
                }

                return enhanced_guidelines

            except json.JSONDecodeError:
                # If JSON parsing fails, add text insights
                return {
                    **initial_guidelines,
                    "additional_insights": response.content,
                    "enhanced": True
                }

        except Exception:
            # Return original guidelines if enhancement fails
            return initial_guidelines

    def _get_fallback_guidelines(self) -> Dict[str, Any]:
        """Provide fallback brand guidelines when extraction fails."""
        return {
            "tone": "professional and friendly",
            "colors": ["#007bff", "#6c757d"],
            "style": "clean and modern",
            "messaging": "customer-focused and trustworthy",
            "restrictions": "maintain professional appearance",
            "template_focus": "clear product presentation and strong call-to-action",
            "email_specific": {
                "cart_abandon": "create urgency while remaining helpful",
                "post_purchase": "express gratitude and build loyalty",
                "order_confirmation": "provide clear information and build trust"
            },
            "fallback": True
        }

    def correlate_products_context(self, primary_product: Dict[str, Any], related_products: List[Dict[str, Any]], template_type: str) -> Dict[str, Any]:
        """
        Provide context about product relationships for template generation.

        Args:
            primary_product: Main product information
            related_products: List of related products
            template_type: Type of email template being generated

        Returns:
            Dictionary with product correlation insights
        """
        try:
            context_prompt = ChatPromptTemplate.from_messages([
                ("system", f"""You are analyzing product relationships for a {template_type} email template.
                Provide insights about:
                1. How to position the primary product
                2. How to present related products
                3. Recommended messaging strategy
                4. Product presentation order

                Return as JSON with specific recommendations."""),
                ("human", f"""
                Primary product: {json.dumps(primary_product)}
                Related products: {json.dumps(related_products)}
                Template type: {template_type}

                Provide correlation insights for effective email presentation.""")
            ])

            chain = context_prompt | self.llm
            response = chain.invoke({})

            try:
                correlation_insights = json.loads(response.content)
            except:
                correlation_insights = {
                    "primary_positioning": "Feature prominently with clear value proposition",
                    "related_positioning": "Present as complementary recommendations",
                    "messaging_strategy": f"Focus on {template_type} context",
                    "presentation_order": "primary first, then related by relevance"
                }

            return {
                "success": True,
                "insights": correlation_insights,
                "product_count": {
                    "primary": 1,
                    "related": len(related_products)
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Product correlation analysis failed: {str(e)}",
                "insights": {
                    "primary_positioning": "Standard product presentation",
                    "related_positioning": "Standard recommendations section",
                    "messaging_strategy": "Generic email messaging",
                    "presentation_order": "Standard order"
                }
            }

# Create retriever instance
retriever_agent = RetrieverAgent()