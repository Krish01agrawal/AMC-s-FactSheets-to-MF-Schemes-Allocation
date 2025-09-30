#!/usr/bin/env python3
"""
Test script for Scalable AMC Extractor
Tests the system with current factsheets
"""

import logging
from scalable_amc_extractor import ScalableAMCExtractor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Test the scalable AMC extractor"""
    logger.info("🧪 Testing Scalable AMC Extractor...")
    
    try:
        # Initialize extractor
        extractor = ScalableAMCExtractor()
        
        # Test AMC detection
        logger.info("🔍 Testing AMC detection patterns...")
        logger.info(f"📊 Supported AMCs: {len(extractor.amc_patterns)}")
        
        for amc_name in list(extractor.amc_patterns.keys())[:10]:  # Show first 10
            logger.info(f"   - {amc_name}")
        
        # Process factsheets
        logger.info("🚀 Processing factsheets...")
        results = extractor.process_all_factsheets()
        
        if results:
            total_schemes = sum(len(schemes) for schemes in results.values())
            logger.info(f"✅ Test completed successfully!")
            logger.info(f"📊 Total schemes extracted: {total_schemes}")
            logger.info(f"📊 Total AMCs processed: {len(results)}")
            
            for amc, schemes in results.items():
                logger.info(f"   {amc}: {len(schemes)} schemes")
        else:
            logger.info("ℹ️ No new files to process (all already processed)")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
