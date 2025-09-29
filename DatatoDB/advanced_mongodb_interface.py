"""
Advanced MongoDB Interface for Multi-Scheme Data Storage and Retrieval
Handles multiple schemes per factsheet with proper deduplication and ObjectId management
"""
import pymongo
from pymongo import MongoClient
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
from bson import ObjectId
import hashlib
import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedMongoDBInterface:
    """Advanced MongoDB interface for multi-scheme factsheet data management"""
    
    def __init__(self, connection_string: str = None, database_name: str = None):
        self.connection_string = connection_string or config.MONGODB_URI
        self.database_name = database_name or config.DATABASE_NAME
        self.collection_name = config.COLLECTION_NAME
        
        try:
            self.client = MongoClient(self.connection_string)
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            
            # Test connection
            self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB: {self.database_name}")
            
            # Create indexes for better performance
            self._create_advanced_indexes()
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
    
    def _create_advanced_indexes(self) -> None:
        """Create comprehensive database indexes for better query performance"""
        try:
            # Create compound index for common queries
            self.collection.create_index([
                ("basic_info.amc_name", 1),
                ("basic_info.asset_class", 1),
                ("basic_info.sub_class", 1)
            ])
            
            # Create index for scheme name
            self.collection.create_index("basic_info.scheme_name")
            
            # Create index for AMC name
            self.collection.create_index("basic_info.amc_name")
            
            # Create index for asset class
            self.collection.create_index("basic_info.asset_class")
            
            # Create index for sub class
            self.collection.create_index("basic_info.sub_class")
            
            # Create index for extraction date
            self.collection.create_index("basic_info.extraction_date")
            
            # Create index for scheme hash (for deduplication)
            self.collection.create_index("scheme_hash", unique=True)
            
            # Create text index for full-text search
            self.collection.create_index([
                ("basic_info.scheme_name", "text"),
                ("basic_info.amc_name", "text"),
                ("basic_info.asset_class", "text"),
                ("basic_info.sub_class", "text")
            ])
            
            # Create index for performance metrics
            self.collection.create_index("performance_metrics.cagr_3y")
            self.collection.create_index("performance_metrics.cagr_5y")
            
            # Create index for risk metrics
            self.collection.create_index("risk_metrics.beta")
            self.collection.create_index("risk_metrics.sharpe_ratio")
            
            # Create index for fund details
            self.collection.create_index("fund_details.aum")
            self.collection.create_index("fund_details.expense_ratio")
            
            logger.info("Advanced database indexes created successfully")
            
        except Exception as e:
            logger.warning(f"Failed to create indexes: {str(e)}")
    
    def insert_scheme_data(self, scheme_data: Dict[str, Any]) -> str:
        """
        Insert scheme data into MongoDB with deduplication
        
        Args:
            scheme_data: Structured scheme data
            
        Returns:
            Inserted document ID
        """
        try:
            # Generate scheme hash for deduplication
            scheme_hash = self._generate_scheme_hash(scheme_data)
            scheme_data['scheme_hash'] = scheme_hash
            
            # Check if scheme already exists
            existing_scheme = self.collection.find_one({'scheme_hash': scheme_hash})
            
            if existing_scheme:
                logger.info(f"Scheme already exists: {scheme_data.get('basic_info', {}).get('scheme_name', 'Unknown')}")
                return str(existing_scheme['_id'])
            
            # Add metadata
            scheme_data['created_at'] = datetime.now()
            scheme_data['updated_at'] = datetime.now()
            
            # Insert document
            result = self.collection.insert_one(scheme_data)
            
            logger.info(f"Inserted scheme data: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to insert scheme data: {str(e)}")
            raise
    
    def insert_multiple_schemes(self, schemes_data: List[Dict[str, Any]]) -> List[str]:
        """
        Insert multiple schemes with batch processing and deduplication
        
        Args:
            schemes_data: List of structured scheme data
            
        Returns:
            List of inserted document IDs
        """
        try:
            inserted_ids = []
            existing_count = 0
            
            for scheme_data in schemes_data:
                try:
                    # Generate scheme hash for deduplication
                    scheme_hash = self._generate_scheme_hash(scheme_data)
                    scheme_data['scheme_hash'] = scheme_hash
                    
                    # Check if scheme already exists
                    existing_scheme = self.collection.find_one({'scheme_hash': scheme_hash})
                    
                    if existing_scheme:
                        existing_count += 1
                        logger.info(f"Scheme already exists: {scheme_data.get('basic_info', {}).get('scheme_name', 'Unknown')}")
                        continue
                    
                    # Add metadata
                    scheme_data['created_at'] = datetime.now()
                    scheme_data['updated_at'] = datetime.now()
                    
                    # Insert document
                    result = self.collection.insert_one(scheme_data)
                    inserted_ids.append(str(result.inserted_id))
                    
                except Exception as e:
                    logger.error(f"Failed to insert scheme: {str(e)}")
                    continue
            
            logger.info(f"Inserted {len(inserted_ids)} new schemes, {existing_count} already existed")
            return inserted_ids
            
        except Exception as e:
            logger.error(f"Failed to insert multiple schemes: {str(e)}")
            raise
    
    def update_scheme_data(self, scheme_data: Dict[str, Any]) -> bool:
        """
        Update existing scheme data
        
        Args:
            scheme_data: Updated scheme data
            
        Returns:
            True if update successful
        """
        try:
            scheme_hash = self._generate_scheme_hash(scheme_data)
            scheme_data['updated_at'] = datetime.now()
            
            result = self.collection.update_one(
                {'scheme_hash': scheme_hash},
                {'$set': scheme_data},
                upsert=True
            )
            
            logger.info(f"Updated scheme data: {scheme_hash}")
            return result.acknowledged
            
        except Exception as e:
            logger.error(f"Failed to update scheme data: {str(e)}")
            raise
    
    def get_scheme_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get scheme data by document ID"""
        try:
            return self.collection.find_one({'_id': ObjectId(document_id)})
        except Exception as e:
            logger.error(f"Failed to get scheme by ID: {str(e)}")
            return None
    
    def get_schemes_by_amc(self, amc_name: str) -> List[Dict[str, Any]]:
        """Get all schemes by AMC name"""
        try:
            cursor = self.collection.find({'basic_info.amc_name': {'$regex': amc_name, '$options': 'i'}})
            return list(cursor)
        except Exception as e:
            logger.error(f"Failed to get schemes by AMC: {str(e)}")
            return []
    
    def get_schemes_by_asset_class(self, asset_class: str) -> List[Dict[str, Any]]:
        """Get all schemes by asset class"""
        try:
            cursor = self.collection.find({'basic_info.asset_class': asset_class})
            return list(cursor)
        except Exception as e:
            logger.error(f"Failed to get schemes by asset class: {str(e)}")
            return []
    
    def get_schemes_by_sub_class(self, sub_class: str) -> List[Dict[str, Any]]:
        """Get all schemes by sub-class"""
        try:
            cursor = self.collection.find({'basic_info.sub_class': sub_class})
            return list(cursor)
        except Exception as e:
            logger.error(f"Failed to get schemes by sub-class: {str(e)}")
            return []
    
    def search_schemes(self, query: str) -> List[Dict[str, Any]]:
        """Search schemes using text search"""
        try:
            cursor = self.collection.find({'$text': {'$search': query}})
            return list(cursor)
        except Exception as e:
            logger.error(f"Failed to search schemes: {str(e)}")
            return []
    
    def get_schemes_by_criteria(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get schemes based on multiple criteria
        
        Args:
            criteria: Dictionary of search criteria
            
        Returns:
            List of matching schemes
        """
        try:
            query = {}
            
            # Build query based on criteria
            if 'asset_class' in criteria:
                query['basic_info.asset_class'] = criteria['asset_class']
            
            if 'sub_class' in criteria:
                query['basic_info.sub_class'] = criteria['sub_class']
            
            if 'amc_name' in criteria:
                query['basic_info.amc_name'] = {'$regex': criteria['amc_name'], '$options': 'i'}
            
            if 'min_aum' in criteria:
                query['fund_details.aum'] = {'$gte': criteria['min_aum']}
            
            if 'max_expense_ratio' in criteria:
                query['fund_details.expense_ratio'] = {'$lte': criteria['max_expense_ratio']}
            
            if 'min_cagr_3y' in criteria:
                query['performance_metrics.cagr_3y'] = {'$gte': criteria['min_cagr_3y']}
            
            if 'max_beta' in criteria:
                query['risk_metrics.beta'] = {'$lte': criteria['max_beta']}
            
            if 'min_sharpe_ratio' in criteria:
                query['risk_metrics.sharpe_ratio'] = {'$gte': criteria['min_sharpe_ratio']}
            
            cursor = self.collection.find(query)
            return list(cursor)
            
        except Exception as e:
            logger.error(f"Failed to get schemes by criteria: {str(e)}")
            return []
    
    def get_performance_analysis(self, asset_class: str = None) -> Dict[str, Any]:
        """Get performance analysis using aggregation"""
        try:
            pipeline = []
            
            # Match stage
            if asset_class:
                pipeline.append({'$match': {'basic_info.asset_class': asset_class}})
            
            # Group stage for performance metrics
            pipeline.append({
                '$group': {
                    '_id': '$basic_info.asset_class',
                    'avg_cagr_1y': {'$avg': '$performance_metrics.cagr_1y'},
                    'avg_cagr_3y': {'$avg': '$performance_metrics.cagr_3y'},
                    'avg_cagr_5y': {'$avg': '$performance_metrics.cagr_5y'},
                    'avg_sharpe_ratio': {'$avg': '$risk_metrics.sharpe_ratio'},
                    'avg_beta': {'$avg': '$risk_metrics.beta'},
                    'avg_standard_deviation': {'$avg': '$risk_metrics.standard_deviation'},
                    'count': {'$sum': 1}
                }
            })
            
            result = list(self.collection.aggregate(pipeline))
            return result[0] if result else {}
            
        except Exception as e:
            logger.error(f"Failed to get performance analysis: {str(e)}")
            return {}
    
    def get_risk_analysis(self) -> Dict[str, Any]:
        """Get risk analysis across all schemes"""
        try:
            pipeline = [
                {
                    '$group': {
                        '_id': '$risk_metrics.riskometer',
                        'count': {'$sum': 1},
                        'avg_beta': {'$avg': '$risk_metrics.beta'},
                        'avg_standard_deviation': {'$avg': '$risk_metrics.standard_deviation'},
                        'avg_sharpe_ratio': {'$avg': '$risk_metrics.sharpe_ratio'}
                    }
                },
                {'$sort': {'count': -1}}
            ]
            
            result = list(self.collection.aggregate(pipeline))
            return result
            
        except Exception as e:
            logger.error(f"Failed to get risk analysis: {str(e)}")
            return []
    
    def get_amc_comparison(self) -> Dict[str, Any]:
        """Get AMC comparison data"""
        try:
            pipeline = [
                {
                    '$group': {
                        '_id': '$basic_info.amc_name',
                        'scheme_count': {'$sum': 1},
                        'avg_aum': {'$avg': '$fund_details.aum'},
                        'avg_expense_ratio': {'$avg': '$fund_details.expense_ratio'},
                        'schemes': {
                            '$push': {
                                'name': '$basic_info.scheme_name',
                                'asset_class': '$basic_info.asset_class',
                                'sub_class': '$basic_info.sub_class',
                                'aum': '$fund_details.aum'
                            }
                        }
                    }
                },
                {'$sort': {'scheme_count': -1}}
            ]
            
            result = list(self.collection.aggregate(pipeline))
            return result
            
        except Exception as e:
            logger.error(f"Failed to get AMC comparison: {str(e)}")
            return []
    
    def get_top_performers(self, asset_class: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top performing schemes"""
        try:
            query = {}
            if asset_class:
                query['basic_info.asset_class'] = asset_class
            
            cursor = self.collection.find(query).sort('performance_metrics.cagr_3y', -1).limit(limit)
            return list(cursor)
            
        except Exception as e:
            logger.error(f"Failed to get top performers: {str(e)}")
            return []
    
    def delete_scheme(self, document_id: str) -> bool:
        """Delete scheme by document ID"""
        try:
            result = self.collection.delete_one({'_id': ObjectId(document_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to delete scheme: {str(e)}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        try:
            stats = {
                'total_schemes': self.collection.count_documents({}),
                'total_amcs': len(self.collection.distinct('basic_info.amc_name')),
                'asset_class_distribution': {},
                'sub_class_distribution': {},
                'recent_updates': 0
            }
            
            # Get asset class distribution
            pipeline = [
                {
                    '$group': {
                        '_id': '$basic_info.asset_class',
                        'count': {'$sum': 1}
                    }
                }
            ]
            
            asset_distribution = list(self.collection.aggregate(pipeline))
            for item in asset_distribution:
                stats['asset_class_distribution'][item['_id']] = item['count']
            
            # Get sub-class distribution
            pipeline = [
                {
                    '$group': {
                        '_id': '$basic_info.sub_class',
                        'count': {'$sum': 1}
                    }
                }
            ]
            
            sub_class_distribution = list(self.collection.aggregate(pipeline))
            for item in sub_class_distribution:
                stats['sub_class_distribution'][item['_id']] = item['count']
            
            # Get recent updates (last 7 days)
            week_ago = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = week_ago.replace(day=week_ago.day - 7)
            
            stats['recent_updates'] = self.collection.count_documents({
                'updated_at': {'$gte': week_ago}
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {str(e)}")
            return {}
    
    def _generate_scheme_hash(self, scheme_data: Dict[str, Any]) -> str:
        """Generate unique hash for scheme deduplication"""
        try:
            basic_info = scheme_data.get('basic_info', {})
            scheme_name = basic_info.get('scheme_name', '')
            amc_name = basic_info.get('amc_name', '')
            inception_date = scheme_data.get('fund_details', {}).get('inception_date', '')
            
            # Create a unique identifier
            identifier = f"{amc_name}_{scheme_name}_{inception_date}".replace(' ', '_').replace('.', '_')
            return hashlib.md5(identifier.encode()).hexdigest()
            
        except Exception as e:
            logger.error(f"Failed to generate scheme hash: {str(e)}")
            return hashlib.md5(str(datetime.now()).encode()).hexdigest()
    
    def close_connection(self) -> None:
        """Close MongoDB connection"""
        try:
            self.client.close()
            logger.info("MongoDB connection closed")
        except Exception as e:
            logger.error(f"Failed to close MongoDB connection: {str(e)}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connection()
