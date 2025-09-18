"""Product-related tools for retrieving SKU information and recommendations."""

import pandas as pd
import os
from typing import List, Dict, Any
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from pathlib import Path

class ProductLookupInput(BaseModel):
    sku: str = Field(..., description="Primary product SKU to lookup")

class RelatedProductsInput(BaseModel):
    sku: str = Field(..., description="Primary product SKU to find related products for")
    max_results: int = Field(default=3, description="Maximum number of related products to return")

class ProductLookupTool(BaseTool):
    """Tool to lookup product information by SKU from CSV."""
    name: str = "product_lookup"
    description: str = """
    Lookup detailed product information by SKU from the products CSV.
    Returns product details including name, category, price, brand, description, and image.
    """
    args_schema: type = ProductLookupInput

    def _run(self, sku: str) -> Dict[str, Any]:
        try:
            csv_path = Path("uploads/products.csv")
            if not csv_path.exists():
                return {"error": f"Products CSV not found at {csv_path}"}

            df = pd.read_csv(csv_path)
            product = df[df['sku'] == sku]

            if product.empty:
                return {"error": f"Product with SKU {sku} not found"}

            product_row = product.iloc[0]
            return {
                "sku": product_row["sku"],
                "name": product_row["name"],
                "category": product_row["category"],
                "price": product_row["price"],
                "brand": product_row["brand"],
                "description": product_row["description"],
                "image_placeholder": product_row["image_placeholder"],
                "related_skus": product_row["related_skus"].split(",") if pd.notna(product_row["related_skus"]) else []
            }
        except Exception as e:
            return {"error": f"Error looking up product {sku}: {str(e)}"}

class RelatedProductsTool(BaseTool):
    """Tool to find related/recommended products for a given SKU."""
    name: str = "related_products"
    description: str = """
    Find related or recommended products for a given primary SKU.
    Returns a list of related products with full details for recommendations section.
    """
    args_schema: type = RelatedProductsInput

    def _run(self, sku: str, max_results: int = 3) -> List[Dict[str, Any]]:
        try:
            csv_path = Path("uploads/products.csv")
            if not csv_path.exists():
                return [{"error": f"Products CSV not found at {csv_path}"}]

            df = pd.read_csv(csv_path)
            primary_product = df[df['sku'] == sku]

            if primary_product.empty:
                return [{"error": f"Primary product with SKU {sku} not found"}]

            # Get related SKUs from the primary product
            related_skus_str = primary_product.iloc[0]["related_skus"]
            if pd.isna(related_skus_str):
                return []

            related_skus = [s.strip() for s in related_skus_str.split(",")][:max_results]

            # Find products with those SKUs
            related_products = df[df['sku'].isin(related_skus)]

            results = []
            for _, row in related_products.iterrows():
                results.append({
                    "sku": row["sku"],
                    "name": row["name"],
                    "category": row["category"],
                    "price": row["price"],
                    "brand": row["brand"],
                    "description": row["description"],
                    "image_placeholder": row["image_placeholder"]
                })

            return results[:max_results]
        except Exception as e:
            return [{"error": f"Error finding related products for {sku}: {str(e)}"}]

# Tool instances
product_lookup_tool = ProductLookupTool()
related_products_tool = RelatedProductsTool()