# Quick Start Guide - PlutoMoney Factsheet Extraction System

## 🚀 Getting Started in 5 Minutes

### 1. Install Dependencies
```bash
cd DatatoDB
pip3 install PyPDF2 pymongo python-dotenv regex python-dateutil tqdm
```

### 2. Start MongoDB (if not running)
```bash
# For macOS with Homebrew
brew services start mongodb-community

# For Linux
sudo systemctl start mongod

# For Windows
net start MongoDB
```

### 3. Run the System
```bash
# Process all factsheets in the factsheets/ directory
python3 main_pipeline.py
```

### 4. View Results
```bash
# Check the output directory
ls output/

# View a sample parsed data file
cat output/*_parsed_data.json | head -50

# View processing report
cat output/processing_report_*.json
```

### 5. Run Analysis
```bash
# Generate comprehensive analysis
python3 demo_analysis.py
```

## 📊 What You Get

### Extracted Data Points (25+ per scheme):
- **Basic Info**: Scheme name, AMC, asset class, inception date
- **NAV Data**: Regular, Growth, IDCW values
- **Fund Details**: AUM, expense ratio, fund manager, benchmark
- **Performance**: CAGR (1Y, 3Y, 5Y, All), turnover ratios
- **Risk Metrics**: Beta, Sharpe ratio, standard deviation
- **Debt Metrics**: YTM, duration, maturity (for debt funds)
- **Portfolio**: Industry allocation, top holdings

### Analysis Features:
- Market overview and trends
- Performance comparison across asset classes
- Risk analysis and profiling
- AMC comparison and benchmarking
- Investment insights and recommendations

## 🔧 System Architecture

```
factsheets/          # Drop your PDF factsheets here
├── AMC1_factsheet.pdf
├── AMC2_factsheet.pdf
└── ...

output/              # Generated files
├── *_parsed_data.json    # Structured data per scheme
├── processing_report_*.json
└── analysis_report_*.json

MongoDB Database:     # Structured storage
├── scheme_data collection
└── Indexed for fast queries
```

## 🎯 Key Features

### ✅ Intelligent PDF Processing
- Multi-page text extraction
- Robust error handling
- Handles various PDF formats

### ✅ Advanced Data Parsing
- 25+ regex patterns for data extraction
- Intelligent asset class classification
- Context-aware parsing

### ✅ Scalable Database Design
- MongoDB with proper indexing
- Structured schema for easy queries
- Aggregation pipelines for analysis

### ✅ Comprehensive Analysis
- Market trends identification
- Performance benchmarking
- Risk assessment
- Investment recommendations

## 📈 Sample Output

### Processing Results:
```
Total files found: 5
Successfully processed: 5
Failed files: 0
Schemes extracted: 5
Database inserts: 5
```

### Analysis Sample:
```
MARKET OVERVIEW
Total Schemes: 5
Total AMCs: 5
Estimated Total AUM: 896.93 Cr
Average Expense Ratio: 33.8%

PERFORMANCE ANALYSIS
Equity Funds:
  Average 3Y CAGR: 15.2%
  Best 3Y CAGR: 18.7%
  Average Sharpe Ratio: 0.85
```

## 🔍 Database Queries

### Get all schemes by AMC:
```python
from mongodb_interface import MongoDBInterface
db = MongoDBInterface()
schemes = db.get_schemes_by_amc("HDFC")
```

### Get performance analysis:
```python
analysis = db.get_performance_analysis("equity")
```

### Search schemes:
```python
results = db.search_schemes("large cap equity")
```

## 🛠️ Customization

### Add New Data Points:
1. Update patterns in `data_parser.py`
2. Add extraction logic in `_extract_*` methods
3. Update MongoDB schema if needed

### Add New Analysis:
1. Extend `analysis_engine.py`
2. Add new analysis methods
3. Update report generation

### Handle New PDF Formats:
1. Add patterns to `config.py`
2. Update extraction logic in `pdf_extractor.py`
3. Test with sample files

## 🚨 Troubleshooting

### Common Issues:

1. **MongoDB Connection Error**
   ```bash
   # Check if MongoDB is running
   brew services list | grep mongodb
   # Start if not running
   brew services start mongodb-community
   ```

2. **PDF Extraction Fails**
   - Check PDF file is not corrupted
   - Ensure PDF is text-based (not scanned image)
   - Try with a different PDF file

3. **Missing Dependencies**
   ```bash
   pip3 install -r requirements.txt
   ```

4. **Permission Errors**
   ```bash
   chmod +x *.py
   ```

## 📞 Support

- Check logs in `factsheet_processing.log`
- Review error messages in processing reports
- Test individual components with `test_system.py`

## 🎉 Success!

Your factsheet extraction system is now ready to process any number of AMC factsheets automatically. Just drop new PDFs in the `factsheets/` directory and run the pipeline!

---

**Next Steps:**
- Add more factsheets to test scalability
- Customize analysis for your specific needs
- Set up automated processing schedules
- Build web interface for data visualization
