#!/usr/bin/env python3
"""
Style Mining Pipeline - Estrae Design Tokens da template storici
Supporta HTML, PDF e immagini come da specifica
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any

from miners.html_miner import HTMLStyleMiner
from miners.pdf_miner import PDFStyleMiner
from miners.image_miner import ImageStyleMiner
from utils.token_consolidator import TokenConsolidator
from utils.dtcg_generator import DTCGGenerator

def setup_paths():
    """Setup required directories"""
    base_dir = Path(__file__).parent.parent

    directories = [
        base_dir / "output",
        base_dir / "cache",
        base_dir.parent / "tokens",
        base_dir.parent / "templates"
    ]

    for dir_path in directories:
        dir_path.mkdir(exist_ok=True)

    return base_dir

def mine_template_sources(template_type: str, sources_dir: Path) -> Dict[str, Any]:
    """
    Estrae tokens da tutti i sorgenti disponibili per un template type
    """
    results = {
        "html_tokens": [],
        "pdf_tokens": [],
        "image_tokens": [],
        "consolidated_tokens": None
    }

    # 1. HTML Sources
    html_files = list(sources_dir.glob(f"{template_type}/**/*.html"))
    if html_files:
        print(f"📄 Mining {len(html_files)} HTML files...")
        html_miner = HTMLStyleMiner()
        for html_file in html_files:
            try:
                tokens = html_miner.extract_tokens(html_file)
                results["html_tokens"].append({
                    "source": str(html_file),
                    "tokens": tokens
                })
            except Exception as e:
                print(f"⚠️  Error processing {html_file}: {e}")

    # 2. PDF Sources
    pdf_files = list(sources_dir.glob(f"{template_type}/**/*.pdf"))
    if pdf_files:
        print(f"📑 Mining {len(pdf_files)} PDF files...")
        pdf_miner = PDFStyleMiner()
        for pdf_file in pdf_files:
            try:
                tokens = pdf_miner.extract_tokens(pdf_file)
                results["pdf_tokens"].append({
                    "source": str(pdf_file),
                    "tokens": tokens
                })
            except Exception as e:
                print(f"⚠️  Error processing {pdf_file}: {e}")

    # 3. Image Sources
    image_files = list(sources_dir.glob(f"{template_type}/**/*.{png,jpg,jpeg}"))
    if image_files:
        print(f"🖼️  Mining {len(image_files)} image files...")
        image_miner = ImageStyleMiner()
        for image_file in image_files:
            try:
                tokens = image_miner.extract_tokens(image_file)
                results["image_tokens"].append({
                    "source": str(image_file),
                    "tokens": tokens
                })
            except Exception as e:
                print(f"⚠️  Error processing {image_file}: {e}")

    # 4. Consolidate tokens
    print("🔄 Consolidating tokens...")
    consolidator = TokenConsolidator()

    all_tokens = []
    for source_tokens in results["html_tokens"]:
        all_tokens.append(source_tokens["tokens"])
    for source_tokens in results["pdf_tokens"]:
        all_tokens.append(source_tokens["tokens"])
    for source_tokens in results["image_tokens"]:
        all_tokens.append(source_tokens["tokens"])

    if all_tokens:
        consolidated = consolidator.consolidate(all_tokens, template_type)
        results["consolidated_tokens"] = consolidated

    return results

def generate_dtcg_tokens(consolidated_tokens: Dict[str, Any], template_type: str, output_dir: Path):
    """
    Genera Design Tokens in formato DTCG
    """
    print("🎨 Generating DTCG tokens...")

    generator = DTCGGenerator()
    dtcg_tokens = generator.generate(consolidated_tokens, template_type)

    # Save to tokens directory
    tokens_file = output_dir.parent / "tokens" / f"{template_type}.json"
    with open(tokens_file, 'w', encoding='utf-8') as f:
        json.dump(dtcg_tokens, f, indent=2, ensure_ascii=False)

    print(f"✅ Tokens saved to {tokens_file}")
    return dtcg_tokens

def main():
    parser = argparse.ArgumentParser(description="Style Mining Pipeline")
    parser.add_argument(
        "template_type",
        choices=["cart_abandon", "post_purchase", "order_confirmation"],
        help="Template type to process"
    )
    parser.add_argument(
        "--sources-dir",
        type=Path,
        default=None,
        help="Directory containing template sources"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for results"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Setup
    base_dir = setup_paths()
    sources_dir = args.sources_dir or base_dir.parent / "templates"
    output_dir = args.output_dir or base_dir / "output"

    print(f"🚀 Starting style mining for template type: {args.template_type}")
    print(f"📁 Sources directory: {sources_dir}")
    print(f"📤 Output directory: {output_dir}")

    if not sources_dir.exists():
        print(f"❌ Sources directory not found: {sources_dir}")
        print("💡 Please add template files to the templates directory")
        return 1

    # Mine all sources
    results = mine_template_sources(args.template_type, sources_dir)

    # Save raw results
    results_file = output_dir / f"{args.template_type}_mining_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print(f"📊 Mining results saved to {results_file}")

    # Generate DTCG tokens if we have consolidated tokens
    if results["consolidated_tokens"]:
        generate_dtcg_tokens(results["consolidated_tokens"], args.template_type, output_dir)
    else:
        print("⚠️  No tokens were extracted. Check your source files.")
        return 1

    print("🎉 Style mining completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())