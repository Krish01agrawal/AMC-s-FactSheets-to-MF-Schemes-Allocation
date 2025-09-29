# PlutoMoney Factsheet Data Extraction System

A comprehensive, intelligent, and scalable system for extracting and analyzing financial data from Asset Management Company (AMC) factsheets.

## Features

- **Robust PDF Processing**: Multi-page text extraction with intelligent parsing
- **Comprehensive Data Extraction**: Extracts 25+ data points including NAV, AUM, performance metrics, risk indicators, and portfolio details
- **Intelligent Pattern Matching**: Advanced regex patterns for accurate data extraction
- **MongoDB Integration**: Structured data storage with indexing for fast queries
- **Analysis Engine**: Advanced analytics and investment insights
- **Scalable Architecture**: Handles multiple PDFs dynamically without code changes
- **Error Handling**: Comprehensive error handling and logging

## Data Points Extracted

### Basic Information
- Asset class and sub-class
- Scheme name and AMC name
- Type of scheme
- Date of allotment (inception date)

### NAV Data
- NAV value (Regular ITC)
- NAV value (Regular Growth, IDCW Plan)

### Fund Details
- AUM (Assets Under Management)
- Fund manager name, tenure, and experience
- Benchmark
- Options (Regular: IDCW, Growth)
- Exit load structure (30 days, 30-90 days, after 90 days)
- Minimum Monthly SIP investment amount
- Expense Ratio

### Performance Metrics
- CAGR (1Y, 3Y, 5Y, All)
- Equity portfolio turnover
- Total turnover

### Risk Metrics
- Standard deviation
- Beta
- Sharpe ratio
- Riskometer (Risk Profile)

### Debt Fund Metrics
- Yield to Maturity
- Modified Duration
- Average Maturity Years
- Macaulay Duration
- Years of Maturity
- Composition by rating

### Portfolio Data
- Portfolio classification by industry allocation
- Portfolio detail (top holdings, asset allocation)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd DatatoDB
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up MongoDB**
   - Install MongoDB locally or use MongoDB Atlas
   - Update the connection string in `config.py` or create a `.env` file

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your MongoDB connection details
   ```

## Usage

### Basic Usage

```python
from main_pipeline import FactsheetProcessingPipeline

# Initialize pipeline
pipeline = FactsheetProcessingPipeline()

# Initialize database connection
pipeline.initialize_database()

# Process all factsheets
results = pipeline.process_all_factsheets(
    save_to_database=True,
    save_to_json=True
)

print(f"Processed {results['processed_files']} files successfully")
```

### Advanced Usage

```python
from main_pipeline import FactsheetProcessingPipeline
from analysis_engine import FactsheetAnalysisEngine

# Process factsheets
pipeline = FactsheetProcessingPipeline()
pipeline.initialize_database()
pipeline.process_all_factsheets()

# Generate analysis
analysis_engine = FactsheetAnalysisEngine()
analysis = analysis_engine.get_comprehensive_analysis()

# Generate report
report_file = analysis_engine.generate_analysis_report()
```

### Command Line Usage

```bash
# Process all factsheets
python main_pipeline.py

# The system will:
# 1. Extract text from all PDFs in the factsheets/ directory
# 2. Parse and structure the data
# 3. Save to MongoDB
# 4. Generate JSON output files
# 5. Create processing reports
```

## Project Structure

```
DatatoDB/
├── factsheets/                 # PDF factsheets directory
├── output/                     # Generated JSON files and reports
├── config.py                   # Configuration settings
├── pdf_extractor.py           # PDF text extraction module
├── data_parser.py             # Intelligent data parsing
├── mongodb_interface.py       # Database operations
├── main_pipeline.py           # Main processing pipeline
├── analysis_engine.py         # Analysis and insights
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Database Schema

The system stores data in MongoDB with the following structure:

```json
{
  "_id": "unique_scheme_identifier",
  "basic_info": {
    "scheme_name": "Scheme Name",
    "amc_name": "AMC Name",
    "file_name": "factsheet.pdf",
    "extraction_date": "2024-01-01T00:00:00"
  },
  "nav_data": {
    "regular_itc": 150.25,
    "regular_growth": 150.25,
    "idcw": 150.25
  },
  "fund_details": {
    "aum": 1250.5,
    "inception_date": "01/01/2020",
    "fund_manager": "Manager Name",
    "benchmark": "Nifty 50",
    "expense_ratio": 1.5
  },
  "performance_metrics": {
    "cagr_1y": 12.5,
    "cagr_3y": 15.2,
    "cagr_5y": 18.7
  },
  "risk_metrics": {
    "standard_deviation": 18.5,
    "beta": 1.2,
    "sharpe_ratio": 0.85
  },
  "asset_classification": {
    "asset_class": "equity",
    "sub_class": "large cap",
    "scheme_type": "Growth"
  }
}
```

## Analysis Features

The analysis engine provides:

### Market Overview
- Total schemes and AMCs
- Asset class distribution
- Average expense ratios
- Market size estimates

### Performance Analysis
- CAGR comparisons across asset classes
- Sharpe ratio analysis
- Risk-adjusted returns
- Top performers identification

### Risk Analysis
- Beta distribution
- Standard deviation analysis
- Riskometer distribution
- Risk-return profiles

### AMC Comparison
- Scheme count by AMC
- Average AUM comparison
- Expense ratio analysis
- Performance benchmarking

### Investment Insights
- Market trends identification
- Performance insights
- Risk assessment
- Cost analysis
- Diversification recommendations

## Error Handling

The system includes comprehensive error handling:

- **PDF Extraction Errors**: Handles corrupted or unreadable PDFs
- **Parsing Errors**: Graceful handling of missing or malformed data
- **Database Errors**: Connection and insertion error handling
- **Validation**: Data validation and cleaning
- **Logging**: Detailed logging for debugging and monitoring

## Scalability

The system is designed for scalability:

- **Dynamic PDF Processing**: Automatically processes new PDFs without code changes
- **Database Indexing**: Optimized queries with proper indexing
- **Modular Architecture**: Easy to extend with new data points or analysis
- **Batch Processing**: Efficient processing of multiple files
- **Memory Management**: Optimized for large datasets

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions:
- Create an issue in the repository
- Check the logs in `factsheet_processing.log`
- Review the generated reports in the `output/` directory

## Future Enhancements

- [ ] Web interface for data visualization
- [ ] Real-time data updates
- [ ] Machine learning for better data extraction
- [ ] API endpoints for data access
- [ ] Automated report generation
- [ ] Integration with external data sources
