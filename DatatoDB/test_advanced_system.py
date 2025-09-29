"""
Test System for Advanced Multi-Scheme Factsheet Data Extraction
Validates the complete advanced pipeline with multi-scheme detection
"""
import os
import logging
from pathlib import Path
import json
from datetime import datetime

from advanced_pdf_extractor import AdvancedPDFExtractor
from multi_scheme_parser import MultiSchemeDataParser
from advanced_mongodb_interface import AdvancedMongoDBInterface
from advanced_main_pipeline import AdvancedFactsheetProcessingPipeline

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_advanced_pdf_extraction():
    """Test advanced PDF text extraction with multi-scheme detection"""
    logger.info("Testing advanced PDF extraction...")
    
    extractor = AdvancedPDFExtractor()
    factsheets_dir = "/Users/krishagrawal/Desktop/PlutoMoney-PortfolioAllocation-Quant/DatatoDB/factsheets"
    
    # Get first PDF file for testing
    pdf_files = extractor.get_all_pdf_files(factsheets_dir)
    
    if not pdf_files:
        logger.error("No PDF files found for testing")
        return False
    
    test_pdf = pdf_files[0]
    logger.info(f"Testing with: {Path(test_pdf).name}")
    
    # Extract text and detect schemes
    extracted_data = extractor.extract_text_from_pdf(test_pdf)
    
    if 'error' in extracted_data:
        logger.error(f"PDF extraction failed: {extracted_data['error']}")
        return False
    
    # Validate extraction
    if not extracted_data.get('full_text'):
        logger.error("No text extracted from PDF")
        return False
    
    schemes = extracted_data.get('schemes', [])
    if not schemes:
        logger.error("No schemes detected in PDF")
        return False
    
    logger.info(f"Successfully extracted {len(extracted_data.get('full_text', ''))} characters")
    logger.info(f"Detected {len(schemes)} schemes")
    logger.info(f"Extracted from {extracted_data.get('metadata', {}).get('total_pages', 0)} pages")
    
    # Log detected schemes
    for i, scheme in enumerate(schemes[:3], 1):  # Show first 3 schemes
        logger.info(f"Scheme {i}: {scheme.get('name', 'Unknown')}")
    
    return True

def test_multi_scheme_parsing():
    """Test multi-scheme data parsing functionality"""
    logger.info("Testing multi-scheme data parsing...")
    
    extractor = AdvancedPDFExtractor()
    parser = MultiSchemeDataParser()
    
    factsheets_dir = "/Users/krishagrawal/Desktop/PlutoMoney-PortfolioAllocation-Quant/DatatoDB/factsheets"
    pdf_files = extractor.get_all_pdf_files(factsheets_dir)
    
    if not pdf_files:
        logger.error("No PDF files found for testing")
        return False
    
    test_pdf = pdf_files[0]
    
    # Extract and parse
    extracted_data = extractor.extract_text_from_pdf(test_pdf)
    parsed_schemes = parser.parse_multi_scheme_factsheet(extracted_data)
    
    if not parsed_schemes:
        logger.error("Multi-scheme parsing failed")
        return False
    
    # Validate parsed data structure
    required_sections = ['basic_info', 'nav_data', 'fund_details', 'performance_metrics', 'risk_metrics']
    
    for i, scheme in enumerate(parsed_schemes[:2]):  # Check first 2 schemes
        logger.info(f"Validating scheme {i+1}: {scheme.get('basic_info', {}).get('scheme_name', 'Unknown')}")
        
        for section in required_sections:
            if section not in scheme:
                logger.error(f"Missing required section: {section}")
                return False
        
        # Log some extracted values
        basic_info = scheme.get('basic_info', {})
        logger.info(f"  Scheme: {basic_info.get('scheme_name', 'N/A')}")
        logger.info(f"  AMC: {basic_info.get('amc_name', 'N/A')}")
        logger.info(f"  Asset Class: {basic_info.get('asset_class', 'N/A')}")
        logger.info(f"  Sub Class: {basic_info.get('sub_class', 'N/A')}")
        
        nav_data = scheme.get('nav_data', {})
        logger.info(f"  NAV Growth: {nav_data.get('regular_growth', 'N/A')}")
        
        fund_details = scheme.get('fund_details', {})
        logger.info(f"  AUM: {fund_details.get('aum', 'N/A')}")
        logger.info(f"  Expense Ratio: {fund_details.get('expense_ratio', 'N/A')}")
    
    logger.info("Multi-scheme data parsing validation passed")
    return True

