"""Supervisor/Router Agent for orchestrating the multi-agent email generation workflow using LangGraph."""

from typing import Dict, Any, List, Optional, Union
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict, Annotated
from pydantic import BaseModel, Field
import json
import logging
import os

from app.tools.product_tools import product_lookup_tool, related_products_tool
from app.tools.asset_tools import asset_selector_tool, brand_guideline_extractor_tool
from app.tools.template_tools import tokens_loader_tool, mjml_renderer_tool, template_validator_tool

logger = logging.getLogger(__name__)

class EmailGenerationInput(BaseModel):
    """Input schema for email generation request."""
    template_type: str = Field(..., description="Type of email template (cart_abandon, post_purchase, order_confirmation)")
    locale: str = Field(default="en", description="Locale for the email")
    primary_sku: str = Field(..., description="Primary product SKU")
    uploaded_file_content: Optional[str] = Field(None, description="Content of uploaded brand guideline file")
    category: str = Field(default="general", description="Product category for asset selection")

class AgentState(TypedDict):
    """State shared across all agents in the workflow."""
    messages: Annotated[List[Union[HumanMessage, AIMessage]], add_messages]
    template_request: EmailGenerationInput
    current_agent: str
    progress: int
    step: str
    agent_results: Dict[str, Any]
    brand_guidelines: Optional[Dict[str, Any]]
    primary_product: Optional[Dict[str, Any]]
    related_products: List[Dict[str, Any]]
    assets: Dict[str, Any]
    copy_content: Dict[str, Any]
    design_tokens: Dict[str, Any]
    template_json: Optional[Dict[str, Any]]
    final_result: Optional[Dict[str, Any]]

