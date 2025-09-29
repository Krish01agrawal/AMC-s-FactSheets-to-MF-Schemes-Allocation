"""
Test System for Factsheet Data Extraction
Validates the complete pipeline with sample data
"""
import os
import logging
from pathlib import Path
import json
from datetime import datetime

from main_pipeline import FactsheetProcessingPipeline
from analysis_engine import FactsheetAnalysisEngine
from mongodb_interface import MongoDBInterface

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_pdf_extraction():
    """Test PDF text extraction functionality"""
    logger.info("Testing PDF extraction...")
    
    from pdf_extractor import PDFExtractor
    
    extractor = PDFExtractor()
    factsheets_dir = "/Users/krishagrawal/Desktop/PlutoMoney-PortfolioAllocation-Quant/DatatoDB/factsheets"
    
    # Get first PDF file for testing
    pdf_files = extractor.get_all_pdf_files(factsheets_dir)
    
    if not pdf_files:
        logger.error("No PDF files found for testing")
        return False
    
    test_pdf = pdf_files[0]
    logger.info(f"Testing with: {Path(test_pdf).name}")
    
    # Extract text
    extracted_data = extractor.extract_text_from_pdf(test_pdf)
    
    if 'error' in extracted_data:
        logger.error(f"PDF extraction failed: {extracted_data['error']}")
        return False
    
    # Validate extraction
    if not extracted_data.get('full_text'):
        logger.error("No text extracted from PDF")
        return False
    
    logger.info(f"Successfully extracted {len(extracted_data['full_text'])} characters")
    logger.info(f"Extracted from {extracted_data.get('total_pages', 0)} pages")
    
    return True

def test_data_parsing():
    """Test data parsing functionality"""
    logger.info("Testing data parsing...")
    
    from pdf_extractor import PDFExtractor
    from data_parser import FactsheetDataParser
    
    extractor = PDFExtractor()
    parser = FactsheetDataParser()
    
    factsheets_dir = "/Users/krishagrawal/Desktop/PlutoMoney-PortfolioAllocation-Quant/DatatoDB/factsheets"
    pdf_files = extractor.get_all_pdf_files(factsheets_dir)
    
    if not pdf_files:
        logger.error("No PDF files found for testing")
        return False
    
    test_pdf = pdf_files[0]
    
    # Extract and parse
    extracted_data = extractor.extract_text_from_pdf(test_pdf)
    parsed_data = parser.parse_factsheet(extracted_data)
    
    if not parsed_data:
        logger.error("Data parsing failed")
        return False
    
    # Validate parsed data structure
    required_sections = ['basic_info', 'nav_data', 'fund_details', 'performance_metrics', 'risk_metrics']
    
    for section in required_sections:
        if section not in parsed_data:
            logger.error(f"Missing required section: {section}")
            return False
    
    logger.info("Data parsing validation passed")
    
    # Log some extracted values
    basic_info = parsed_data.get('basic_info', {})
    logger.info(f"Scheme: {basic_info.get('scheme_name', 'N/A')}")
    logger.info(f"AMC: {basic_info.get('amc_name', 'N/A')}")
    
    nav_data = parsed_data.get('nav_data', {})
    logger.info(f"NAV Growth: {nav_data.get('regular_growth', 'N/A')}")
    
    fund_details = parsed_data.get('fund_details', {})
    logger.info(f"AUM: {fund_details.get('aum', 'N/A')}")
    logger.info(f"Expense Ratio: {fund_details.get('expense_ratio', 'N/A')}")
    
    return True