def test_advanced_database_operations():
    """Test advanced database operations with multi-scheme data"""
    logger.info("Testing advanced database operations...")
    
    try:
        # Test database connection
        db_interface = AdvancedMongoDBInterface()
        
        # Test basic operations
        stats = db_interface.get_database_stats()
        logger.info(f"Database stats: {stats}")
        
        # Test data insertion with sample multi-scheme data
        sample_schemes = [
            {
                'basic_info': {
                    'scheme_name': 'Test Equity Fund',
                    'amc_name': 'Test AMC',
                    'asset_class': 'equity',
                    'sub_class': 'large cap',
                    'scheme_type': 'Growth'
                },
                'nav_data': {
                    'regular_growth': 100.0,
                    'regular_idcw': 95.0
                },
                'fund_details': {
                    'aum': 1000.0,
                    'expense_ratio': 1.5,
                    'inception_date': '01/01/2020'
                },
                'performance_metrics': {
                    'cagr_3y': 12.5,
                    'cagr_5y': 15.2
                },
                'risk_metrics': {
                    'beta': 1.2,
                    'sharpe_ratio': 0.85
                }
            },
            {
                'basic_info': {
                    'scheme_name': 'Test Debt Fund',
                    'amc_name': 'Test AMC',
                    'asset_class': 'debt',
                    'sub_class': 'corporate bond',
                    'scheme_type': 'Growth'
                },
                'nav_data': {
                    'regular_growth': 50.0,
                    'regular_idcw': 48.0
                },
                'fund_details': {
                    'aum': 500.0,
                    'expense_ratio': 0.8,
                    'inception_date': '01/01/2019'
                },
                'performance_metrics': {
                    'cagr_3y': 8.5,
                    'cagr_5y': 9.2
                },
                'risk_metrics': {
                    'beta': 0.5,
                    'sharpe_ratio': 1.2
                }
            }
        ]
        
        # Insert test data
        inserted_ids = db_interface.insert_multiple_schemes(sample_schemes)
        logger.info(f"Inserted {len(inserted_ids)} test schemes")
        
        # Test retrieval
        schemes_by_amc = db_interface.get_schemes_by_amc("Test AMC")
        logger.info(f"Retrieved {len(schemes_by_amc)} schemes by AMC")
        
        # Test criteria-based search
        criteria = {
            'asset_class': 'equity',
            'min_cagr_3y': 10.0
        }
        matching_schemes = db_interface.get_schemes_by_criteria(criteria)
        logger.info(f"Found {len(matching_schemes)} schemes matching criteria")
        
        # Clean up test data
        for scheme_id in inserted_ids:
            db_interface.delete_scheme(scheme_id)
        logger.info("Cleaned up test data")
        
        db_interface.close_connection()
        return True
        
    except Exception as e:
        logger.error(f"Advanced database test failed: {str(e)}")
        return False

def test_complete_advanced_pipeline():
    """Test the complete advanced processing pipeline"""
    logger.info("Testing complete advanced pipeline...")
    
    try:
        # Initialize pipeline
        pipeline = AdvancedFactsheetProcessingPipeline()
        
        # Test without database (JSON only)
        results = pipeline.process_all_factsheets(
            save_to_database=False,
            save_to_json=True
        )
        
        logger.info(f"Advanced pipeline results: {results}")
        
        # Validate results
        if results['processed_files'] > 0 and results['total_schemes_found'] > 0:
            logger.info("Advanced pipeline test passed")
            return True
        else:
            logger.error("No files or schemes were processed")
            return False
            
    except Exception as e:
        logger.error(f"Advanced pipeline test failed: {str(e)}")
        return False

def test_scheme_deduplication():
    """Test scheme deduplication functionality"""
    logger.info("Testing scheme deduplication...")
    
    try:
        db_interface = AdvancedMongoDBInterface()
        
        # Create sample scheme data
        sample_scheme = {
            'basic_info': {
                'scheme_name': 'Deduplication Test Fund',
                'amc_name': 'Test AMC',
                'asset_class': 'equity',
                'sub_class': 'large cap'
            },
            'fund_details': {
                'inception_date': '01/01/2020'
            }
        }
        
        # Insert first time
        inserted_id_1 = db_interface.insert_scheme_data(sample_scheme)
        logger.info(f"First insertion: {inserted_id_1}")
        
        # Try to insert same scheme again
        inserted_id_2 = db_interface.insert_scheme_data(sample_scheme)
        logger.info(f"Second insertion: {inserted_id_2}")
        
        # Should return the same ID (deduplication working)
        if inserted_id_1 == inserted_id_2:
            logger.info("Deduplication working correctly")
            success = True
        else:
            logger.error("Deduplication failed")
            success = False
        
        # Clean up
        db_interface.delete_scheme(inserted_id_1)
        db_interface.close_connection()
        
        return success
        
    except Exception as e:
        logger.error(f"Deduplication test failed: {str(e)}")
        return False

def run_all_advanced_tests():
    """Run all advanced system tests"""
    logger.info("="*60)
    logger.info("STARTING ADVANCED SYSTEM TESTS")
    logger.info("="*60)
    
    tests = [
        ("Advanced PDF Extraction", test_advanced_pdf_extraction),
        ("Multi-Scheme Data Parsing", test_multi_scheme_parsing),
        ("Advanced Database Operations", test_advanced_database_operations),
        ("Complete Advanced Pipeline", test_complete_advanced_pipeline),
        ("Scheme Deduplication", test_scheme_deduplication)
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
    logger.info("\n" + "="*60)
    logger.info("ADVANCED TEST RESULTS SUMMARY")
    logger.info("="*60)
    
    for test_name, result in results.items():
        status = "✅" if result == "PASSED" else "❌"
        logger.info(f"{status} {test_name}: {result}")
    
    # Overall result
    passed_tests = sum(1 for result in results.values() if result == "PASSED")
    total_tests = len(results)
    
    logger.info(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        logger.info("🎉 All advanced tests passed! System is ready for production use.")
    else:
        logger.warning("⚠️  Some tests failed. Please review the errors above.")
    
    return results

def main():
    """Main test function"""
    try:
        results = run_all_advanced_tests()
        
        # Save test results
        results_file = f"advanced_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Advanced test results saved to: {results_file}")
        
    except Exception as e:
        logger.error(f"Advanced test execution failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()