class SupervisorAgent:
    """Supervisor agent that orchestrates the email generation workflow using LangGraph."""

    def __init__(self):
        try:
            self.llm = ChatOpenAI(
                model="gpt-4",
                temperature=0.1,
                api_key=os.getenv("OPENAI_API_KEY", "dummy-key-for-testing")
            )
        except Exception:
            self.llm = None
            print("Warning: OpenAI not configured, using fallback implementation")

        # Create the multi-agent workflow
        self.workflow = self._create_workflow()

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph multi-agent workflow."""
        workflow = StateGraph(AgentState)

        # Add nodes for each agent
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("retriever", self._retriever_node)
        workflow.add_node("asset_curator", self._asset_curator_node)
        workflow.add_node("copywriter", self._copywriter_node)
        workflow.add_node("template_layout", self._template_layout_node)
        workflow.add_node("render", self._render_node)

        # Define the workflow edges
        workflow.add_edge(START, "supervisor")
        workflow.add_edge("supervisor", "retriever")
        workflow.add_edge("retriever", "asset_curator")
        workflow.add_edge("asset_curator", "copywriter")
        workflow.add_edge("copywriter", "template_layout")
        workflow.add_edge("template_layout", "render")
        workflow.add_edge("render", END)

        return workflow.compile()

    async def process_template_request(self, input_data: EmailGenerationInput) -> Dict[str, Any]:
        """Process a template request through the multi-agent workflow."""
        logger.info(f"Processing template request: {input_data.template_type}")

        # Initialize state
        initial_state = AgentState(
            messages=[HumanMessage(content=f"Generate {input_data.template_type} email template")],
            template_request=input_data,
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

        try:
            # Run the workflow
            final_state = await self.workflow.ainvoke(initial_state)
            return final_state.get("final_result", {})
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return {"error": f"Workflow failed: {str(e)}"}

    def _supervisor_node(self, state: AgentState) -> AgentState:
        """Supervisor node that analyzes input and initializes workflow."""
        logger.info("Supervisor: Analyzing template request")

        state["current_agent"] = "supervisor"
        state["progress"] = 10
        state["step"] = "supervisor"
        state["agent_results"] = {}

        template_request = state["template_request"]
        analysis_message = f"Analyzing {template_request.template_type} template request for SKU: {template_request.primary_sku}"

        state["messages"].append(AIMessage(content=analysis_message))
        state["agent_results"]["supervisor"] = {
            "status": "completed",
            "analysis": analysis_message
        }

        return state

    def _retriever_node(self, state: AgentState) -> AgentState:
        """Retriever node that processes products and brand guidelines."""
        logger.info("Retriever: Processing SKUs and brand guidelines")

        state["current_agent"] = "retriever"
        state["progress"] = 25
        state["step"] = "retriever"

        template_request = state["template_request"]

        # Retrieve primary product
        try:
            primary_product = product_lookup_tool._run(template_request.primary_sku)
            state["primary_product"] = primary_product if not primary_product.get("error") else None
        except Exception as e:
            logger.error(f"Error retrieving primary product: {e}")
            state["primary_product"] = None

        # Retrieve related products
        try:
            related_products = related_products_tool._run(template_request.primary_sku, max_results=3)
            state["related_products"] = related_products if not isinstance(related_products, dict) or not related_products.get("error") else []
        except Exception as e:
            logger.error(f"Error retrieving related products: {e}")
            state["related_products"] = []

        # Extract brand guidelines if provided
        if template_request.uploaded_file_content:
            try:
                brand_guidelines = brand_guideline_extractor_tool._run(template_request.uploaded_file_content)
                state["brand_guidelines"] = brand_guidelines
            except Exception as e:
                logger.error(f"Error extracting brand guidelines: {e}")
                state["brand_guidelines"] = None

        retriever_message = f"Retrieved product data and processed brand guidelines"
        state["messages"].append(AIMessage(content=retriever_message))
        state["agent_results"]["retriever"] = {
            "status": "completed",
            "has_primary_product": bool(state["primary_product"]),
            "related_products_count": len(state["related_products"]),
            "has_brand_guidelines": bool(state["brand_guidelines"])
        }

        return state

    def _asset_curator_node(self, state: AgentState) -> AgentState:
        """Asset Curator node that selects appropriate images."""
        logger.info("Asset Curator: Selecting images for template")

        state["current_agent"] = "asset_curator"
        state["progress"] = 45
        state["step"] = "asset_curator"

        template_request = state["template_request"]

        try:
            # Select hero image
            hero_assets = asset_selector_tool._run(
                template_type=template_request.template_type,
                category=template_request.category,
                asset_type="hero",
                count=1
            )

            # Select grid images
            grid_assets = asset_selector_tool._run(
                template_type=template_request.template_type,
                category=template_request.category,
                asset_type="grid",
                count=2
            )

            state["assets"] = {
                "hero": hero_assets[0] if hero_assets else None,
                "grid": grid_assets
            }

        except Exception as e:
            logger.error(f"Error selecting assets: {e}")
            state["assets"] = {
                "hero": {"url": "https://via.placeholder.com/600x400", "category": "general"},
                "grid": [{"url": "https://via.placeholder.com/300x200", "category": "general"}]
            }

        curator_message = f"Selected hero and grid images for template"
        state["messages"].append(AIMessage(content=curator_message))
        state["agent_results"]["asset_curator"] = {
            "status": "completed",
            "hero_selected": bool(state["assets"]["hero"]),
            "grid_count": len(state["assets"]["grid"])
        }

        return state

    def _copywriter_node(self, state: AgentState) -> AgentState:
        """Copywriter node that generates email content using OpenAI."""
        logger.info("Copywriter: Generating email content")

        state["current_agent"] = "copywriter"
        state["progress"] = 65
        state["step"] = "copywriter"

        template_request = state["template_request"]
        primary_product = state.get("primary_product")
        brand_guidelines = state.get("brand_guidelines")

        # Generate copy using OpenAI
        try:
            copy_content = self._generate_copy_with_ai(
                template_request.template_type,
                primary_product,
                brand_guidelines
            )
            state["copy_content"] = copy_content

        except Exception as e:
            logger.error(f"Error generating copy: {e}")
            # Fallback copy
            state["copy_content"] = {
                "subject": f"Your {template_request.template_type.replace('_', ' ').title()}",
                "preheader": "Check out these great products",
                "headline": "Great Products Await",
                "subcopy": "Discover something special today.",
                "cta": "Shop Now",
                "items_title": "Products",
                "recommendations_title": "Recommendations"
            }

        copywriter_message = f"Generated email copy content"
        state["messages"].append(AIMessage(content=copywriter_message))
        state["agent_results"]["copywriter"] = {
            "status": "completed",
            "subject": state["copy_content"]["subject"],
            "headline": state["copy_content"]["headline"]
        }

        return state

    def _template_layout_node(self, state: AgentState) -> AgentState:
        """Template Layout node that composes the final JSON."""
        logger.info("Template Layout: Composing email template JSON")

        state["current_agent"] = "template_layout"
        state["progress"] = 80
        state["step"] = "template_layout"

        template_request = state["template_request"]

        # Load design tokens
        try:
            design_tokens = tokens_loader_tool._run(template_request.template_type)
            state["design_tokens"] = design_tokens
        except Exception as e:
            logger.error(f"Error loading design tokens: {e}")
            state["design_tokens"] = {}

        # Compose template JSON
        template_json = self._compose_template_json(state)
        state["template_json"] = template_json

        # Validate template
        try:
            validation_result = template_validator_tool._run(template_json)
            is_valid = validation_result.get("valid", True)
        except Exception as e:
            logger.error(f"Error validating template: {e}")
            is_valid = True

        layout_message = f"Composed template JSON with {len(template_json.get('blocks', []))} blocks"
        state["messages"].append(AIMessage(content=layout_message))
        state["agent_results"]["template_layout"] = {
            "status": "completed",
            "blocks_count": len(template_json.get("blocks", [])),
            "is_valid": is_valid
        }

        return state

    def _render_node(self, state: AgentState) -> AgentState:
        """Render node that converts JSON to MJML and HTML."""
        logger.info("Render: Converting template to MJML and HTML")

        state["current_agent"] = "render"
        state["progress"] = 95
        state["step"] = "render"

        template_json = state.get("template_json")

        if not template_json:
            logger.error("No template JSON available for rendering")
            state["final_result"] = {"error": "No template JSON available"}
            state["progress"] = 100
            state["step"] = "error"
            return state

        try:
            # Convert to MJML
            mjml_content = self._json_to_mjml(template_json)

            # Render to HTML
            render_result = mjml_renderer_tool._run(mjml_content)

            state["final_result"] = {
                "jsonTemplate": template_json,
                "mjml": mjml_content,
                "html": render_result.get("html", ""),
                "tokensVersion": "1.0"
            }

        except Exception as e:
            logger.error(f"Error rendering template: {e}")
            state["final_result"] = {
                "error": f"Rendering failed: {str(e)}",
                "jsonTemplate": template_json
            }

        state["progress"] = 100
        state["step"] = "result"

        render_message = "Template rendering completed"
        state["messages"].append(AIMessage(content=render_message))
        state["agent_results"]["render"] = {
            "status": "completed",
            "has_html": bool(state["final_result"].get("html")),
            "has_mjml": bool(state["final_result"].get("mjml"))
        }

        return state

    def _generate_copy_with_ai(self, template_type: str, primary_product: Optional[Dict[str, Any]], brand_guidelines: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate copy using OpenAI."""

        # Prepare context
        product_name = primary_product.get("name", "Product") if primary_product else "Product"
        brand_tone = brand_guidelines.get("tone", "professional") if brand_guidelines else "professional"

        # If OpenAI is not available, use fallback immediately
        if self.llm is None:
            return self._get_fallback_copy_content(template_type, product_name)

        prompt = ChatPromptTemplate.from_template("""
        You are an expert email copywriter. Generate compelling email content for a {template_type} email.

        Product: {product_name}
        Brand tone: {brand_tone}
        Brand guidelines: {brand_guidelines}

        Generate the following (return as JSON):
        1. subject: Email subject line (under 50 characters, compelling)
        2. preheader: Preview text (under 90 characters)
        3. headline: Main hero headline (engaging, 3-8 words)
        4. subcopy: Supporting text for hero (1-2 sentences)
        5. cta: Call-to-action button text (2-3 words)
        6. items_title: Title for main products section
        7. recommendations_title: Title for recommendations section

        Make it relevant to the template type and engaging for the customer.
        """)

        try:
            chain = prompt | self.llm
            response = chain.invoke({
                "template_type": template_type.replace("_", " "),
                "product_name": product_name,
                "brand_tone": brand_tone,
                "brand_guidelines": brand_guidelines or "Standard professional approach"
            })

            # Try to parse JSON response
            try:
                import re
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except:
                pass

            # Fallback structured response
            return self._get_fallback_copy_content(template_type, product_name)

        except Exception as e:
            logger.error(f"AI copy generation failed: {e}")
            return self._get_fallback_copy_content(template_type, product_name)

    def _get_fallback_copy_content(self, template_type: str, product_name: str) -> Dict[str, Any]:
        """Get fallback copy content when AI generation fails."""

        fallback_templates = {
            "cart_abandon": {
                "subject": f"Don't forget about {product_name}!",
                "preheader": "Complete your purchase today",
                "headline": f"Still thinking about {product_name}?",
                "subcopy": "Complete your purchase now and enjoy fast shipping.",
                "cta": "Complete Purchase",
                "items_title": "Your Cart",
                "recommendations_title": "You Might Also Like"
            },
            "post_purchase": {
                "subject": "Thank you for your purchase!",
                "preheader": "Your order is confirmed",
                "headline": f"Thanks for choosing {product_name}!",
                "subcopy": "Your order is being processed and will ship soon.",
                "cta": "Track Order",
                "items_title": "Your Purchase",
                "recommendations_title": "Recommended for You"
            },
            "order_confirmation": {
                "subject": "Order confirmed - We're preparing your items",
                "preheader": "Order details inside",
                "headline": "Your order is confirmed!",
                "subcopy": f"We're preparing {product_name} for shipment.",
                "cta": "View Order Details",
                "items_title": "Your Order",
                "recommendations_title": "You Might Also Like"
            }
        }

        return fallback_templates.get(template_type, fallback_templates["cart_abandon"])

    def _compose_template_json(self, state: AgentState) -> Dict[str, Any]:
        """Compose the final template JSON structure."""
        template_request = state["template_request"]
        copy_content = state.get("copy_content", {})
        assets = state.get("assets", {})
        primary_product = state.get("primary_product")
        related_products = state.get("related_products", [])

        template_json = {
            "locale": template_request.locale,
            "templateType": template_request.template_type,
            "subject": copy_content.get("subject", ""),
            "preheader": copy_content.get("preheader", ""),
            "blocks": []
        }

        # Hero block
        hero_block = {
            "type": "hero",
            "headline": copy_content.get("headline", ""),
            "subcopy": copy_content.get("subcopy", ""),
            "imageUrl": assets.get("hero", {}).get("url", "") if assets.get("hero") else ""
        }
        template_json["blocks"].append(hero_block)

        # Items block (primary product)
        if primary_product and not primary_product.get("error"):
            items_block = {
                "type": "items",
                "title": copy_content.get("items_title", "Products"),
                "items": [{
                    "sku": primary_product.get("sku", ""),
                    "name": primary_product.get("name", ""),
                    "price": primary_product.get("price", ""),
                    "imageUrl": primary_product.get("image_placeholder", ""),
                    "url": f"#{primary_product.get('sku', '')}"
                }]
            }
            template_json["blocks"].append(items_block)

        # Recommendations block
        if related_products and len(related_products) > 0:
            recommendations_items = []
            for product in related_products[:3]:  # Limit to 3 recommendations
                if not product.get("error"):
                    recommendations_items.append({
                        "sku": product.get("sku", ""),
                        "name": product.get("name", ""),
                        "price": product.get("price", ""),
                        "imageUrl": product.get("image_placeholder", ""),
                        "url": f"#{product.get('sku', '')}"
                    })

            if recommendations_items:
                recommendations_block = {
                    "type": "recommendations",
                    "title": copy_content.get("recommendations_title", "You Might Also Like"),
                    "items": recommendations_items
                }
                template_json["blocks"].append(recommendations_block)

        # Footer block
        footer_block = {
            "type": "footer",
            "legal": "© 2025 Your Company. All rights reserved.",
            "preferencesUrl": "#preferences",
            "unsubscribeUrl": "#unsubscribe"
        }
        template_json["blocks"].append(footer_block)

        return template_json

    def _json_to_mjml(self, template_json: Dict[str, Any]) -> str:
        """Convert template JSON to MJML for rendering."""
        mjml_parts = [
            '<mjml>',
            '  <mj-head>',
            f'    <mj-title>{template_json.get("subject", "Email")}</mj-title>',
            '    <mj-preview>' + template_json.get("preheader", "") + '</mj-preview>',
            '  </mj-head>',
            '  <mj-body>'
        ]

        # Process blocks
        for block in template_json.get("blocks", []):
            if block["type"] == "hero":
                mjml_parts.extend([
                    '    <mj-section>',
                    '      <mj-column>',
                    f'        <mj-image src="{block.get("imageUrl", "")}" alt="Hero Image" />',
                    f'        <mj-text font-size="24px" font-weight="bold">{block.get("headline", "")}</mj-text>',
                    f'        <mj-text>{block.get("subcopy", "")}</mj-text>',
                    '        <mj-button>Shop Now</mj-button>',
                    '      </mj-column>',
                    '    </mj-section>'
                ])

            elif block["type"] == "items":
                mjml_parts.extend([
                    '    <mj-section>',
                    '      <mj-column>',
                    f'        <mj-text font-size="20px" font-weight="bold">{block.get("title", "Items")}</mj-text>'
                ])

                for item in block.get("items", []):
                    mjml_parts.extend([
                        f'        <mj-image src="{item.get("imageUrl", "")}" alt="{item.get("name", "")}" width="200px" />',
                        f'        <mj-text font-weight="bold">{item.get("name", "")}</mj-text>',
                        f'        <mj-text>{item.get("price", "")}</mj-text>'
                    ])

                mjml_parts.extend([
                    '      </mj-column>',
                    '    </mj-section>'
                ])

            elif block["type"] == "recommendations":
                mjml_parts.extend([
                    '    <mj-section>',
                    '      <mj-column>',
                    f'        <mj-text font-size="20px" font-weight="bold">{block.get("title", "Recommendations")}</mj-text>',
                    '      </mj-column>',
                    '    </mj-section>',
                    '    <mj-section>'
                ])

                for item in block.get("items", []):
                    mjml_parts.extend([
                        '      <mj-column>',
                        f'        <mj-image src="{item.get("imageUrl", "")}" alt="{item.get("name", "")}" />',
                        f'        <mj-text font-weight="bold">{item.get("name", "")}</mj-text>',
                        f'        <mj-text>{item.get("price", "")}</mj-text>',
                        '      </mj-column>'
                    ])

                mjml_parts.append('    </mj-section>')

            elif block["type"] == "footer":
                mjml_parts.extend([
                    '    <mj-section>',
                    '      <mj-column>',
                    f'        <mj-text align="center">{block.get("legal", "")}</mj-text>',
                    f'        <mj-text align="center"><a href="{block.get("unsubscribeUrl", "#")}">Unsubscribe</a></mj-text>',
                    '      </mj-column>',
                    '    </mj-section>'
                ])

        mjml_parts.extend([
            '  </mj-body>',
            '</mjml>'
        ])

        return '\n'.join(mjml_parts)


# Create supervisor instance
supervisor_agent = SupervisorAgent()