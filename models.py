from sqlalchemy import Column, Integer, String, Float, ForeignKey, BigInteger, DateTime
from database import Base
from datetime import datetime

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), unique=True, index=True)
    company_name = Column(String(255))
    cik = Column(String(20))
    form_type = Column(String(10))
    filing_date = Column(String(20))

class FinancialStatement(Base):
    __tablename__ = "financial_statements"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"))
    filing_date = Column(String(20))
    
    revenue = Column(BigInteger, nullable=True)
    cost_of_revenue = Column(BigInteger, nullable=True)
    gross_profit = Column(BigInteger, nullable=True)
    operating_income = Column(BigInteger, nullable=True)
    net_income = Column(BigInteger, nullable=True)
    interest_expense = Column(BigInteger, nullable=True)
    income_tax = Column(BigInteger, nullable=True)
    ebit = Column(BigInteger, nullable=True)
    ebitda = Column(BigInteger, nullable=True)
    
    operating_cash_flow = Column(BigInteger, nullable=True)
    capital_expenditure = Column(BigInteger, nullable=True)
    depreciation = Column(BigInteger, nullable=True)
    free_cash_flow = Column(BigInteger, nullable=True)

class FinancialMetric(Base):
    __tablename__ = "financial_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"))
    filing_date = Column(String(20))
    
    gross_margin = Column(Float, nullable=True)
    operating_margin = Column(Float, nullable=True)
    net_profit_margin = Column(Float, nullable=True)
    roa = Column(Float, nullable=True)
    roe = Column(Float, nullable=True)
    roic = Column(Float, nullable=True)
    ebitda_margin = Column(Float, nullable=True)
    
    current_ratio = Column(Float, nullable=True)
    quick_ratio = Column(Float, nullable=True)
    cash_ratio = Column(Float, nullable=True)
    
    debt_to_equity = Column(Float, nullable=True)
    debt_to_assets = Column(Float, nullable=True)
    interest_coverage_ratio = Column(Float, nullable=True)
    
    price_to_earnings = Column(Float, nullable=True)
    price_to_book = Column(Float, nullable=True)
    price_to_sales = Column(Float, nullable=True)
    enterprise_value = Column(BigInteger, nullable=True)
    ev_to_ebitda = Column(Float, nullable=True)

class GrowthMetric(Base):
    __tablename__ = "growth_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"))
    filing_date = Column(String(20))
    
    revenue_growth_yoy = Column(Float, nullable=True)
    net_income_growth_yoy = Column(Float, nullable=True)
    free_cash_flow_growth = Column(Float, nullable=True)

class AcquisitionIndicator(Base):
    __tablename__ = "acquisition_indicators"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"))
    filing_date = Column(String(20))
    
    financial_distress = Column(Integer, nullable=True)
    valuation_attractiveness = Column(Integer, nullable=True)
    market_position = Column(Integer, nullable=True)
    operational_efficiency = Column(Integer, nullable=True)

class Metadata(Base):
    __tablename__ = "metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"))
    filing_date = Column(String(20))
    
    data_source = Column(String(100))
    currency = Column(String(10))
    units = Column(String(20))
    extraction_timestamp = Column(DateTime, nullable=True)