def test_database_operations():
    """Test database operations"""
    logger.info("Testing database operations...")
    
    try:
        # Test database connection
        db_interface = MongoDBInterface()
        
        # Test basic operations
        stats = db_interface.get_database_stats()
        logger.info(f"Database stats: {stats}")
        
        # Test data insertion with sample data
        sample_data = {
            'basic_info': {
                'scheme_name': 'Test Scheme',
                'amc_name': 'Test AMC',
                'file_name': 'test.pdf',
                'extraction_date': datetime.now().isoformat()
            },
            'nav_data': {
                'regular_growth': 100.0
            },
            'fund_details': {
                'aum': 1000.0,
                'expense_ratio': 1.5
            },
            'asset_classification': {
                'asset_class': 'equity',
                'sub_class': 'large cap'
            }
        }
        
        # Insert test data
        document_id = db_interface.insert_scheme_data(sample_data)
        logger.info(f"Inserted test document: {document_id}")
        
        # Retrieve test data
        retrieved_data = db_interface.get_scheme_by_id(document_id)
        if retrieved_data:
            logger.info("Successfully retrieved test data")
        else:
            logger.error("Failed to retrieve test data")
            return False
        
        # Clean up test data
        db_interface.delete_scheme(document_id)
        logger.info("Cleaned up test data")
        
        db_interface.close_connection()
        return True
        
    except Exception as e:
        logger.error(f"Database test failed: {str(e)}")
        return False

def test_complete_pipeline():
    """Test the complete processing pipeline"""
    logger.info("Testing complete pipeline...")
    
    try:
        # Initialize pipeline
        pipeline = FactsheetProcessingPipeline()
        
        # Test without database (JSON only)
        results = pipeline.process_all_factsheets(
            save_to_database=False,
            save_to_json=True
        )
        
        logger.info(f"Pipeline results: {results}")
        
        # Validate results
        if results['processed_files'] > 0:
            logger.info("Pipeline test passed")
            return True
        else:
            logger.error("No files were processed")
            return False
            
    except Exception as e:
        logger.error(f"Pipeline test failed: {str(e)}")
        return False

def test_analysis_engine():
    """Test analysis engine functionality"""
    logger.info("Testing analysis engine...")
    
    try:
        # Initialize analysis engine
        analysis_engine = FactsheetAnalysisEngine()
        
        # Test analysis generation
        analysis = analysis_engine.get_comprehensive_analysis()
        
        if analysis:
            logger.info("Analysis generation successful")
            
            # Check key analysis sections
            required_sections = ['market_overview', 'performance_analysis', 'risk_analysis']
            for section in required_sections:
                if section in analysis:
                    logger.info(f"Analysis section '{section}' generated")
                else:
                    logger.warning(f"Analysis section '{section}' missing")
            
            return True
        else:
            logger.error("Analysis generation failed")
            return False
            
    except Exception as e:
        logger.error(f"Analysis engine test failed: {str(e)}")
        return False

def run_all_tests():
    """Run all system tests"""
    logger.info("="*50)
    logger.info("STARTING SYSTEM TESTS")
    logger.info("="*50)
    
    tests = [
        ("PDF Extraction", test_pdf_extraction),
        ("Data Parsing", test_data_parsing),
        ("Database Operations", test_database_operations),
        ("Complete Pipeline", test_complete_pipeline),
        ("Analysis Engine", test_analysis_engine)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\nRunning {test_name} test...")
        try:
            result = test_func()
            results[test_name] = "PASSED" if result else "FAILED"
            logger.info(f"{test_name} test: {results[test_name]}")
        except Exception as e:
            results[test_name] = f"ERROR: {str(e)}"
            logger.error(f"{test_name} test failed with error: {str(e)}")
    
    # Print summary
    logger.info("\n" + "="*50)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("="*50)
    
    for test_name, result in results.items():
        status = "✅" if result == "PASSED" else "❌"
        logger.info(f"{status} {test_name}: {result}")
    
    # Overall result
    passed_tests = sum(1 for result in results.values() if result == "PASSED")
    total_tests = len(results)
    
    logger.info(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        logger.info("🎉 All tests passed! System is ready for use.")
    else:
        logger.warning("⚠️  Some tests failed. Please review the errors above.")
    
    return results

def main():
    """Main test function"""
    try:
        results = run_all_tests()
        
        # Save test results
        results_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Test results saved to: {results_file}")
        
    except Exception as e:
        logger.error(f"Test execution failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()
