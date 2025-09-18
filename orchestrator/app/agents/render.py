"""Render Agent for converting email JSON templates to MJML and HTML."""

from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import json

from app.tools.template_tools import mjml_renderer_tool

class RenderAgent:
    """Agent responsible for rendering email templates to MJML and HTML."""

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
            print("Warning: OpenAI not configured in RenderAgent, using fallback implementation")

    def render_email(
        self,
        template_json: Dict[str, Any],
        design_tokens: Dict[str, Any],
        render_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Render email template to MJML and HTML.

        Args:
            template_json: Complete email template JSON
            design_tokens: Design tokens for styling
            render_options: Optional rendering preferences

        Returns:
            Dictionary containing MJML, HTML, and rendering metadata
        """
        try:
            # Generate MJML from template JSON
            mjml_content = self._generate_mjml(template_json, design_tokens, render_options)

            # Render MJML to HTML using external service
            render_result = mjml_renderer_tool._run(mjml_content)

            # Process and optimize the rendered output
            processed_result = self._process_render_result(
                render_result, template_json, design_tokens
            )

            return {
                "success": True,
                "mjml": mjml_content,
                "html": processed_result["html"],
                "warnings": processed_result["warnings"],
                "metadata": {
                    "template_type": template_json.get("templateType"),
                    "locale": template_json.get("locale"),
                    "render_timestamp": processed_result["timestamp"],
                    "design_tokens_applied": bool(design_tokens)
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Email rendering failed: {str(e)}",
                "mjml": self._get_fallback_mjml(template_json),
                "html": self._get_fallback_html(template_json)
            }

    def _generate_mjml(
        self,
        template_json: Dict[str, Any],
        design_tokens: Dict[str, Any],
        render_options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate MJML from template JSON using design tokens."""

        # Extract design token values
        colors = design_tokens.get("colors", {})
        fonts = design_tokens.get("fonts", {})
        spacing = design_tokens.get("spacing", {})
        radius = design_tokens.get("radius", {})

        # Build MJML structure
        mjml_parts = []

        # MJML Header
        mjml_parts.extend([
            '<mjml>',
            '  <mj-head>',
            f'    <mj-title>{template_json.get("subject", "Email")}</mj-title>',
            f'    <mj-preview>{template_json.get("preheader", "")}</mj-preview>',
            '    <mj-attributes>',
            f'      <mj-text font-family="{fonts.get("primary", "Arial, sans-serif")}" font-size="{fonts.get("body", {}).get("size", "16px")}" line-height="{fonts.get("body", {}).get("lineHeight", "1.5")}" color="{colors.get("text", "#1e293b")}" />',
            f'      <mj-section background-color="{colors.get("background", "#f8fafc")}" padding="{spacing.get("md", "16px")}" />',
            '    </mj-attributes>',
            '    <mj-style>',
            '      .hero-text { text-align: center; }',
            '      .product-item { border: 1px solid #e2e8f0; border-radius: ' + radius.get("card", "8px") + '; margin-bottom: ' + spacing.get("md", "16px") + '; }',
            '      .cta-button { background-color: ' + colors.get("primary", "#dc2626") + '; border-radius: ' + radius.get("button", "6px") + '; }',
            '    </mj-style>',
            '  </mj-head>',
            '  <mj-body background-color="' + colors.get("background", "#f8fafc") + '">'
        ])

        # Process blocks
        for block in template_json.get("blocks", []):
            mjml_block = self._render_block_to_mjml(block, design_tokens)
            mjml_parts.extend(mjml_block)

        # MJML Footer
        mjml_parts.extend([
            '  </mj-body>',
            '</mjml>'
        ])

        return '\n'.join(mjml_parts)

    def _render_block_to_mjml(self, block: Dict[str, Any], design_tokens: Dict[str, Any]) -> List[str]:
        """Render individual block to MJML."""

        block_type = block.get("type")
        colors = design_tokens.get("colors", {})
        fonts = design_tokens.get("fonts", {})
        spacing = design_tokens.get("spacing", {})

        if block_type == "hero":
            return self._render_hero_block(block, colors, fonts, spacing)
        elif block_type == "items":
            return self._render_items_block(block, colors, fonts, spacing)
        elif block_type == "recommendations":
            return self._render_recommendations_block(block, colors, fonts, spacing)
        elif block_type == "footer":
            return self._render_footer_block(block, colors, fonts, spacing)
        else:
            return []

    def _render_hero_block(self, block: Dict[str, Any], colors: Dict, fonts: Dict, spacing: Dict) -> List[str]:
        """Render hero block to MJML."""

        mjml_parts = [
            '    <mj-section background-color="' + colors.get("surface", "#ffffff") + '" padding="' + spacing.get("xl", "32px") + '">',
            '      <mj-column>'
        ]

        # Hero image
        if block.get("imageUrl"):
            mjml_parts.append(f'        <mj-image src="{block["imageUrl"]}" alt="Hero Image" width="600px" />')

        # Hero text
        mjml_parts.extend([
            f'        <mj-text css-class="hero-text" font-size="{fonts.get("heading", {}).get("size", "24px")}" font-weight="{fonts.get("heading", {}).get("weight", "700")}" color="{colors.get("text", "#1e293b")}" padding-top="{spacing.get("lg", "24px")}">',
            f'          {block.get("headline", "")}',
            '        </mj-text>',
            f'        <mj-text css-class="hero-text" color="{colors.get("textSecondary", "#64748b")}" padding-top="{spacing.get("sm", "8px")}">',
            f'          {block.get("subcopy", "")}',
            '        </mj-text>'
        ])

        # CTA button
        if block.get("ctaLabel"):
            mjml_parts.extend([
                f'        <mj-button css-class="cta-button" href="{block.get("ctaUrl", "#")}" background-color="{colors.get("primary", "#dc2626")}" color="white" padding-top="{spacing.get("lg", "24px")}">',
                f'          {block["ctaLabel"]}',
                '        </mj-button>'
            ])

        mjml_parts.extend([
            '      </mj-column>',
            '    </mj-section>'
        ])

        return mjml_parts

    def _render_items_block(self, block: Dict[str, Any], colors: Dict, fonts: Dict, spacing: Dict) -> List[str]:
        """Render items block to MJML."""

        mjml_parts = [
            '    <mj-section background-color="' + colors.get("surface", "#ffffff") + '" padding="' + spacing.get("lg", "24px") + '">',
            '      <mj-column>',
            f'        <mj-text font-size="{fonts.get("heading", {}).get("size", "20px")}" font-weight="{fonts.get("heading", {}).get("weight", "700")}" color="{colors.get("text", "#1e293b")}" align="center">',
            f'          {block.get("title", "Items")}',
            '        </mj-text>',
            '      </mj-column>',
            '    </mj-section>'
        ]

        # Render each item
        for item in block.get("items", []):
            mjml_parts.extend([
                '    <mj-section background-color="' + colors.get("surface", "#ffffff") + '" padding="' + spacing.get("md", "16px") + '">',
                '      <mj-column width="30%">'
            ])

            if item.get("imageUrl"):
                mjml_parts.append(f'        <mj-image src="{item["imageUrl"]}" alt="{item.get("name", "")}" width="150px" />')

            mjml_parts.extend([
                '      </mj-column>',
                '      <mj-column width="70%">',
                f'        <mj-text font-weight="bold" color="{colors.get("text", "#1e293b")}">',
                f'          {item.get("name", "")}',
                '        </mj-text>',
                f'        <mj-text color="{colors.get("primary", "#dc2626")}" font-weight="bold">',
                f'          ${item.get("price", "0")}',
                '        </mj-text>',
                f'        <mj-text color="{colors.get("textSecondary", "#64748b")}" font-size="14px">',
                f'          {item.get("description", "")}',
                '        </mj-text>',
                f'        <mj-text color="{colors.get("textSecondary", "#64748b")}" font-size="12px">',
                f'          SKU: {item.get("sku", "")}',
                '        </mj-text>',
                '      </mj-column>',
                '    </mj-section>'
            ])

        return mjml_parts

    def _render_recommendations_block(self, block: Dict[str, Any], colors: Dict, fonts: Dict, spacing: Dict) -> List[str]:
        """Render recommendations block to MJML."""

        mjml_parts = [
            '    <mj-section background-color="' + colors.get("surface", "#ffffff") + '" padding="' + spacing.get("lg", "24px") + '">',
            '      <mj-column>',
            f'        <mj-text font-size="{fonts.get("heading", {}).get("size", "20px")}" font-weight="{fonts.get("heading", {}).get("weight", "700")}" color="{colors.get("text", "#1e293b")}" align="center">',
            f'          {block.get("title", "Recommendations")}',
            '        </mj-text>',
            '      </mj-column>',
            '    </mj-section>',
            '    <mj-section background-color="' + colors.get("surface", "#ffffff") + '" padding="' + spacing.get("md", "16px") + '">'
        ]

        # Render items in grid layout
        items = block.get("items", [])
        items_per_row = min(3, len(items))
        column_width = f"{100 // items_per_row}%" if items_per_row > 0 else "100%"

        for item in items:
            mjml_parts.extend([
                f'      <mj-column width="{column_width}">',
                f'        <mj-image src="{item.get("imageUrl", "")}" alt="{item.get("name", "")}" width="150px" />',
                f'        <mj-text font-weight="bold" color="{colors.get("text", "#1e293b")}" align="center">',
                f'          {item.get("name", "")}',
                '        </mj-text>',
                f'        <mj-text color="{colors.get("primary", "#dc2626")}" font-weight="bold" align="center">',
                f'          ${item.get("price", "0")}',
                '        </mj-text>',
                '      </mj-column>'
            ])

        mjml_parts.append('    </mj-section>')
        return mjml_parts

    def _render_footer_block(self, block: Dict[str, Any], colors: Dict, fonts: Dict, spacing: Dict) -> List[str]:
        """Render footer block to MJML."""

        mjml_parts = [
            '    <mj-section background-color="' + colors.get("secondary", "#64748b") + '" padding="' + spacing.get("lg", "24px") + '">',
            '      <mj-column>',
            f'        <mj-text color="white" align="center" font-size="16px" font-weight="bold">',
            f'          {block.get("companyName", "Your Company")}',
            '        </mj-text>',
            f'        <mj-text color="white" align="center" font-size="14px">',
            f'          {block.get("address", "")}',
            '        </mj-text>'
        ]

        # Social links
        social_links = block.get("socialLinks", [])
        if social_links:
            mjml_parts.append('        <mj-social mode="horizontal" align="center" icon-size="20px">')
            for link in social_links:
                platform = link.get("platform", "")
                url = link.get("url", "#")
                mjml_parts.append(f'          <mj-social-element name="{platform}" href="{url}"></mj-social-element>')
            mjml_parts.append('        </mj-social>')

        # Unsubscribe link
        mjml_parts.extend([
            f'        <mj-text color="white" align="center" font-size="12px" padding-top="{spacing.get("md", "16px")}">',
            f'          <a href="{block.get("unsubscribeUrl", "#")}" style="color: white;">Unsubscribe</a>',
            '        </mj-text>',
            '      </mj-column>',
            '    </mj-section>'
        ])

        return mjml_parts

    def _process_render_result(
        self,
        render_result: Dict[str, Any],
        template_json: Dict[str, Any],
        design_tokens: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process and enhance render result."""

        import datetime

        processed_result = {
            "html": render_result.get("html", ""),
            "warnings": render_result.get("warnings", []),
            "timestamp": datetime.datetime.now().isoformat()
        }

        # Add metadata to HTML if successful
        if processed_result["html"] and not render_result.get("error"):
            # Add meta tags for email clients
            html_with_meta = self._add_email_meta_tags(
                processed_result["html"],
                template_json,
                design_tokens
            )
            processed_result["html"] = html_with_meta

        return processed_result

    def _add_email_meta_tags(
        self,
        html: str,
        template_json: Dict[str, Any],
        design_tokens: Dict[str, Any]
    ) -> str:
        """Add email-specific meta tags to HTML."""

        # Basic meta tags for email clients
        meta_tags = [
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
            '<meta http-equiv="X-UA-Compatible" content="IE=edge">',
            f'<meta name="color-scheme" content="light">',
            f'<meta name="supported-color-schemes" content="light">'
        ]

        # Insert meta tags after <head> tag
        if '<head>' in html:
            head_pos = html.find('<head>') + 6
            html = html[:head_pos] + '\n    ' + '\n    '.join(meta_tags) + html[head_pos:]

        return html

    def _get_fallback_mjml(self, template_json: Dict[str, Any]) -> str:
        """Generate fallback MJML when rendering fails."""

        return f"""<mjml>
  <mj-head>
    <mj-title>{template_json.get("subject", "Email")}</mj-title>
    <mj-preview>{template_json.get("preheader", "")}</mj-preview>
  </mj-head>
  <mj-body>
    <mj-section>
      <mj-column>
        <mj-text font-size="24px" font-weight="bold">Email Content</mj-text>
        <mj-text>Sorry, there was an issue rendering your email template.</mj-text>
        <mj-button href="#">View Online</mj-button>
      </mj-column>
    </mj-section>
  </mj-body>
</mjml>"""

    def _get_fallback_html(self, template_json: Dict[str, Any]) -> str:
        """Generate fallback HTML when rendering fails."""

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{template_json.get("subject", "Email")}</title>
</head>
<body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8fafc;">
    <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 20px;">
        <h1 style="color: #1e293b;">Email Content</h1>
        <p style="color: #64748b;">Sorry, there was an issue rendering your email template.</p>
        <a href="#" style="display: inline-block; background-color: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px;">View Online</a>
    </div>
</body>
</html>"""

# Create render agent instance
render_agent = RenderAgent()