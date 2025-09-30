"""
Main Pipeline for PlutoMoney Factsheet Extraction System
Clean, production-ready system using Smart Hybrid Extraction (Gemini + Regex)
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from smart_hybrid_extractor import SmartHybridExtractor
from advanced_mongodb_interface import AdvancedMongoDBInterface
from analysis_engine import FactsheetAnalysisEngine
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('factsheet_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PlutoMoneyFactsheetProcessor:
    """Main processor for factsheet extraction and analysis"""
    
    def __init__(self):
        """Initialize the processor"""
        self.extractor = SmartHybridExtractor()
        self.db_interface = None
        self.analysis_engine = None
        
        # Processing statistics
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0,
            'total_schemes': 0,
            'new_schemes': 0,
            'existing_schemes': 0,
            'processing_time': 0,
            'errors': []
        }
    
    def initialize_database(self, connection_string: str = None) -> bool:
        """Initialize database connection"""
        try:
            self.db_interface = AdvancedMongoDBInterface(connection_string)
            self.analysis_engine = FactsheetAnalysisEngine(self.db_interface)
            logger.info("✅ Database connection initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {str(e)}")
            return False
    
    def process_factsheets(self, save_to_db: bool = True, save_to_json: bool = True) -> Dict[str, Any]:
        """Process all factsheets in the factsheets directory"""
        logger.info("🚀 Starting factsheet processing...")
        
        start_time = datetime.now()
        
        # Get factsheet files
        factsheet_dir = Path("factsheets")
        if not factsheet_dir.exists():
            logger.error(f"❌ Factsheet directory not found: {factsheet_dir}")
            return {}
        
        pdf_files = list(factsheet_dir.glob("*.pdf"))
        if not pdf_files:
            logger.error("❌ No PDF files found in factsheet directory")
            return {}
        
        self.stats['total_files'] = len(pdf_files)
        logger.info(f"📁 Found {len(pdf_files)} PDF files to process")
        
        # Process each factsheet
        all_schemes = []
        
        for pdf_file in pdf_files:
            try:
                logger.info(f"📄 Processing: {pdf_file.name}")
                
                # Extract schemes using smart hybrid approach
                schemes = self.extractor.process_factsheet(str(pdf_file))
                
                if schemes:
                    all_schemes.extend(schemes)
                    self.stats['processed_files'] += 1
                    self.stats['total_schemes'] += len(schemes)
                    logger.info(f"✅ Extracted {len(schemes)} schemes from {pdf_file.name}")
                else:
                    self.stats['failed_files'] += 1
                    logger.warning(f"⚠️ No schemes extracted from {pdf_file.name}")
                
            except Exception as e:
                self.stats['failed_files'] += 1
                self.stats['errors'].append(f"{pdf_file.name}: {str(e)}")
                logger.error(f"❌ Error processing {pdf_file.name}: {e}")
        
        # Save to database if requested
        if save_to_db and self.db_interface:
            try:
                logger.info("💾 Saving schemes to database...")
                for scheme in all_schemes:
                    result = self.db_interface.insert_scheme(scheme)
                    if result.get('inserted'):
                        self.stats['new_schemes'] += 1
                    else:
                        self.stats['existing_schemes'] += 1
                
                logger.info(f"✅ Database: {self.stats['new_schemes']} new, {self.stats['existing_schemes']} existing")
                
            except Exception as e:
                logger.error(f"❌ Database save error: {e}")
        
        # Save to JSON if requested
        if save_to_json:
            try:
                self._save_to_json(all_schemes)
            except Exception as e:
                logger.error(f"❌ JSON save error: {e}")
        
        # Calculate processing time
        self.stats['processing_time'] = (datetime.now() - start_time).total_seconds()
        
        # Generate summary
        summary = self._generate_summary()
        logger.info("🎉 Processing completed!")
        logger.info(f"📊 Summary: {summary}")
        
        return {
            'schemes': all_schemes,
            'stats': self.stats,
            'summary': summary
        }
    
    def _save_to_json(self, schemes: List[Dict[str, Any]]):
        """Save schemes to JSON file"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"factsheet_extraction_{timestamp}.json"
        
        data = {
            'metadata': {
                'extraction_method': 'smart_hybrid',
                'description': 'Smart hybrid extraction using Gemini + Regex',
                'total_schemes': len(schemes),
                'extraction_date': datetime.now().isoformat(),
                'stats': self.stats
            },
            'schemes': schemes
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Results saved to: {output_file}")
    
    def _generate_summary(self) -> str:
        """Generate processing summary"""
        return (
            f"{self.stats['processed_files']}/{self.stats['total_files']} files processed, "
            f"{self.stats['total_schemes']} schemes extracted, "
            f"{self.stats['new_schemes']} new, {self.stats['existing_schemes']} existing, "
            f"{self.stats['processing_time']:.2f}s total"
        )
    
    def generate_analysis(self) -> Dict[str, Any]:
        """Generate comprehensive analysis"""
        if not self.analysis_engine:
            logger.error("❌ Analysis engine not initialized")
            return {}
        
        try:
            logger.info("📊 Generating comprehensive analysis...")
            analysis = self.analysis_engine.get_comprehensive_analysis()
            
            # Save analysis
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            analysis_file = output_dir / f"analysis_report_{timestamp}.json"
            
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📊 Analysis saved to: {analysis_file}")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Analysis generation error: {e}")
            return {}

def main():
    """Main entry point"""
    try:
        # Initialize processor
        processor = PlutoMoneyFactsheetProcessor()
        
        # Initialize database
        if not processor.initialize_database():
            logger.warning("⚠️ Database not available, will save to JSON only")
        
        # Process factsheets
        results = processor.process_factsheets(save_to_db=True, save_to_json=True)
        
        if results and results.get('schemes'):
            # Generate analysis
            analysis = processor.generate_analysis()
            
            logger.info("🎉 All processing completed successfully!")
            logger.info(f"📁 Check the 'output/' directory for results")
            
        else:
            logger.error("❌ No schemes were extracted")
            
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
