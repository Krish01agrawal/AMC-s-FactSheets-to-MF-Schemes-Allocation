"""
Intelligent Main Processing Pipeline for Multi-Scheme Factsheet Data Extraction
Uses intelligent scheme detection and context-aware parsing for accurate data extraction
"""
import os
import logging
from typing import Dict, List, Any
from pathlib import Path
import json
from datetime import datetime
from bson import ObjectId

from advanced_pdf_extractor import AdvancedPDFExtractor
from intelligent_scheme_detector import IntelligentSchemeDetector
from intelligent_data_parser import IntelligentDataParser
from advanced_mongodb_interface import AdvancedMongoDBInterface
import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('intelligent_factsheet_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IntelligentFactsheetProcessingPipeline:
    """Intelligent pipeline for processing multi-scheme factsheet PDFs with accurate data extraction"""
    
    def __init__(self, factsheets_dir: str = None, output_dir: str = None):
        self.factsheets_dir = factsheets_dir or config.FACTSHEETS_DIR
        self.output_dir = output_dir or config.OUTPUT_DIR
        
        # Initialize components
        self.pdf_extractor = AdvancedPDFExtractor()
        self.scheme_detector = IntelligentSchemeDetector()
        self.data_parser = IntelligentDataParser()
        self.db_interface = None
        
        # Processing statistics
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0,
            'total_schemes_found': 0,
            'new_schemes_inserted': 0,
            'existing_schemes_skipped': 0,
            'processing_errors': []
        }
    
    def initialize_database(self, connection_string: str = None) -> bool:
        """Initialize database connection"""
        try:
            self.db_interface = AdvancedMongoDBInterface(connection_string)
            logger.info("Intelligent database connection initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            return False
    
    def process_all_factsheets(self, save_to_database: bool = True, save_to_json: bool = True) -> Dict[str, Any]:
        """
        Process all factsheet PDFs with intelligent multi-scheme extraction
        
        Args:
            save_to_database: Whether to save data to MongoDB
            save_to_json: Whether to save data to JSON files
            
        Returns:
            Processing results and statistics
        """
        logger.info("Starting intelligent factsheet processing pipeline")
        
        # Get all PDF files
        pdf_files = self.pdf_extractor.get_all_pdf_files(self.factsheets_dir)
        self.stats['total_files'] = len(pdf_files)
        
        if not pdf_files:
            logger.warning("No PDF files found in the factsheets directory")
            return self.stats
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        # Process each PDF file
        all_processed_schemes = []
        
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
                
                # Detect schemes intelligently
                amc_name = self._determine_amc_from_filename(pdf_file)
                detected_schemes = self.scheme_detector.detect_schemes(
                    extracted_data.get('full_text', ''), 
                    amc_name
                )
                
                if not detected_schemes:
                    logger.error(f"No schemes detected in {pdf_file}")
                    self.stats['failed_files'] += 1
                    self.stats['processing_errors'].append({
                        'file': pdf_file,
                        'error': 'No schemes detected',
                        'stage': 'scheme_detection'
                    })
                    continue
                
                # Parse each scheme with intelligent data extraction
                parsed_schemes = []
                for scheme in detected_schemes:
                    try:
                        parsed_scheme = self.data_parser.parse_scheme_data(scheme, extracted_data)
                        if parsed_scheme:
                            parsed_schemes.append(parsed_scheme)
                    except Exception as e:
                        logger.error(f"Error parsing scheme {scheme.get('name', 'Unknown')}: {str(e)}")
                        continue
                
                if not parsed_schemes:
                    logger.error(f"No schemes could be parsed from {pdf_file}")
                    self.stats['failed_files'] += 1
                    self.stats['processing_errors'].append({
                        'file': pdf_file,
                        'error': 'No schemes could be parsed',
                        'stage': 'data_parsing'
                    })
                    continue
                
                # Update statistics
                self.stats['processed_files'] += 1
                self.stats['total_schemes_found'] += len(parsed_schemes)
                
                # Store processed schemes
                all_processed_schemes.extend(parsed_schemes)
                
                # Save to database if enabled
                if save_to_database and self.db_interface:
                    try:
                        inserted_ids = self.db_interface.insert_multiple_schemes(parsed_schemes)
                        self.stats['new_schemes_inserted'] += len(inserted_ids)
                        self.stats['existing_schemes_skipped'] += len(parsed_schemes) - len(inserted_ids)
                        logger.info(f"Saved {len(inserted_ids)} new schemes to database")
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
                        self._save_schemes_to_json(parsed_schemes, pdf_file)
                    except Exception as e:
                        logger.error(f"Failed to save to JSON: {str(e)}")
                
                logger.info(f"Successfully processed {len(parsed_schemes)} schemes from: {Path(pdf_file).name}")
                
            except Exception as e:
                logger.error(f"Unexpected error processing {pdf_file}: {str(e)}")
                self.stats['failed_files'] += 1
                self.stats['processing_errors'].append({
                    'file': pdf_file,
                    'error': str(e),
                    'stage': 'general_processing'
                })
        
        # Generate comprehensive processing report
        self._generate_intelligent_processing_report(all_processed_schemes)
        
        logger.info("Intelligent factsheet processing pipeline completed")
        return self.stats
    
    def process_single_factsheet(self, pdf_file: str, save_to_database: bool = True, save_to_json: bool = True) -> List[Dict[str, Any]]:
        """
        Process a single factsheet PDF with intelligent multi-scheme extraction
        
        Args:
            pdf_file: Path to the PDF file
            save_to_database: Whether to save data to MongoDB
            save_to_json: Whether to save data to JSON file
            
        Returns:
            List of processed scheme data
        """
        logger.info(f"Processing single factsheet: {pdf_file}")
        
        try:
            # Extract text from PDF
            extracted_data = self.pdf_extractor.extract_text_from_pdf(pdf_file)
            
            if 'error' in extracted_data:
                logger.error(f"Failed to extract text from {pdf_file}: {extracted_data['error']}")
                return []
            
            # Detect schemes intelligently
            amc_name = self._determine_amc_from_filename(pdf_file)
            detected_schemes = self.scheme_detector.detect_schemes(
                extracted_data.get('full_text', ''), 
                amc_name
            )
            
            if not detected_schemes:
                logger.error(f"No schemes detected in {pdf_file}")
                return []
            
            # Parse each scheme with intelligent data extraction
            parsed_schemes = []
            for scheme in detected_schemes:
                try:
                    parsed_scheme = self.data_parser.parse_scheme_data(scheme, extracted_data)
                    if parsed_scheme:
                        parsed_schemes.append(parsed_scheme)
                except Exception as e:
                    logger.error(f"Error parsing scheme {scheme.get('name', 'Unknown')}: {str(e)}")
                    continue
            
            # Save to database if enabled
            if save_to_database and self.db_interface:
                try:
                    inserted_ids = self.db_interface.insert_multiple_schemes(parsed_schemes)
                    logger.info(f"Saved {len(inserted_ids)} new schemes to database")
                except Exception as e:
                    logger.error(f"Failed to save to database: {str(e)}")
            
            # Save to JSON if enabled
            if save_to_json:
                try:
                    self._save_schemes_to_json(parsed_schemes, pdf_file)
                except Exception as e:
                    logger.error(f"Failed to save to JSON: {str(e)}")
            
            logger.info(f"Successfully processed {len(parsed_schemes)} schemes from: {Path(pdf_file).name}")
            return parsed_schemes
            
        except Exception as e:
            logger.error(f"Unexpected error processing {pdf_file}: {str(e)}")
            return []
    
    def _determine_amc_from_filename(self, pdf_file: str) -> str:
        """Determine AMC name from filename"""
        filename = Path(pdf_file).name.lower()
        
        if 'hdfc' in filename:
            return 'HDFC Mutual Fund'
        elif 'sbi' in filename:
            return 'SBI Mutual Fund'
        elif 'icici' in filename:
            return 'ICICI Prudential Mutual Fund'
        elif 'axis' in filename:
            return 'Axis Mutual Fund'
        elif 'nippon' in filename:
            return 'Nippon India Mutual Fund'
        
        return 'Unknown AMC'
    
    def _save_schemes_to_json(self, parsed_schemes: List[Dict[str, Any]], pdf_file: str) -> None:
        """Save parsed schemes to JSON file"""
        try:
            # Create output filename
            pdf_filename = Path(pdf_file).stem
            json_filename = f"{pdf_filename}_intelligent_schemes_data.json"
            json_filepath = os.path.join(self.output_dir, json_filename)
            
            # Convert ObjectId to string for JSON serialization
            schemes_for_json = []
            for scheme in parsed_schemes:
                scheme_copy = scheme.copy()
                if '_id' in scheme_copy:
                    scheme_copy['_id'] = str(scheme_copy['_id'])
                schemes_for_json.append(scheme_copy)
            
            # Save to JSON
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(schemes_for_json, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Saved {len(parsed_schemes)} schemes to: {json_filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save schemes to JSON: {str(e)}")
            raise
    
    def _generate_intelligent_processing_report(self, all_processed_schemes: List[Dict[str, Any]]) -> None:
        """Generate comprehensive processing report"""
        try:
            report = {
                'processing_date': datetime.now().isoformat(),
                'statistics': self.stats,
                'processed_schemes': [],
                'summary': {},
                'scheme_analysis': {},
                'data_quality_metrics': {}
            }
            
            # Add scheme summaries
            for scheme in all_processed_schemes:
                basic_info = scheme.get('basic_info', {})
                fund_details = scheme.get('fund_details', {})
                performance_metrics = scheme.get('performance_metrics', {})
                
                scheme_summary = {
                    'scheme_id': str(scheme.get('_id', '')),
                    'scheme_name': basic_info.get('scheme_name', ''),
                    'amc_name': basic_info.get('amc_name', ''),
                    'asset_class': basic_info.get('asset_class', ''),
                    'sub_class': basic_info.get('sub_class', ''),
                    'aum': fund_details.get('aum', ''),
                    'expense_ratio': fund_details.get('expense_ratio', ''),
                    'cagr_3y': performance_metrics.get('cagr_3y', ''),
                    'beta': scheme.get('risk_metrics', {}).get('beta', ''),
                    'sharpe_ratio': scheme.get('risk_metrics', {}).get('sharpe_ratio', '')
                }
                report['processed_schemes'].append(scheme_summary)
            
            # Generate summary statistics
            asset_classes = {}
            sub_classes = {}
            amcs = {}
            
            for scheme in all_processed_schemes:
                basic_info = scheme.get('basic_info', {})
                asset_class = basic_info.get('asset_class', 'Unknown')
                sub_class = basic_info.get('sub_class', 'Unknown')
                amc_name = basic_info.get('amc_name', 'Unknown')
                
                asset_classes[asset_class] = asset_classes.get(asset_class, 0) + 1
                sub_classes[sub_class] = sub_classes.get(sub_class, 0) + 1
                amcs[amc_name] = amcs.get(amc_name, 0) + 1
            
            report['summary'] = {
                'asset_class_distribution': asset_classes,
                'sub_class_distribution': sub_classes,
                'amc_distribution': amcs,
                'total_schemes_processed': len(all_processed_schemes)
            }
            
            # Generate data quality metrics
            report['data_quality_metrics'] = self._calculate_data_quality_metrics(all_processed_schemes)
            
            # Generate scheme analysis
            report['scheme_analysis'] = self._analyze_schemes_intelligent(all_processed_schemes)
            
            # Save report
            report_filename = f"intelligent_processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            report_filepath = os.path.join(self.output_dir, report_filename)
            
            with open(report_filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Intelligent processing report saved to: {report_filepath}")
            
        except Exception as e:
            logger.error(f"Failed to generate intelligent processing report: {str(e)}")
    
    def _calculate_data_quality_metrics(self, schemes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate data quality metrics"""
        total_schemes = len(schemes)
        if total_schemes == 0:
            return {}
        
        metrics = {
            'total_schemes': total_schemes,
            'completeness_scores': {},
            'field_population_rates': {}
        }
        
        # Define key fields to check
        key_fields = [
            'basic_info.scheme_name',
            'basic_info.amc_name',
            'nav_data.regular_growth',
            'fund_details.aum',
            'fund_details.inception_date',
            'fund_details.fund_manager_name',
            'performance_metrics.cagr_3y',
            'risk_metrics.beta',
            'risk_metrics.sharpe_ratio'
        ]
        
        # Calculate field population rates
        for field in key_fields:
            populated_count = 0
            for scheme in schemes:
                if self._get_nested_value(scheme, field) is not None:
                    populated_count += 1
            
            population_rate = (populated_count / total_schemes) * 100
            metrics['field_population_rates'][field] = population_rate
        
        # Calculate overall completeness score
        total_population_rate = sum(metrics['field_population_rates'].values()) / len(key_fields)
        metrics['overall_completeness_score'] = total_population_rate
        
        return metrics
    
    def _get_nested_value(self, data: Dict, key_path: str) -> Any:
        """Get nested value from dictionary using dot notation"""
        keys = key_path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _analyze_schemes_intelligent(self, schemes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze processed schemes for insights with intelligent metrics"""
        try:
            analysis = {
                'performance_insights': {},
                'risk_insights': {},
                'cost_insights': {},
                'top_performers': {},
                'risk_profiles': {},
                'data_extraction_quality': {}
            }
            
            # Performance analysis
            cagr_3y_values = []
            cagr_5y_values = []
            sharpe_ratios = []
            
            for scheme in schemes:
                performance = scheme.get('performance_metrics', {})
                risk_metrics = scheme.get('risk_metrics', {})
                
                if performance.get('cagr_3y'):
                    cagr_3y_values.append(performance['cagr_3y'])
                if performance.get('cagr_5y'):
                    cagr_5y_values.append(performance['cagr_5y'])
                if risk_metrics.get('sharpe_ratio'):
                    sharpe_ratios.append(risk_metrics['sharpe_ratio'])
            
            if cagr_3y_values:
                analysis['performance_insights']['avg_cagr_3y'] = sum(cagr_3y_values) / len(cagr_3y_values)
                analysis['performance_insights']['max_cagr_3y'] = max(cagr_3y_values)
                analysis['performance_insights']['min_cagr_3y'] = min(cagr_3y_values)
            
            if cagr_5y_values:
                analysis['performance_insights']['avg_cagr_5y'] = sum(cagr_5y_values) / len(cagr_5y_values)
                analysis['performance_insights']['max_cagr_5y'] = max(cagr_5y_values)
                analysis['performance_insights']['min_cagr_5y'] = min(cagr_5y_values)
            
            if sharpe_ratios:
                analysis['risk_insights']['avg_sharpe_ratio'] = sum(sharpe_ratios) / len(sharpe_ratios)
                analysis['risk_insights']['max_sharpe_ratio'] = max(sharpe_ratios)
                analysis['risk_insights']['min_sharpe_ratio'] = min(sharpe_ratios)
            
            # Cost analysis
            expense_ratios = []
            for scheme in schemes:
                fund_details = scheme.get('fund_details', {})
                if fund_details.get('expense_ratio'):
                    expense_ratios.append(fund_details['expense_ratio'])
            
            if expense_ratios:
                analysis['cost_insights']['avg_expense_ratio'] = sum(expense_ratios) / len(expense_ratios)
                analysis['cost_insights']['max_expense_ratio'] = max(expense_ratios)
                analysis['cost_insights']['min_expense_ratio'] = min(expense_ratios)
            
            # Top performers
            schemes_with_cagr = [(s, s.get('performance_metrics', {}).get('cagr_3y', 0)) for s in schemes if s.get('performance_metrics', {}).get('cagr_3y')]
            schemes_with_cagr.sort(key=lambda x: x[1], reverse=True)
            
            analysis['top_performers'] = [
                {
                    'scheme_name': s[0].get('basic_info', {}).get('scheme_name', ''),
                    'amc_name': s[0].get('basic_info', {}).get('amc_name', ''),
                    'cagr_3y': s[1]
                }
                for s in schemes_with_cagr[:5]
            ]
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze schemes intelligently: {str(e)}")
            return {}
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get current processing statistics"""
        return self.stats.copy()
    
    def reset_statistics(self) -> None:
        """Reset processing statistics"""
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0,
            'total_schemes_found': 0,
            'new_schemes_inserted': 0,
            'existing_schemes_skipped': 0,
            'processing_errors': []
        }
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            if self.db_interface:
                self.db_interface.close_connection()
            logger.info("Intelligent pipeline cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

def main():
    """Main function to run the intelligent processing pipeline"""
    try:
        # Initialize pipeline
        pipeline = IntelligentFactsheetProcessingPipeline()
        
        # Initialize database connection
        if not pipeline.initialize_database():
            logger.warning("Database connection failed, continuing with JSON output only")
        
        # Process all factsheets
        results = pipeline.process_all_factsheets(
            save_to_database=True,
            save_to_json=True
        )
        
        # Print results
        print("\n" + "="*60)
        print("INTELLIGENT FACTSHEET PROCESSING RESULTS")
        print("="*60)
        print(f"Total files found: {results['total_files']}")
        print(f"Successfully processed: {results['processed_files']}")
        print(f"Failed files: {results['failed_files']}")
        print(f"Total schemes found: {results['total_schemes_found']}")
        print(f"New schemes inserted: {results['new_schemes_inserted']}")
        print(f"Existing schemes skipped: {results['existing_schemes_skipped']}")
        
        if results['processing_errors']:
            print(f"\nProcessing errors: {len(results['processing_errors'])}")
            for error in results['processing_errors']:
                print(f"  - {error['file']}: {error['error']}")
        
        print("="*60)
        
    except Exception as e:
        logger.error(f"Intelligent pipeline execution failed: {str(e)}")
        raise
    finally:
        if 'pipeline' in locals():
            pipeline.cleanup()

if __name__ == "__main__":
    main()
