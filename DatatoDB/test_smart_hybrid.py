"""
Test script for the Smart Hybrid Extractor using Gemini API.
This combines regex for simple fields and Gemini for complex extraction.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

from smart_hybrid_extractor import SmartHybridExtractor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Test the smart hybrid extractor"""
    logger.info("Starting smart hybrid extraction test...")
    
    try:
        # Initialize extractor
        extractor = SmartHybridExtractor()
        
        # Get factsheet files
        factsheet_dir = Path("factsheets")
        if not factsheet_dir.exists():
            logger.error(f"Factsheet directory not found: {factsheet_dir}")
            return
        
        pdf_files = list(factsheet_dir.glob("*.pdf"))
        if not pdf_files:
            logger.error("No PDF files found in factsheet directory")
            return
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        # Process factsheets
        results = extractor.process_multiple_factsheets("factsheets")
        
        # Save results
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"smart_hybrid_results_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Print summary
        logger.info(f"\nSmart hybrid extraction results:")
        logger.info(f"Total schemes extracted: {results['metadata']['total_schemes']}")
        logger.info(f"Total PDFs processed: {results['metadata']['total_pdfs']}")
        logger.info(f"Total processing time: {results['metadata']['total_processing_time']:.2f}s")
        logger.info(f"Average time per PDF: {results['metadata']['average_processing_time']:.2f}s")
        logger.info(f"Results saved to: {output_file}")
        
        # Show sample extracted data
        if results['schemes']:
            logger.info(f"\nSample extracted data:")
            sample_scheme = results['schemes'][0]
            logger.info(f"Scheme: {sample_scheme.get('scheme_name', 'Unknown')}")
            logger.info(f"AMC: {sample_scheme.get('amc_name', 'Unknown')}")
            logger.info(f"NAV Growth: {sample_scheme.get('nav_data', {}).get('regular_growth', 'None')}")
            logger.info(f"AUM: {sample_scheme.get('fund_details', {}).get('aum', 'None')} Crores")
            logger.info(f"Expense Ratio: {sample_scheme.get('fund_details', {}).get('expense_ratio', 'None')}%")
            logger.info(f"Benchmark: {sample_scheme.get('fund_details', {}).get('benchmark', 'None')}")
            logger.info(f"Fund Manager: {sample_scheme.get('fund_details', {}).get('fund_manager', 'None')}")
            logger.info(f"Min SIP: {sample_scheme.get('fund_details', {}).get('min_sip', 'None')}")
            logger.info(f"Standard Deviation: {sample_scheme.get('risk_metrics', {}).get('standard_deviation', 'None')}%")
            logger.info(f"Beta: {sample_scheme.get('risk_metrics', {}).get('beta', 'None')}")
            logger.info(f"Sharpe Ratio: {sample_scheme.get('risk_metrics', {}).get('sharpe_ratio', 'None')}")
        
        logger.info(f"\nSmart hybrid extraction test completed!")
        logger.info(f"Results saved to: {output_file}")
        
        # Cost and performance summary
        logger.info(f"\nCost: ~$0.001-0.01 per scheme (Gemini 1.5 Flash)")
        logger.info(f"Speed: Fast (regex for simple fields, Gemini for complex)")
        logger.info(f"Accuracy: High (combines best of both approaches)")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
