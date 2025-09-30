"""
Main Pipeline for PlutoMoney Factsheet Extraction System
Scalable system for 44+ AMCs with automatic detection and resume capability
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from scalable_amc_extractor import ScalableAMCExtractor
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
    """Scalable processor for factsheet extraction and analysis across 44+ AMCs"""
    
    def __init__(self):
        """Initialize the scalable processor"""
        self.extractor = ScalableAMCExtractor()
        self.db_interface = None
        self.analysis_engine = None
        
        # Processing statistics
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'skipped_files': 0,
            'failed_files': 0,
            'total_schemes': 0,
            'new_schemes': 0,
            'existing_schemes': 0,
            'processing_time': 0,
            'amcs_processed': 0,
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
        """Process all factsheets with scalable AMC detection and resume capability"""
        logger.info("🚀 Starting scalable factsheet processing...")
        
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
        logger.info(f"📁 Found {len(pdf_files)} PDF files")
        
        # Process using scalable extractor
        all_schemes_by_amc = self.extractor.process_all_factsheets("factsheets")
        
        if not all_schemes_by_amc:
            logger.info("ℹ️ No new files to process (all already processed)")
            return {}
        
        # Flatten all schemes
        all_schemes = []
        for amc_schemes in all_schemes_by_amc.values():
            all_schemes.extend(amc_schemes)
        
        self.stats['processed_files'] = len(all_schemes_by_amc)
        self.stats['total_schemes'] = len(all_schemes)
        self.stats['amcs_processed'] = len(all_schemes_by_amc)
        
        logger.info(f"📊 Processed {len(all_schemes_by_amc)} AMCs with {len(all_schemes)} total schemes")
        
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
                self._save_to_json(all_schemes_by_amc)
            except Exception as e:
                logger.error(f"❌ JSON save error: {e}")
        
        # Calculate processing time
        self.stats['processing_time'] = (datetime.now() - start_time).total_seconds()
        
        # Generate summary
        summary = self._generate_summary()
        logger.info("🎉 Scalable processing completed!")
        logger.info(f"📊 Summary: {summary}")
        
        return {
            'schemes_by_amc': all_schemes_by_amc,
            'all_schemes': all_schemes,
            'stats': self.stats,
            'summary': summary
        }
    
    def _save_to_json(self, schemes_by_amc: Dict[str, List[Dict[str, Any]]]):
        """Save schemes to JSON file"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"scalable_extraction_{timestamp}.json"
        
        data = {
            'metadata': {
                'extraction_method': 'scalable_amc',
                'description': 'Scalable extraction for 44+ AMCs with automatic detection',
                'total_amcs': len(schemes_by_amc),
                'total_schemes': sum(len(schemes) for schemes in schemes_by_amc.values()),
                'extraction_date': datetime.now().isoformat(),
                'stats': self.stats
            },
            'schemes_by_amc': schemes_by_amc
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Results saved to: {output_file}")
    
    def _generate_summary(self) -> str:
        """Generate processing summary"""
        return (
            f"{self.stats['amcs_processed']} AMCs processed, "
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
            analysis_file = output_dir / f"scalable_analysis_report_{timestamp}.json"
            
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
        
        if results and results.get('all_schemes'):
            # Generate analysis
            analysis = processor.generate_analysis()
            
            logger.info("🎉 All scalable processing completed successfully!")
            logger.info(f"📁 Check the 'output/' directory for results")
            
        else:
            logger.info("ℹ️ No new schemes were extracted (all files already processed)")
            
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
