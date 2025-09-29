"""
Main Processing Pipeline for Factsheet Data Extraction
Orchestrates the entire process from PDF extraction to database storage
"""
import os
import logging
from typing import Dict, List, Any
from pathlib import Path
import json
from datetime import datetime

from pdf_extractor import PDFExtractor
from data_parser import FactsheetDataParser
from mongodb_interface import MongoDBInterface
import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('factsheet_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FactsheetProcessingPipeline:
    """Main pipeline for processing factsheet PDFs"""
    
    def __init__(self, factsheets_dir: str = None, output_dir: str = None):
        self.factsheets_dir = factsheets_dir or config.FACTSHEETS_DIR
        self.output_dir = output_dir or config.OUTPUT_DIR
        
        # Initialize components
        self.pdf_extractor = PDFExtractor()
        self.data_parser = FactsheetDataParser()
        self.db_interface = None
        
        # Processing statistics
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0,
            'extracted_schemes': 0,
            'database_inserts': 0,
            'processing_errors': []
        }
    
    def initialize_database(self, connection_string: str = None) -> bool:
        """Initialize database connection"""
        try:
            self.db_interface = MongoDBInterface(connection_string)
            logger.info("Database connection initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            return False
    
    def process_all_factsheets(self, save_to_database: bool = True, save_to_json: bool = True) -> Dict[str, Any]:
        """
        Process all factsheet PDFs in the directory
        
        Args:
            save_to_database: Whether to save data to MongoDB
            save_to_json: Whether to save data to JSON files
            
        Returns:
            Processing results and statistics
        """
        logger.info("Starting factsheet processing pipeline")
        
        # Get all PDF files
        pdf_files = self.pdf_extractor.get_all_pdf_files(self.factsheets_dir)
        self.stats['total_files'] = len(pdf_files)
        
        if not pdf_files:
            logger.warning("No PDF files found in the factsheets directory")
            return self.stats
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        # Process each PDF file
        all_processed_data = {}
        
        for pdf_file in pdf_files:
            try:
                logger.info(f"Processing: {Path(pdf_file).name}")
                
                # Extract text from PDF
                extracted_data = self.pdf_extractor.extract_text_from_pdf(pdf_file)
                
                if 'error' in extracted_data:
                    logger.error(f"Failed to extract text from {pdf_file}: {extracted_data['error']}")
                    self.stats['failed_files'] += 1
                    self.stats['processing_errors'].append({
                        'file': pdf_file,
                        'error': extracted_data['error'],
                        'stage': 'text_extraction'
                    })
                    continue
                
                # Parse extracted data
                parsed_data = self.data_parser.parse_factsheet(extracted_data)
                
                if not parsed_data:
                    logger.error(f"Failed to parse data from {pdf_file}")
                    self.stats['failed_files'] += 1
                    self.stats['processing_errors'].append({
                        'file': pdf_file,
                        'error': 'Failed to parse extracted data',
                        'stage': 'data_parsing'
                    })
                    continue
                
                # Store processed data
                all_processed_data[pdf_file] = parsed_data
                self.stats['processed_files'] += 1
                self.stats['extracted_schemes'] += 1
                
                # Save to database if enabled
                if save_to_database and self.db_interface:
                    try:
                        document_id = self.db_interface.insert_scheme_data(parsed_data)
                        self.stats['database_inserts'] += 1
                        logger.info(f"Saved to database: {document_id}")
                    except Exception as e:
                        logger.error(f"Failed to save to database: {str(e)}")
                        self.stats['processing_errors'].append({
                            'file': pdf_file,
                            'error': str(e),
                            'stage': 'database_insert'
                        })
                
                # Save to JSON if enabled
                if save_to_json:
                    try:
                        self._save_to_json(parsed_data, pdf_file)
                    except Exception as e:
                        logger.error(f"Failed to save to JSON: {str(e)}")
                
                logger.info(f"Successfully processed: {Path(pdf_file).name}")
                
            except Exception as e:
                logger.error(f"Unexpected error processing {pdf_file}: {str(e)}")
                self.stats['failed_files'] += 1
                self.stats['processing_errors'].append({
                    'file': pdf_file,
                    'error': str(e),
                    'stage': 'general_processing'
                })
        
        # Generate processing report
        self._generate_processing_report(all_processed_data)
        
        logger.info("Factsheet processing pipeline completed")
        return self.stats
    
    def process_single_factsheet(self, pdf_file: str, save_to_database: bool = True, save_to_json: bool = True) -> Dict[str, Any]:
        """
        Process a single factsheet PDF
        
        Args:
            pdf_file: Path to the PDF file
            save_to_database: Whether to save data to MongoDB
            save_to_json: Whether to save data to JSON file
            
        Returns:
            Processed data
        """
        logger.info(f"Processing single factsheet: {pdf_file}")
        
        try:
            # Extract text from PDF
            extracted_data = self.pdf_extractor.extract_text_from_pdf(pdf_file)
            
            if 'error' in extracted_data:
                logger.error(f"Failed to extract text from {pdf_file}: {extracted_data['error']}")
                return {'error': extracted_data['error']}
            
            # Parse extracted data
            parsed_data = self.data_parser.parse_factsheet(extracted_data)
            
            if not parsed_data:
                logger.error(f"Failed to parse data from {pdf_file}")
                return {'error': 'Failed to parse extracted data'}
            
            # Save to database if enabled
            if save_to_database and self.db_interface:
                try:
                    document_id = self.db_interface.insert_scheme_data(parsed_data)
                    logger.info(f"Saved to database: {document_id}")
                except Exception as e:
                    logger.error(f"Failed to save to database: {str(e)}")
            
            # Save to JSON if enabled
            if save_to_json:
                try:
                    self._save_to_json(parsed_data, pdf_file)
                except Exception as e:
                    logger.error(f"Failed to save to JSON: {str(e)}")
            
            logger.info(f"Successfully processed: {Path(pdf_file).name}")
            return parsed_data
            
        except Exception as e:
            logger.error(f"Unexpected error processing {pdf_file}: {str(e)}")
            return {'error': str(e)}
    
    def _save_to_json(self, parsed_data: Dict[str, Any], pdf_file: str) -> None:
        """Save parsed data to JSON file"""
        try:
            # Create output filename
            pdf_filename = Path(pdf_file).stem
            json_filename = f"{pdf_filename}_parsed_data.json"
            json_filepath = os.path.join(self.output_dir, json_filename)
            
            # Save to JSON
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(parsed_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Saved parsed data to: {json_filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save to JSON: {str(e)}")
            raise
    
    def _generate_processing_report(self, all_processed_data: Dict[str, Any]) -> None:
        """Generate processing report"""
        try:
            report = {
                'processing_date': datetime.now().isoformat(),
                'statistics': self.stats,
                'processed_schemes': [],
                'summary': {}
            }
            
            # Add scheme summaries
            for pdf_file, data in all_processed_data.items():
                scheme_summary = {
                    'file': Path(pdf_file).name,
                    'scheme_name': data.get('basic_info', {}).get('scheme_name', ''),
                    'amc_name': data.get('basic_info', {}).get('amc_name', ''),
                    'asset_class': data.get('asset_classification', {}).get('asset_class', ''),
                    'sub_class': data.get('asset_classification', {}).get('sub_class', ''),
                    'aum': data.get('fund_details', {}).get('aum', ''),
                    'expense_ratio': data.get('fund_details', {}).get('expense_ratio', '')
                }
                report['processed_schemes'].append(scheme_summary)
            
            # Generate summary statistics
            asset_classes = {}
            amcs = {}
            
            for data in all_processed_data.values():
                asset_class = data.get('asset_classification', {}).get('asset_class', 'Unknown')
                amc_name = data.get('basic_info', {}).get('amc_name', 'Unknown')
                
                asset_classes[asset_class] = asset_classes.get(asset_class, 0) + 1
                amcs[amc_name] = amcs.get(amc_name, 0) + 1
            
            report['summary'] = {
                'asset_class_distribution': asset_classes,
                'amc_distribution': amcs,
                'total_schemes_processed': len(all_processed_data)
            }
            
            # Save report
            report_filename = f"processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            report_filepath = os.path.join(self.output_dir, report_filename)
            
            with open(report_filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Processing report saved to: {report_filepath}")
            
        except Exception as e:
            logger.error(f"Failed to generate processing report: {str(e)}")
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get current processing statistics"""
        return self.stats.copy()
    
    def reset_statistics(self) -> None:
        """Reset processing statistics"""
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0,
            'extracted_schemes': 0,
            'database_inserts': 0,
            'processing_errors': []
        }
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            if self.db_interface:
                self.db_interface.close_connection()
            logger.info("Pipeline cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

def main():
    """Main function to run the processing pipeline"""
    try:
        # Initialize pipeline
        pipeline = FactsheetProcessingPipeline()
        
        # Initialize database connection
        if not pipeline.initialize_database():
            logger.warning("Database connection failed, continuing with JSON output only")
        
        # Process all factsheets
        results = pipeline.process_all_factsheets(
            save_to_database=True,
            save_to_json=True
        )
        
        # Print results
        print("\n" + "="*50)
        print("FACTSHEET PROCESSING RESULTS")
        print("="*50)
        print(f"Total files found: {results['total_files']}")
        print(f"Successfully processed: {results['processed_files']}")
        print(f"Failed files: {results['failed_files']}")
        print(f"Schemes extracted: {results['extracted_schemes']}")
        print(f"Database inserts: {results['database_inserts']}")
        
        if results['processing_errors']:
            print(f"\nProcessing errors: {len(results['processing_errors'])}")
            for error in results['processing_errors']:
                print(f"  - {error['file']}: {error['error']}")
        
        print("="*50)
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {str(e)}")
        raise
    finally:
        if 'pipeline' in locals():
            pipeline.cleanup()

if __name__ == "__main__":
    main()
