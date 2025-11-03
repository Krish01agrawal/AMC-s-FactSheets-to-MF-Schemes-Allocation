"""
Normalized JSON Schema for Mutual Fund Scheme Data
This module defines the target schema and validation rules for extracted data.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json


@dataclass
class AUMData:
    """Assets Under Management data"""
    amountCr: Optional[float] = None
    asOf: str = ""
    sourceSpan: str = ""


@dataclass
class FundManager:
    """Fund Manager information"""
    name: str = ""
    role: str = ""  # e.g., "Equity", "Debt", "Lead"
    since: str = ""  # dd/mm/yyyy
    experience: str = ""  # e.g., "15 years"
    sourceSpan: str = ""


@dataclass
class Options:
    """Investment options available"""
    regular: List[str] = field(default_factory=list)  # ["Growth", "IDCW"]
    direct: List[str] = field(default_factory=list)   # ["Growth", "IDCW"]


@dataclass
class ExpenseRatio:
    """Total Expense Ratio"""
    regular: Optional[float] = None  # %
    direct: Optional[float] = None   # %
    sourceSpan: str = ""


@dataclass
class RiskMetrics:
    """Risk and volatility metrics"""
    standardDeviation: Optional[float] = None
    beta: Optional[float] = None
    sharpeRatio: Optional[float] = None
    sourceSpan: str = ""


@dataclass
class Turnover:
    """Portfolio turnover metrics"""
    equityPortfolioTurnover: Optional[float] = None  # times
    totalTurnover: Optional[float] = None            # times
    sourceSpan: str = ""


@dataclass
class MarketCapAllocation:
    """Market cap allocation for equity funds"""
    largeCapPct: Optional[float] = None
    midCapPct: Optional[float] = None
    smallCapPct: Optional[float] = None
    otherAssetsPct: Optional[float] = None
    sourceSpan: str = ""


@dataclass
class AssetAllocation:
    """Asset allocation for hybrid funds"""
    equityPct: Optional[float] = None
    debtPct: Optional[float] = None
    cashOthersPct: Optional[float] = None
    sourceSpan: str = ""


@dataclass
class NAV:
    """Net Asset Value"""
    asOf: str = ""
    regularGrowth: Optional[float] = None
    regularIDCW: Optional[float] = None
    directGrowth: Optional[float] = None
    directIDCW: Optional[float] = None
    sourceSpan: str = ""


@dataclass
class ExitLoad:
    """Exit load structure"""
    under30Days: str = ""
    days30To90: str = ""
    after90Days: str = ""
    other: List[str] = field(default_factory=list)  # non-standard slabs
    sourceSpan: str = ""


@dataclass
class CAGR:
    """Compound Annual Growth Rate"""
    oneY: Optional[float] = None      # %
    threeY: Optional[float] = None    # %
    fiveY: Optional[float] = None     # %
    sinceInception: Optional[float] = None  # %
    sourceSpan: str = ""


@dataclass
class RatingComposition:
    """Credit rating composition for debt funds"""
    AAA_SovPct: Optional[float] = None    # AAA + Sovereign
    AA_Pct: Optional[float] = None        # AA+, AA, AA-
    A_and_belowPct: Optional[float] = None  # A and below
    othersPct: Optional[float] = None     # Unrated, Cash, etc.
    ratingSumError: bool = False          # Flag if sum != 100±1
    sourceSpan: str = ""


@dataclass
class DebtMetrics:
    """Debt fund specific metrics"""
    ytmPct: Optional[float] = None                # Yield to Maturity %
    modifiedDurationYears: Optional[float] = None
    averageMaturityYears: Optional[float] = None
    macaulayDurationYears: Optional[float] = None
    ratingComposition: RatingComposition = field(default_factory=RatingComposition)
    sourceSpan: str = ""


@dataclass
class IndustryAllocation:
    """Industry sector allocation"""
    industry: str = ""
    pct: Optional[float] = None


@dataclass
class PortfolioHolding:
    """Individual portfolio holding"""
    name: str = ""
    pct: Optional[float] = None
    assetType: str = ""  # "Equity", "Debt", "Cash"


@dataclass
class Source:
    """Audit trail for extracted data"""
    pdfFile: str = ""
    schemePageHint: str = ""  # page number or section
    asOfPrinted: str = ""     # the "as of" date printed on page
    extractedAt: str = ""     # ISO timestamp of extraction


@dataclass
class NormalizedScheme:
    """
    Normalized Mutual Fund Scheme Data
    This is the final output schema with all fields properly typed and validated.
    """
    schemeName: str = ""
    amc: str = ""
    assetClass: str = ""        # Equity | Debt | Hybrid | FOF | ETF | Index
    subClass: str = ""          # e.g., Large Cap Fund, Dynamic Bond Fund
    typeOfScheme: str = ""      # As printed by AMC page header
    dateOfAllotment: str = ""   # dd/mm/yyyy
    
    aum: AUMData = field(default_factory=AUMData)
    aaum: AUMData = field(default_factory=AUMData)  # optional AAUM
    
    fundManagers: List[FundManager] = field(default_factory=list)
    benchmark: str = ""
    
    options: Options = field(default_factory=Options)
    expenseRatio: ExpenseRatio = field(default_factory=ExpenseRatio)
    riskMetrics: RiskMetrics = field(default_factory=RiskMetrics)
    turnover: Turnover = field(default_factory=Turnover)
    
    marketCapAllocation: MarketCapAllocation = field(default_factory=MarketCapAllocation)
    assetAllocation: AssetAllocation = field(default_factory=AssetAllocation)
    
    nav: NAV = field(default_factory=NAV)
    exitLoad: ExitLoad = field(default_factory=ExitLoad)
    minMonthlySIP: Optional[float] = None  # ₹
    riskometer: str = ""
    
    cagr: CAGR = field(default_factory=CAGR)
    debtMetrics: DebtMetrics = field(default_factory=DebtMetrics)
    
    industryAllocation: List[IndustryAllocation] = field(default_factory=list)
    portfolioHoldings: List[PortfolioHolding] = field(default_factory=list)
    
    source: Source = field(default_factory=Source)
    
    # Validation flags
    validationErrors: List[str] = field(default_factory=list)
    confidence: float = 0.0  # 0-100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding internal fields"""
        data = asdict(self)
        # Remove empty validation errors and source spans for cleaner output
        if not data['validationErrors']:
            del data['validationErrors']
        return data
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def validate(self) -> bool:
        """Validate the extracted data"""
        errors = []
        
        # Required fields
        if not self.schemeName:
            errors.append("Missing schemeName")
        if not self.amc:
            errors.append("Missing amc")
        if not self.assetClass:
            errors.append("Missing assetClass")
        
        # Asset class validation
        valid_asset_classes = ["Equity", "Debt", "Hybrid", "FOF", "ETF", "Index"]
        if self.assetClass and self.assetClass not in valid_asset_classes:
            errors.append(f"Invalid assetClass: {self.assetClass}")
        
        # Date format validation
        if self.dateOfAllotment and not self._is_valid_date(self.dateOfAllotment):
            errors.append(f"Invalid dateOfAllotment format: {self.dateOfAllotment}")
        
        # AUM validation
        if self.aum.amountCr is not None and self.aum.amountCr < 0:
            errors.append("AUM cannot be negative")
        
        # Expense ratio validation
        if self.expenseRatio.regular is not None:
            if self.expenseRatio.regular < 0 or self.expenseRatio.regular > 5:
                errors.append(f"Expense ratio out of range: {self.expenseRatio.regular}")
        
        # Rating composition sum validation
        if self.debtMetrics.ratingComposition:
            rc = self.debtMetrics.ratingComposition
            components = [
                rc.AAA_SovPct or 0,
                rc.AA_Pct or 0,
                rc.A_and_belowPct or 0,
                rc.othersPct or 0
            ]
            total = sum(components)
            if total > 0 and abs(total - 100) > 1:  # Allow 1% tolerance
                self.debtMetrics.ratingComposition.ratingSumError = True
                errors.append(f"Rating composition sum error: {total}%")
        
        self.validationErrors = errors
        return len(errors) == 0
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Validate date format (dd/mm/yyyy)"""
        try:
            datetime.strptime(date_str, "%d/%m/%Y")
            return True
        except ValueError:
            return False
    
    def calculate_confidence(self) -> float:
        """Calculate confidence score based on filled fields"""
        total_fields = 0
        filled_fields = 0
        
        # Core fields (weight: 2x)
        core_fields = [
            self.schemeName, self.amc, self.assetClass, self.subClass,
            self.dateOfAllotment, self.benchmark
        ]
        total_fields += len(core_fields) * 2
        filled_fields += sum(2 for f in core_fields if f)
        
        # Financial fields (weight: 1x)
        financial_checks = [
            self.aum.amountCr is not None,
            self.expenseRatio.regular is not None,
            self.nav.regularGrowth is not None,
            len(self.fundManagers) > 0,
            self.riskometer != "",
            self.cagr.oneY is not None or self.cagr.threeY is not None
        ]
        total_fields += len(financial_checks)
        filled_fields += sum(financial_checks)
        
        # Optional fields (weight: 0.5x)
        optional_checks = [
            len(self.industryAllocation) > 0,
            len(self.portfolioHoldings) > 0,
            self.minMonthlySIP is not None
        ]
        total_fields += len(optional_checks) * 0.5
        filled_fields += sum(optional_checks) * 0.5
        
        if total_fields == 0:
            return 0.0
        
        self.confidence = (filled_fields / total_fields) * 100
        return self.confidence


def create_empty_scheme(scheme_name: str, amc: str) -> NormalizedScheme:
    """Factory function to create an empty normalized scheme"""
    scheme = NormalizedScheme()
    scheme.schemeName = scheme_name
    scheme.amc = amc
    scheme.source.extractedAt = datetime.now().isoformat()
    return scheme

