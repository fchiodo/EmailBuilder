"""
HTML Style Miner - Estrae Design Tokens da template HTML
Utilizza BeautifulSoup + CSS Stats per analisi completa
"""

import re
import cssutils
from pathlib import Path
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import webcolors

from ..utils.css_analyzer import CSSAnalyzer

class HTMLStyleMiner:
    """Estrae style tokens da file HTML"""

    def __init__(self):
        self.css_analyzer = CSSAnalyzer()
        # Suppress cssutils warnings
        cssutils.log.setLevel(50)

    def extract_tokens(self, html_file: Path) -> Dict[str, Any]:
        """
        Estrae tutti i design tokens da un file HTML
        """
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()

        soup = BeautifulSoup(content, 'html.parser')

        tokens = {
            "source": str(html_file),
            "colors": self._extract_colors(soup, content),
            "typography": self._extract_typography(soup),
            "spacing": self._extract_spacing(soup),
            "radius": self._extract_radius(soup),
            "components": self._extract_components(soup),
            "layout": self._extract_layout(soup)
        }

        return tokens

    def _extract_colors(self, soup: BeautifulSoup, content: str) -> Dict[str, Any]:
        """Estrae palette colori da CSS e attributi"""
        colors = {
            "palette": [],
            "usage": {
                "background": [],
                "text": [],
                "accent": [],
                "border": []
            }
        }

        # 1. CSS colors
        css_colors = self._parse_css_colors(content)
        colors["palette"].extend(css_colors)

        # 2. Inline style colors
        inline_colors = self._parse_inline_colors(soup)
        colors["palette"].extend(inline_colors)

        # 3. Categorize colors by usage
        colors["usage"] = self._categorize_colors(soup, colors["palette"])

        # Remove duplicates and normalize
        colors["palette"] = list(set(colors["palette"]))

        return colors

    def _parse_css_colors(self, content: str) -> List[str]:
        """Estrae colori da CSS embedded"""
        colors = []

        # Extract CSS from <style> tags and external links
        css_content = self._extract_css_content(content)

        if css_content:
            # Use cssutils to parse CSS
            sheet = cssutils.parseString(css_content)
            for rule in sheet:
                if rule.type == rule.STYLE_RULE:
                    for prop in rule.style:
                        if 'color' in prop.name or 'background' in prop.name:
                            color_value = prop.value
                            extracted_colors = self._extract_color_values(color_value)
                            colors.extend(extracted_colors)

        return colors

    def _extract_css_content(self, html_content: str) -> str:
        """Estrae tutto il CSS dal contenuto HTML"""
        css_content = ""

        # Extract from <style> tags
        style_pattern = r'<style[^>]*>(.*?)</style>'
        styles = re.findall(style_pattern, html_content, re.DOTALL | re.IGNORECASE)
        for style in styles:
            css_content += style + "\n"

        return css_content

    def _extract_color_values(self, css_value: str) -> List[str]:
        """Estrae valori di colore da una proprietà CSS"""
        colors = []

        # Hex colors
        hex_pattern = r'#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})'
        hex_colors = re.findall(hex_pattern, css_value)
        for hex_color in hex_colors:
            colors.append(f"#{hex_color}")

        # RGB/RGBA colors
        rgb_pattern = r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+))?\s*\)'
        rgb_matches = re.findall(rgb_pattern, css_value)
        for match in rgb_matches:
            r, g, b = int(match[0]), int(match[1]), int(match[2])
            if match[3]:  # RGBA
                a = float(match[3])
                colors.append(f"rgba({r}, {g}, {b}, {a})")
            else:  # RGB
                colors.append(f"rgb({r}, {g}, {b})")

        # Named colors
        named_colors = ['red', 'blue', 'green', 'black', 'white', 'gray', 'yellow', 'orange', 'purple', 'pink']
        for named_color in named_colors:
            if named_color in css_value.lower():
                colors.append(named_color)

        return colors

    def _parse_inline_colors(self, soup: BeautifulSoup) -> List[str]:
        """Estrae colori da attributi style inline"""
        colors = []

        elements_with_style = soup.find_all(attrs={"style": True})
        for element in elements_with_style:
            style_attr = element.get('style', '')
            extracted_colors = self._extract_color_values(style_attr)
            colors.extend(extracted_colors)

        return colors

    def _categorize_colors(self, soup: BeautifulSoup, palette: List[str]) -> Dict[str, List[str]]:
        """Categorizza i colori per uso (background, text, etc.)"""
        usage = {
            "background": [],
            "text": [],
            "accent": [],
            "border": []
        }

        # Analyze color usage context
        for element in soup.find_all(attrs={"style": True}):
            style = element.get('style', '')

            if 'background' in style:
                bg_colors = self._extract_color_values(style)
                usage["background"].extend(bg_colors)

            if 'color:' in style:
                text_colors = self._extract_color_values(style)
                usage["text"].extend(text_colors)

        return usage

    def _extract_typography(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Estrae tokens tipografici"""
        typography = {
            "families": [],
            "sizes": [],
            "weights": [],
            "hierarchy": {}
        }

        # Extract font families
        font_families = set()
        font_sizes = set()
        font_weights = set()

        # From CSS and inline styles
        elements_with_style = soup.find_all(attrs={"style": True})
        for element in elements_with_style:
            style = element.get('style', '')

            # Font family
            font_family_match = re.search(r'font-family:\s*([^;]+)', style)
            if font_family_match:
                family = font_family_match.group(1).strip().strip('"\'')
                font_families.add(family)

            # Font size
            font_size_match = re.search(r'font-size:\s*([^;]+)', style)
            if font_size_match:
                size = font_size_match.group(1).strip()
                font_sizes.add(size)

            # Font weight
            font_weight_match = re.search(r'font-weight:\s*([^;]+)', style)
            if font_weight_match:
                weight = font_weight_match.group(1).strip()
                font_weights.add(weight)

        # Extract hierarchy from HTML tags
        typography["hierarchy"] = self._extract_typography_hierarchy(soup)

        typography["families"] = list(font_families)
        typography["sizes"] = list(font_sizes)
        typography["weights"] = list(font_weights)

        return typography

    def _extract_typography_hierarchy(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Estrae gerarchia tipografica da tag HTML"""
        hierarchy = {}

        # Analyze heading tags
        for i in range(1, 7):
            headings = soup.find_all(f'h{i}')
            if headings:
                hierarchy[f"h{i}"] = {
                    "count": len(headings),
                    "sample_text": headings[0].get_text()[:50] if headings else ""
                }

        # Analyze paragraph and body text
        paragraphs = soup.find_all('p')
        if paragraphs:
            hierarchy["body"] = {
                "count": len(paragraphs),
                "sample_text": paragraphs[0].get_text()[:50] if paragraphs else ""
            }

        return hierarchy

    def _extract_spacing(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Estrae tokens di spaziatura"""
        spacing = {
            "padding": [],
            "margin": [],
            "gaps": []
        }

        elements_with_style = soup.find_all(attrs={"style": True})
        for element in elements_with_style:
            style = element.get('style', '')

            # Padding values
            padding_matches = re.findall(r'padding[^:]*:\s*([^;]+)', style)
            for match in padding_matches:
                spacing["padding"].extend(self._parse_spacing_values(match))

            # Margin values
            margin_matches = re.findall(r'margin[^:]*:\s*([^;]+)', style)
            for match in margin_matches:
                spacing["margin"].extend(self._parse_spacing_values(match))

        # Remove duplicates and sort
        spacing["padding"] = sorted(list(set(spacing["padding"])))
        spacing["margin"] = sorted(list(set(spacing["margin"])))

        return spacing

    def _parse_spacing_values(self, css_value: str) -> List[str]:
        """Parse spacing values from CSS"""
        values = []
        # Extract numeric values with units
        value_pattern = r'(\d+(?:\.\d+)?(?:px|em|rem|%|vh|vw))'
        matches = re.findall(value_pattern, css_value)
        values.extend(matches)
        return values

    def _extract_radius(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Estrae tokens di border-radius"""
        radius = {
            "values": [],
            "usage": {}
        }

        elements_with_style = soup.find_all(attrs={"style": True})
        for element in elements_with_style:
            style = element.get('style', '')

            radius_matches = re.findall(r'border-radius:\s*([^;]+)', style)
            for match in radius_matches:
                values = self._parse_spacing_values(match)
                radius["values"].extend(values)

        radius["values"] = sorted(list(set(radius["values"])))
        return radius

    def _extract_components(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Identifica pattern di componenti"""
        components = {
            "buttons": self._analyze_buttons(soup),
            "links": self._analyze_links(soup),
            "cards": self._analyze_cards(soup),
            "lists": self._analyze_lists(soup)
        }

        return components

    def _analyze_buttons(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analizza pattern dei bottoni"""
        buttons = soup.find_all(['button', 'input[type="button"]', 'input[type="submit"]'])
        button_links = soup.find_all('a', class_=lambda x: x and 'button' in x.lower() if x else False)

        all_buttons = buttons + button_links

        return {
            "count": len(all_buttons),
            "patterns": self._extract_button_patterns(all_buttons)
        }

    def _extract_button_patterns(self, buttons: List) -> List[Dict[str, Any]]:
        """Estrae pattern comuni dai bottoni"""
        patterns = []

        for button in buttons[:5]:  # Analyze first 5 buttons
            pattern = {
                "text": button.get_text().strip(),
                "classes": button.get('class', []),
                "style": button.get('style', ''),
                "tag": button.name
            }
            patterns.append(pattern)

        return patterns

    def _analyze_links(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analizza pattern dei link"""
        links = soup.find_all('a')

        return {
            "count": len(links),
            "patterns": [
                {
                    "text": link.get_text().strip()[:30],
                    "href": link.get('href', ''),
                    "classes": link.get('class', [])
                }
                for link in links[:5]
            ]
        }

    def _analyze_cards(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analizza pattern delle card"""
        # Look for common card patterns
        card_selectors = [
            lambda x: x and any(word in x.lower() for word in ['card', 'item', 'product']) if x else False
        ]

        cards = []
        for selector in card_selectors:
            cards.extend(soup.find_all(class_=selector))

        return {
            "count": len(cards),
            "patterns": [
                {
                    "classes": card.get('class', []),
                    "children_count": len(card.find_all())
                }
                for card in cards[:3]
            ]
        }

    def _analyze_lists(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analizza pattern delle liste"""
        lists = soup.find_all(['ul', 'ol'])

        return {
            "count": len(lists),
            "types": {
                "ul": len(soup.find_all('ul')),
                "ol": len(soup.find_all('ol'))
            }
        }

    def _extract_layout(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analizza pattern di layout"""
        layout = {
            "structure": self._analyze_layout_structure(soup),
            "grid_systems": self._detect_grid_systems(soup),
            "containers": self._analyze_containers(soup)
        }

        return layout

    def _analyze_layout_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analizza struttura del layout"""
        structure = {
            "sections": len(soup.find_all(['section', 'div[class*="section"]'])),
            "headers": len(soup.find_all(['header', 'div[class*="header"]'])),
            "footers": len(soup.find_all(['footer', 'div[class*="footer"]'])),
            "containers": len(soup.find_all(class_=lambda x: x and 'container' in x.lower() if x else False))
        }

        return structure

    def _detect_grid_systems(self, soup: BeautifulSoup) -> List[str]:
        """Rileva sistemi di griglia utilizzati"""
        grid_systems = []

        # Bootstrap
        if soup.find(class_=lambda x: x and any(cls.startswith('col-') for cls in x) if x else False):
            grid_systems.append("bootstrap")

        # CSS Grid
        elements_with_style = soup.find_all(attrs={"style": True})
        for element in elements_with_style:
            style = element.get('style', '')
            if 'display: grid' in style or 'grid-template' in style:
                grid_systems.append("css-grid")
                break

        # Flexbox
        for element in elements_with_style:
            style = element.get('style', '')
            if 'display: flex' in style or 'flex-' in style:
                grid_systems.append("flexbox")
                break

        return grid_systems

    def _analyze_containers(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analizza pattern dei container"""
        containers = soup.find_all(class_=lambda x: x and 'container' in x.lower() if x else False)

        return {
            "count": len(containers),
            "classes": list(set([
                ' '.join(container.get('class', []))
                for container in containers
            ]))
        }