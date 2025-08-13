"""
Data Quality Validation and Monitoring Service
Comprehensive data quality framework with validation, monitoring, and remediation
"""
import asyncio
import json
import re
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
import pandas as pd
from sqlalchemy import select, and_, or_, desc, func, text
from sqlalchemy.ext.asyncio import AsyncSession
import nltk
from textstat import flesch_reading_ease, flesch_kincaid_grade
from langdetect import detect, detect_langs
from collections import Counter
import difflib

from ..database import get_db_session, get_redis_client
from ..logging import get_logger
from ..utils.text_analyzer import TextAnalyzer
from ..utils.domain_validator import DomainValidator
from .time_series_service import TimeSeriesService

logger = get_logger(__name__)

class ValidationSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ValidationCategory(str, Enum):
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    VALIDITY = "validity"
    UNIQUENESS = "uniqueness"
    TIMELINESS = "timeliness"
    INTEGRITY = "integrity"

@dataclass
class ValidationRule:
    """Data validation rule definition"""
    rule_id: str
    name: str
    description: str
    category: ValidationCategory
    severity: ValidationSeverity
    field_name: str
    rule_type: str  # regex, range, required, custom, etc.
    parameters: Dict[str, Any]
    enabled: bool = True
    domain_specific: Optional[str] = None
    error_message_template: str = ""

@dataclass
class ValidationResult:
    """Result of a validation check"""
    rule_id: str
    field_name: str
    category: ValidationCategory
    severity: ValidationSeverity
    passed: bool
    error_message: str
    suggested_fix: Optional[str] = None
    confidence_score: float = 1.0
    metadata: Dict[str, Any] = None

@dataclass
class DataQualityReport:
    """Comprehensive data quality report"""
    content_id: str
    overall_score: float
    validation_results: List[ValidationResult]
    quality_dimensions: Dict[str, float]
    issues_by_severity: Dict[str, int]
    recommendations: List[str]
    validated_at: datetime
    validator_version: str

class DataQualityService:
    """Comprehensive data quality validation and monitoring service"""
    
    def __init__(self):
        self.redis = get_redis_client()
        self.time_series = TimeSeriesService()
        self.text_analyzer = TextAnalyzer()
        self.domain_validator = DomainValidator()
        
        # Validation rules registry
        self.validation_rules: Dict[str, ValidationRule] = {}
        self.custom_validators: Dict[str, Callable] = {}
        
        # Quality thresholds
        self.quality_thresholds = {
            'overall_minimum': 0.6,
            'critical_threshold': 0.3,
            'domain_specific': {
                'finance': {
                    'accuracy_minimum': 0.9,
                    'completeness_minimum': 0.95,
                    'timeliness_maximum_hours': 2
                },
                'sports': {
                    'timeliness_maximum_minutes': 30,
                    'accuracy_minimum': 0.85,
                    'uniqueness_minimum': 0.8
                },
                'technology': {
                    'completeness_minimum': 0.85,
                    'accuracy_minimum': 0.8,
                    'consistency_minimum': 0.9
                }
            }
        }
        
        # Initialize validation rules
        asyncio.create_task(self._initialize_validation_rules())
        
        # Download required NLTK data
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
        except:
            logger.warning("Failed to download NLTK data")
    
    async def _initialize_validation_rules(self):
        """Initialize all validation rules"""
        
        # Content completeness rules
        self.add_validation_rule(ValidationRule(
            rule_id="content_title_required",
            name="Title Required",
            description="Content must have a non-empty title",
            category=ValidationCategory.COMPLETENESS,
            severity=ValidationSeverity.CRITICAL,
            field_name="title",
            rule_type="required",
            parameters={},
            error_message_template="Content is missing a title"
        ))
        
        self.add_validation_rule(ValidationRule(
            rule_id="content_body_required",
            name="Content Body Required",
            description="Content must have a non-empty body",
            category=ValidationCategory.COMPLETENESS,
            severity=ValidationSeverity.CRITICAL,
            field_name="content",
            rule_type="required",
            parameters={},
            error_message_template="Content is missing body text"
        ))
        
        self.add_validation_rule(ValidationRule(
            rule_id="content_min_length",
            name="Minimum Content Length",
            description="Content must meet minimum word count",
            category=ValidationCategory.COMPLETENESS,
            severity=ValidationSeverity.MEDIUM,
            field_name="content",
            rule_type="min_word_count",
            parameters={"min_words": 100},
            error_message_template="Content is too short ({word_count} words, minimum {min_words})"
        ))
        
        # Content accuracy rules
        self.add_validation_rule(ValidationRule(
            rule_id="content_language_detection",
            name="Language Detection",
            description="Content language must be detected and consistent",
            category=ValidationCategory.ACCURACY,
            severity=ValidationSeverity.MEDIUM,
            field_name="content",
            rule_type="language_check",
            parameters={"expected_languages": ["en", "es", "fr", "de"]},
            error_message_template="Content language could not be reliably detected"
        ))
        
        self.add_validation_rule(ValidationRule(
            rule_id="readability_score",
            name="Content Readability",
            description="Content must have acceptable readability",
            category=ValidationCategory.ACCURACY,
            severity=ValidationSeverity.LOW,
            field_name="content",
            rule_type="readability",
            parameters={"min_flesch_score": 30, "max_grade_level": 16},
            error_message_template="Content readability is poor (Flesch: {flesch_score}, Grade: {grade_level})"
        ))
        
        # Content validity rules
        self.add_validation_rule(ValidationRule(
            rule_id="url_format_validation",
            name="URL Format Validation",
            description="URLs must be properly formatted",
            category=ValidationCategory.VALIDITY,
            severity=ValidationSeverity.MEDIUM,
            field_name="source_url",
            rule_type="url_format",
            parameters={},
            error_message_template="Source URL is not properly formatted: {url}"
        ))
        
        self.add_validation_rule(ValidationRule(
            rule_id="date_format_validation",
            name="Date Format Validation",
            description="Dates must be properly formatted and reasonable",
            category=ValidationCategory.VALIDITY,
            severity=ValidationSeverity.MEDIUM,
            field_name="published_date",
            rule_type="date_validation",
            parameters={"max_future_days": 1, "max_past_years": 10},
            error_message_template="Published date is invalid or unreasonable: {date}"
        ))
        
        # Content uniqueness rules
        self.add_validation_rule(ValidationRule(
            rule_id="content_duplication_check",
            name="Content Duplication Check",
            description="Content must be unique",
            category=ValidationCategory.UNIQUENESS,
            severity=ValidationSeverity.HIGH,
            field_name="content",
            rule_type="duplication_check",
            parameters={"similarity_threshold": 0.9, "check_window_hours": 24},
            error_message_template="Content appears to be duplicate or highly similar to existing content"
        ))
        
        # Domain-specific rules
        await self._initialize_domain_specific_rules()
        
        logger.info(f"Initialized {len(self.validation_rules)} validation rules")
    
    async def _initialize_domain_specific_rules(self):
        """Initialize domain-specific validation rules"""
        
        # Finance domain rules
        self.add_validation_rule(ValidationRule(
            rule_id="finance_entity_validation",
            name="Financial Entity Validation",
            description="Finance content must contain relevant financial entities",
            category=ValidationCategory.ACCURACY,
            severity=ValidationSeverity.MEDIUM,
            field_name="content",
            rule_type="domain_entity_check",
            parameters={"entity_types": ["stock_symbols", "financial_metrics", "companies"]},
            domain_specific="finance",
            error_message_template="Finance content lacks expected financial entities"
        ))
        
        self.add_validation_rule(ValidationRule(
            rule_id="finance_accuracy_check",
            name="Financial Data Accuracy",
            description="Financial data must be accurate and current",
            category=ValidationCategory.ACCURACY,
            severity=ValidationSeverity.HIGH,
            field_name="content",
            rule_type="finance_accuracy",
            parameters={"check_stock_prices": True, "max_data_age_hours": 4},
            domain_specific="finance",
            error_message_template="Financial data appears outdated or inaccurate"
        ))
        
        # Sports domain rules
        self.add_validation_rule(ValidationRule(
            rule_id="sports_timeliness_check",
            name="Sports Content Timeliness",
            description="Sports content must be timely",
            category=ValidationCategory.TIMELINESS,
            severity=ValidationSeverity.HIGH,
            field_name="published_date",
            rule_type="timeliness_check",
            parameters={"max_age_minutes": 60},
            domain_specific="sports",
            error_message_template="Sports content is not timely ({age_minutes} minutes old)"
        ))
        
        self.add_validation_rule(ValidationRule(
            rule_id="sports_score_validation",
            name="Sports Score Validation",
            description="Sports scores must be properly formatted",
            category=ValidationCategory.VALIDITY,
            severity=ValidationSeverity.MEDIUM,
            field_name="content",
            rule_type="sports_score_format",
            parameters={"score_patterns": [r'\d+[-–]\d+', r'\d+:\d+']},
            domain_specific="sports",
            error_message_template="Sports scores are not properly formatted"
        ))
        
        # Technology domain rules
        self.add_validation_rule(ValidationRule(
            rule_id="tech_terminology_check",
            name="Technology Terminology Check",
            description="Technology content should use consistent terminology",
            category=ValidationCategory.CONSISTENCY,
            severity=ValidationSeverity.LOW,
            field_name="content",
            rule_type="terminology_consistency",
            parameters={"tech_terms_dict": True},
            domain_specific="technology",
            error_message_template="Technology terminology is inconsistent or unclear"
        ))
    
    def add_validation_rule(self, rule: ValidationRule):
        """Add a validation rule to the registry"""
        self.validation_rules[rule.rule_id] = rule
    
    def add_custom_validator(self, name: str, validator_func: Callable):
        """Add a custom validation function"""
        self.custom_validators[name] = validator_func
    
    async def validate_content(
        self,
        content: Dict[str, Any],
        domain: str = None,
        rule_ids: List[str] = None
    ) -> DataQualityReport:
        """Perform comprehensive content validation"""
        
        start_time = datetime.now()
        content_id = content.get('id', content.get('content_id', ''))
        
        # Determine validation rules to apply
        applicable_rules = self._get_applicable_rules(domain, rule_ids)
        
        # Run validation checks
        validation_results = []
        
        for rule in applicable_rules:
            try:
                result = await self._execute_validation_rule(rule, content)
                if result:
                    validation_results.append(result)
            except Exception as e:
                logger.error(f"Validation rule {rule.rule_id} failed: {e}")
                # Create error result
                error_result = ValidationResult(
                    rule_id=rule.rule_id,
                    field_name=rule.field_name,
                    category=rule.category,
                    severity=ValidationSeverity.HIGH,
                    passed=False,
                    error_message=f"Validation rule execution failed: {str(e)}",
                    confidence_score=0.5
                )
                validation_results.append(error_result)
        
        # Calculate quality dimensions and overall score
        quality_dimensions = self._calculate_quality_dimensions(validation_results)
        overall_score = self._calculate_overall_quality_score(quality_dimensions, validation_results)
        
        # Count issues by severity
        issues_by_severity = self._count_issues_by_severity(validation_results)
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(validation_results, content, domain)
        
        # Create quality report
        report = DataQualityReport(
            content_id=content_id,
            overall_score=overall_score,
            validation_results=validation_results,
            quality_dimensions=quality_dimensions,
            issues_by_severity=issues_by_severity,
            recommendations=recommendations,
            validated_at=start_time,
            validator_version="1.0"
        )
        
        # Log metrics
        await self._log_quality_metrics(report, domain)
        
        # Cache report for quick access
        await self._cache_quality_report(report)
        
        logger.debug(f"Content validation completed in {(datetime.now() - start_time).total_seconds():.2f}s")
        
        return report
    
    def _get_applicable_rules(self, domain: str = None, rule_ids: List[str] = None) -> List[ValidationRule]:
        """Get validation rules applicable to the content"""
        
        if rule_ids:
            return [rule for rule_id, rule in self.validation_rules.items() 
                   if rule_id in rule_ids and rule.enabled]
        
        applicable_rules = []
        for rule in self.validation_rules.values():
            if not rule.enabled:
                continue
            
            # Check domain specificity
            if rule.domain_specific:
                if domain and rule.domain_specific == domain:
                    applicable_rules.append(rule)
            else:
                # General rule applies to all domains
                applicable_rules.append(rule)
        
        return applicable_rules
    
    async def _execute_validation_rule(
        self,
        rule: ValidationRule,
        content: Dict[str, Any]
    ) -> Optional[ValidationResult]:
        """Execute a single validation rule"""
        
        field_value = content.get(rule.field_name)
        
        # Handle required field validation
        if rule.rule_type == "required":
            passed = field_value is not None and str(field_value).strip() != ""
            return ValidationResult(
                rule_id=rule.rule_id,
                field_name=rule.field_name,
                category=rule.category,
                severity=rule.severity,
                passed=passed,
                error_message=rule.error_message_template if not passed else "",
                confidence_score=1.0
            )
        
        # Skip if field is missing and not required
        if field_value is None:
            return None
        
        # Execute specific rule type
        if rule.rule_type == "min_word_count":
            return await self._validate_min_word_count(rule, field_value)
        elif rule.rule_type == "language_check":
            return await self._validate_language(rule, field_value)
        elif rule.rule_type == "readability":
            return await self._validate_readability(rule, field_value)
        elif rule.rule_type == "url_format":
            return await self._validate_url_format(rule, field_value)
        elif rule.rule_type == "date_validation":
            return await self._validate_date_format(rule, field_value)
        elif rule.rule_type == "duplication_check":
            return await self._validate_uniqueness(rule, field_value, content)
        elif rule.rule_type == "domain_entity_check":
            return await self._validate_domain_entities(rule, field_value, content)
        elif rule.rule_type == "finance_accuracy":
            return await self._validate_finance_accuracy(rule, field_value, content)
        elif rule.rule_type == "timeliness_check":
            return await self._validate_timeliness(rule, field_value, content)
        elif rule.rule_type == "sports_score_format":
            return await self._validate_sports_scores(rule, field_value)
        elif rule.rule_type == "terminology_consistency":
            return await self._validate_terminology_consistency(rule, field_value)
        elif rule.rule_type in self.custom_validators:
            return await self.custom_validators[rule.rule_type](rule, field_value, content)
        else:
            logger.warning(f"Unknown validation rule type: {rule.rule_type}")
            return None
    
    async def _validate_min_word_count(self, rule: ValidationRule, text: str) -> ValidationResult:
        """Validate minimum word count"""
        word_count = len(text.split()) if text else 0
        min_words = rule.parameters.get("min_words", 100)
        passed = word_count >= min_words
        
        error_message = ""
        if not passed:
            error_message = rule.error_message_template.format(
                word_count=word_count,
                min_words=min_words
            )
        
        return ValidationResult(
            rule_id=rule.rule_id,
            field_name=rule.field_name,
            category=rule.category,
            severity=rule.severity,
            passed=passed,
            error_message=error_message,
            suggested_fix=f"Add {min_words - word_count} more words to meet minimum length requirement" if not passed else None,
            confidence_score=1.0,
            metadata={"actual_word_count": word_count, "required_word_count": min_words}
        )
    
    async def _validate_language(self, rule: ValidationRule, text: str) -> ValidationResult:
        """Validate content language"""
        try:
            if not text or len(text.strip()) < 10:
                return ValidationResult(
                    rule_id=rule.rule_id,
                    field_name=rule.field_name,
                    category=rule.category,
                    severity=rule.severity,
                    passed=False,
                    error_message="Text too short for reliable language detection",
                    confidence_score=0.3
                )
            
            detected_lang = detect(text)
            expected_languages = rule.parameters.get("expected_languages", ["en"])
            confidence_scores = detect_langs(text)
            
            # Find confidence for detected language
            lang_confidence = next((lang.prob for lang in confidence_scores 
                                  if lang.lang == detected_lang), 0.0)
            
            passed = detected_lang in expected_languages and lang_confidence > 0.7
            
            error_message = ""
            if not passed:
                error_message = rule.error_message_template + f" (detected: {detected_lang}, confidence: {lang_confidence:.2f})"
            
            return ValidationResult(
                rule_id=rule.rule_id,
                field_name=rule.field_name,
                category=rule.category,
                severity=rule.severity,
                passed=passed,
                error_message=error_message,
                confidence_score=lang_confidence,
                metadata={"detected_language": detected_lang, "language_confidence": lang_confidence}
            )
            
        except Exception as e:
            return ValidationResult(
                rule_id=rule.rule_id,
                field_name=rule.field_name,
                category=rule.category,
                severity=rule.severity,
                passed=False,
                error_message=f"Language detection failed: {str(e)}",
                confidence_score=0.0
            )
    
    async def _validate_readability(self, rule: ValidationRule, text: str) -> ValidationResult:
        """Validate content readability"""
        try:
            if not text or len(text.strip()) < 50:
                return ValidationResult(
                    rule_id=rule.rule_id,
                    field_name=rule.field_name,
                    category=rule.category,
                    severity=rule.severity,
                    passed=False,
                    error_message="Text too short for readability analysis",
                    confidence_score=0.5
                )
            
            flesch_score = flesch_reading_ease(text)
            grade_level = flesch_kincaid_grade(text)
            
            min_flesch = rule.parameters.get("min_flesch_score", 30)
            max_grade = rule.parameters.get("max_grade_level", 16)
            
            passed = flesch_score >= min_flesch and grade_level <= max_grade
            
            error_message = ""
            if not passed:
                error_message = rule.error_message_template.format(
                    flesch_score=flesch_score,
                    grade_level=grade_level
                )
            
            # Generate readability improvement suggestions
            suggested_fix = None
            if not passed:
                fixes = []
                if flesch_score < min_flesch:
                    fixes.append("Use shorter sentences and simpler words")
                if grade_level > max_grade:
                    fixes.append("Reduce sentence complexity and technical jargon")
                suggested_fix = "; ".join(fixes)
            
            return ValidationResult(
                rule_id=rule.rule_id,
                field_name=rule.field_name,
                category=rule.category,
                severity=rule.severity,
                passed=passed,
                error_message=error_message,
                suggested_fix=suggested_fix,
                confidence_score=0.8,
                metadata={
                    "flesch_reading_ease": flesch_score,
                    "flesch_kincaid_grade": grade_level
                }
            )
            
        except Exception as e:
            return ValidationResult(
                rule_id=rule.rule_id,
                field_name=rule.field_name,
                category=rule.category,
                severity=rule.severity,
                passed=False,
                error_message=f"Readability analysis failed: {str(e)}",
                confidence_score=0.0
            )
    
    async def _validate_url_format(self, rule: ValidationRule, url: str) -> ValidationResult:
        """Validate URL format"""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        passed = bool(url_pattern.match(url)) if url else False
        
        error_message = ""
        if not passed:
            error_message = rule.error_message_template.format(url=url)
        
        return ValidationResult(
            rule_id=rule.rule_id,
            field_name=rule.field_name,
            category=rule.category,
            severity=rule.severity,
            passed=passed,
            error_message=error_message,
            suggested_fix="Ensure URL starts with http:// or https:// and has valid format" if not passed else None,
            confidence_score=1.0
        )
    
    async def _validate_date_format(self, rule: ValidationRule, date_value: Union[str, datetime]) -> ValidationResult:
        """Validate date format and reasonableness"""
        try:
            if isinstance(date_value, str):
                from dateutil import parser
                parsed_date = parser.parse(date_value)
            elif isinstance(date_value, datetime):
                parsed_date = date_value
            else:
                return ValidationResult(
                    rule_id=rule.rule_id,
                    field_name=rule.field_name,
                    category=rule.category,
                    severity=rule.severity,
                    passed=False,
                    error_message="Date is not in recognized format",
                    confidence_score=1.0
                )
            
            now = datetime.now(timezone.utc)
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
            
            max_future_days = rule.parameters.get("max_future_days", 1)
            max_past_years = rule.parameters.get("max_past_years", 10)
            
            future_limit = now + timedelta(days=max_future_days)
            past_limit = now - timedelta(days=max_past_years * 365)
            
            passed = past_limit <= parsed_date <= future_limit
            
            error_message = ""
            if not passed:
                error_message = rule.error_message_template.format(date=parsed_date.isoformat())
            
            return ValidationResult(
                rule_id=rule.rule_id,
                field_name=rule.field_name,
                category=rule.category,
                severity=rule.severity,
                passed=passed,
                error_message=error_message,
                confidence_score=1.0,
                metadata={
                    "parsed_date": parsed_date.isoformat(),
                    "days_from_now": (parsed_date - now).days
                }
            )
            
        except Exception as e:
            return ValidationResult(
                rule_id=rule.rule_id,
                field_name=rule.field_name,
                category=rule.category,
                severity=rule.severity,
                passed=False,
                error_message=f"Date parsing failed: {str(e)}",
                confidence_score=0.0
            )
    
    async def _validate_uniqueness(
        self, 
        rule: ValidationRule, 
        content_text: str, 
        content: Dict[str, Any]
    ) -> ValidationResult:
        """Validate content uniqueness"""
        try:
            content_id = content.get('id', content.get('content_id', ''))
            similarity_threshold = rule.parameters.get("similarity_threshold", 0.9)
            
            # Generate content hash for exact duplicate detection
            content_hash = hashlib.sha256(content_text.encode()).hexdigest()
            
            # Check for exact duplicates in cache
            duplicate_key = f"content_hash:{content_hash}"
            existing_id = await self.redis.get(duplicate_key)
            
            if existing_id and existing_id != content_id:
                return ValidationResult(
                    rule_id=rule.rule_id,
                    field_name=rule.field_name,
                    category=rule.category,
                    severity=rule.severity,
                    passed=False,
                    error_message="Exact duplicate content found",
                    confidence_score=1.0,
                    metadata={"duplicate_content_id": existing_id, "similarity": 1.0}
                )
            
            # Check for near-duplicates using text similarity
            # This would require integration with vector database for efficiency
            # For now, implement basic similarity check
            
            # Store content hash for future checks
            await self.redis.setex(duplicate_key, 86400, content_id)  # 24 hour window
            
            return ValidationResult(
                rule_id=rule.rule_id,
                field_name=rule.field_name,
                category=rule.category,
                severity=rule.severity,
                passed=True,
                error_message="",
                confidence_score=0.8,  # Lower confidence without full similarity analysis
                metadata={"content_hash": content_hash}
            )
            
        except Exception as e:
            return ValidationResult(
                rule_id=rule.rule_id,
                field_name=rule.field_name,
                category=rule.category,
                severity=rule.severity,
                passed=False,
                error_message=f"Uniqueness check failed: {str(e)}",
                confidence_score=0.0
            )
    
    async def _validate_domain_entities(
        self, 
        rule: ValidationRule, 
        content_text: str, 
        content: Dict[str, Any]
    ) -> ValidationResult:
        """Validate domain-specific entities in content"""
        try:
            domain = content.get('domain', 'general')
            entity_types = rule.parameters.get("entity_types", [])
            
            # Use domain validator to check for relevant entities
            entity_analysis = await self.domain_validator.analyze_domain_entities(
                content_text, domain
            )
            
            found_entity_types = set(entity_analysis.keys())
            required_entity_types = set(entity_types)
            
            # Check if at least one required entity type is present
            passed = bool(found_entity_types & required_entity_types)
            
            error_message = ""
            if not passed:
                error_message = f"{rule.error_message_template} (missing: {required_entity_types - found_entity_types})"
            
            return ValidationResult(
                rule_id=rule.rule_id,
                field_name=rule.field_name,
                category=rule.category,
                severity=rule.severity,
                passed=passed,
                error_message=error_message,
                confidence_score=0.7,
                metadata={
                    "found_entities": entity_analysis,
                    "required_types": list(required_entity_types),
                    "found_types": list(found_entity_types)
                }
            )
            
        except Exception as e:
            return ValidationResult(
                rule_id=rule.rule_id,
                field_name=rule.field_name,
                category=rule.category,
                severity=rule.severity,
                passed=False,
                error_message=f"Entity validation failed: {str(e)}",
                confidence_score=0.0
            )
    
    async def _validate_finance_accuracy(
        self, 
        rule: ValidationRule, 
        content_text: str, 
        content: Dict[str, Any]
    ) -> ValidationResult:
        """Validate financial data accuracy"""
        # This would require integration with financial data APIs
        # For now, implement basic checks
        
        try:
            # Extract financial entities
            stock_symbols = re.findall(r'\b[A-Z]{2,5}\b', content_text)
            
            # Check if content mentions recent/current financial data
            currency_amounts = re.findall(r'[\$€£¥]\s*[\d,]+\.?\d*[MBK]?', content_text)
            
            # Simple heuristic: content with financial entities is likely accurate
            has_financial_data = len(stock_symbols) > 0 or len(currency_amounts) > 0
            
            return ValidationResult(
                rule_id=rule.rule_id,
                field_name=rule.field_name,
                category=rule.category,
                severity=rule.severity,
                passed=has_financial_data,
                error_message=rule.error_message_template if not has_financial_data else "",
                confidence_score=0.5,  # Low confidence without real data validation
                metadata={
                    "stock_symbols": stock_symbols,
                    "currency_amounts": currency_amounts
                }
            )
            
        except Exception as e:
            return ValidationResult(
                rule_id=rule.rule_id,
                field_name=rule.field_name,
                category=rule.category,
                severity=rule.severity,
                passed=False,
                error_message=f"Financial accuracy check failed: {str(e)}",
                confidence_score=0.0
            )
    
    async def _validate_timeliness(
        self, 
        rule: ValidationRule, 
        date_value: Union[str, datetime], 
        content: Dict[str, Any]
    ) -> ValidationResult:
        """Validate content timeliness"""
        try:
            if isinstance(date_value, str):
                from dateutil import parser
                content_date = parser.parse(date_value)
            elif isinstance(date_value, datetime):
                content_date = date_value
            else:
                return ValidationResult(
                    rule_id=rule.rule_id,
                    field_name=rule.field_name,
                    category=rule.category,
                    severity=rule.severity,
                    passed=False,
                    error_message="Cannot validate timeliness: invalid date",
                    confidence_score=1.0
                )
            
            now = datetime.now(timezone.utc)
            if content_date.tzinfo is None:
                content_date = content_date.replace(tzinfo=timezone.utc)
            
            age_minutes = (now - content_date).total_seconds() / 60
            max_age_minutes = rule.parameters.get("max_age_minutes", 60)
            
            passed = age_minutes <= max_age_minutes
            
            error_message = ""
            if not passed:
                error_message = rule.error_message_template.format(age_minutes=int(age_minutes))
            
            return ValidationResult(
                rule_id=rule.rule_id,
                field_name=rule.field_name,
                category=rule.category,
                severity=rule.severity,
                passed=passed,
                error_message=error_message,
                confidence_score=1.0,
                metadata={"age_minutes": age_minutes, "max_age_minutes": max_age_minutes}
            )
            
        except Exception as e:
            return ValidationResult(
                rule_id=rule.rule_id,
                field_name=rule.field_name,
                category=rule.category,
                severity=rule.severity,
                passed=False,
                error_message=f"Timeliness check failed: {str(e)}",
                confidence_score=0.0
            )
    
    async def _validate_sports_scores(self, rule: ValidationRule, content_text: str) -> ValidationResult:
        """Validate sports score formatting"""
        try:
            score_patterns = rule.parameters.get("score_patterns", [r'\d+[-–]\d+'])
            
            found_scores = []
            for pattern in score_patterns:
                matches = re.findall(pattern, content_text)
                found_scores.extend(matches)
            
            # Sports content should have at least one score if it's about a completed game
            # This is a heuristic - more sophisticated analysis would be needed
            has_game_indicators = any(word in content_text.lower() 
                                    for word in ['final', 'score', 'won', 'beat', 'defeated'])
            
            if has_game_indicators:
                passed = len(found_scores) > 0
                error_message = rule.error_message_template if not passed else ""
            else:
                # If no game indicators, scores are optional
                passed = True
                error_message = ""
            
            return ValidationResult(
                rule_id=rule.rule_id,
                field_name=rule.field_name,
                category=rule.category,
                severity=rule.severity,
                passed=passed,
                error_message=error_message,
                confidence_score=0.7,
                metadata={
                    "found_scores": found_scores,
                    "has_game_indicators": has_game_indicators
                }
            )
            
        except Exception as e:
            return ValidationResult(
                rule_id=rule.rule_id,
                field_name=rule.field_name,
                category=rule.category,
                severity=rule.severity,
                passed=False,
                error_message=f"Sports score validation failed: {str(e)}",
                confidence_score=0.0
            )
    
    async def _validate_terminology_consistency(self, rule: ValidationRule, content_text: str) -> ValidationResult:
        """Validate terminology consistency"""
        try:
            # Simple terminology consistency check
            # In practice, this would use a comprehensive tech terms dictionary
            
            inconsistent_terms = []
            
            # Check for common inconsistencies
            if 'AI' in content_text and 'artificial intelligence' in content_text.lower():
                # Both AI and full form present - this is actually good
                pass
            
            # Check for mixed casing in technical terms
            tech_terms = ['API', 'URL', 'HTTP', 'JSON', 'XML', 'CSS', 'HTML', 'SQL']
            for term in tech_terms:
                if term.lower() in content_text.lower() and term not in content_text:
                    inconsistent_terms.append(f"{term} should be uppercase")
            
            passed = len(inconsistent_terms) == 0
            
            error_message = ""
            if not passed:
                error_message = f"{rule.error_message_template}: {'; '.join(inconsistent_terms)}"
            
            return ValidationResult(
                rule_id=rule.rule_id,
                field_name=rule.field_name,
                category=rule.category,
                severity=rule.severity,
                passed=passed,
                error_message=error_message,
                suggested_fix="Ensure technical terms use consistent capitalization and terminology" if not passed else None,
                confidence_score=0.6,
                metadata={"inconsistent_terms": inconsistent_terms}
            )
            
        except Exception as e:
            return ValidationResult(
                rule_id=rule.rule_id,
                field_name=rule.field_name,
                category=rule.category,
                severity=rule.severity,
                passed=False,
                error_message=f"Terminology validation failed: {str(e)}",
                confidence_score=0.0
            )
    
    def _calculate_quality_dimensions(self, validation_results: List[ValidationResult]) -> Dict[str, float]:
        """Calculate quality scores for each dimension"""
        
        dimensions = {}
        
        for category in ValidationCategory:
            category_results = [r for r in validation_results if r.category == category]
            
            if category_results:
                # Weight by severity and confidence
                total_weight = 0
                total_score = 0
                
                for result in category_results:
                    severity_weight = {
                        ValidationSeverity.LOW: 1,
                        ValidationSeverity.MEDIUM: 2,
                        ValidationSeverity.HIGH: 3,
                        ValidationSeverity.CRITICAL: 4
                    }[result.severity]
                    
                    weight = severity_weight * result.confidence_score
                    score = 1.0 if result.passed else 0.0
                    
                    total_weight += weight
                    total_score += score * weight
                
                dimensions[category.value] = total_score / total_weight if total_weight > 0 else 0.0
            else:
                dimensions[category.value] = 1.0  # Perfect score if no rules for this dimension
        
        return dimensions
    
    def _calculate_overall_quality_score(
        self, 
        quality_dimensions: Dict[str, float], 
        validation_results: List[ValidationResult]
    ) -> float:
        """Calculate overall quality score"""
        
        # Weighted average of dimensions
        dimension_weights = {
            ValidationCategory.COMPLETENESS.value: 0.25,
            ValidationCategory.ACCURACY.value: 0.25,
            ValidationCategory.CONSISTENCY.value: 0.15,
            ValidationCategory.VALIDITY.value: 0.15,
            ValidationCategory.UNIQUENESS.value: 0.10,
            ValidationCategory.TIMELINESS.value: 0.05,
            ValidationCategory.INTEGRITY.value: 0.05
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for dimension, score in quality_dimensions.items():
            weight = dimension_weights.get(dimension, 0.0)
            total_score += score * weight
            total_weight += weight
        
        base_score = total_score / total_weight if total_weight > 0 else 0.0
        
        # Apply penalties for critical issues
        critical_issues = [r for r in validation_results 
                         if not r.passed and r.severity == ValidationSeverity.CRITICAL]
        
        if critical_issues:
            # Significant penalty for critical issues
            penalty = min(0.5, len(critical_issues) * 0.2)
            base_score *= (1.0 - penalty)
        
        return min(1.0, max(0.0, base_score))
    
    def _count_issues_by_severity(self, validation_results: List[ValidationResult]) -> Dict[str, int]:
        """Count validation issues by severity"""
        
        counts = {severity.value: 0 for severity in ValidationSeverity}
        
        for result in validation_results:
            if not result.passed:
                counts[result.severity.value] += 1
        
        return counts
    
    async def _generate_recommendations(
        self,
        validation_results: List[ValidationResult],
        content: Dict[str, Any],
        domain: str = None
    ) -> List[str]:
        """Generate improvement recommendations"""
        
        recommendations = []
        
        # Group issues by category
        issues_by_category = {}
        for result in validation_results:
            if not result.passed:
                if result.category.value not in issues_by_category:
                    issues_by_category[result.category.value] = []
                issues_by_category[result.category.value].append(result)
        
        # Generate category-specific recommendations
        if ValidationCategory.COMPLETENESS.value in issues_by_category:
            recommendations.append("Ensure all required fields are filled with meaningful content")
        
        if ValidationCategory.ACCURACY.value in issues_by_category:
            recommendations.append("Verify facts, figures, and domain-specific information for accuracy")
        
        if ValidationCategory.CONSISTENCY.value in issues_by_category:
            recommendations.append("Review content for consistent terminology, formatting, and style")
        
        if ValidationCategory.VALIDITY.value in issues_by_category:
            recommendations.append("Check that all data formats (URLs, dates, etc.) are properly formatted")
        
        if ValidationCategory.UNIQUENESS.value in issues_by_category:
            recommendations.append("Ensure content is original and not duplicated from existing sources")
        
        if ValidationCategory.TIMELINESS.value in issues_by_category:
            recommendations.append("Update content with more recent information if available")
        
        # Add specific suggestions from validation results
        for result in validation_results:
            if not result.passed and result.suggested_fix:
                recommendations.append(result.suggested_fix)
        
        # Domain-specific recommendations
        if domain == 'finance':
            recommendations.append("Include recent market data and verify all financial figures")
        elif domain == 'sports':
            recommendations.append("Ensure scores and statistics are current and accurate")
        elif domain == 'technology':
            recommendations.append("Use consistent technical terminology and verify product details")
        
        return list(set(recommendations))  # Remove duplicates
    
    async def _log_quality_metrics(self, report: DataQualityReport, domain: str = None):
        """Log quality metrics to time series database"""
        
        try:
            # Log overall quality score
            await self.time_series.write_metric(
                metric_name="data_quality",
                value=report.overall_score,
                tags={
                    "domain": domain or "general",
                    "validation_type": "comprehensive",
                    "content_id": report.content_id
                }
            )
            
            # Log dimension scores
            for dimension, score in report.quality_dimensions.items():
                await self.time_series.write_metric(
                    metric_name="data_quality",
                    value=score,
                    tags={
                        "domain": domain or "general",
                        "validation_type": dimension,
                        "content_id": report.content_id
                    }
                )
            
            # Log issue counts by severity
            for severity, count in report.issues_by_severity.items():
                if count > 0:
                    await self.time_series.write_metric(
                        metric_name="data_quality_issues",
                        value=count,
                        tags={
                            "domain": domain or "general",
                            "severity": severity,
                            "content_id": report.content_id
                        }
                    )
                    
        except Exception as e:
            logger.error(f"Failed to log quality metrics: {e}")
    
    async def _cache_quality_report(self, report: DataQualityReport):
        """Cache quality report for quick access"""
        
        try:
            cache_key = f"quality_report:{report.content_id}"
            
            # Convert report to dict for JSON serialization
            report_dict = asdict(report)
            report_dict['validated_at'] = report.validated_at.isoformat()
            
            await self.redis.setex(
                cache_key,
                3600,  # 1 hour cache
                json.dumps(report_dict, default=str)
            )
            
        except Exception as e:
            logger.error(f"Failed to cache quality report: {e}")
    
    async def get_cached_quality_report(self, content_id: str) -> Optional[DataQualityReport]:
        """Get cached quality report"""
        
        try:
            cache_key = f"quality_report:{content_id}"
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                report_dict = json.loads(cached_data)
                
                # Convert back to DataQualityReport
                report_dict['validated_at'] = datetime.fromisoformat(report_dict['validated_at'])
                
                # Convert validation results
                validation_results = []
                for result_dict in report_dict['validation_results']:
                    validation_results.append(ValidationResult(**result_dict))
                
                report_dict['validation_results'] = validation_results
                
                return DataQualityReport(**report_dict)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached quality report: {e}")
            return None
    
    async def get_quality_trends(
        self,
        domain: str = None,
        time_range: str = "24h"
    ) -> Dict[str, Any]:
        """Get quality trends over time"""
        
        try:
            end_time = datetime.now(timezone.utc)
            
            # Parse time range
            if time_range.endswith('h'):
                hours = int(time_range[:-1])
                start_time = end_time - timedelta(hours=hours)
            elif time_range.endswith('d'):
                days = int(time_range[:-1])
                start_time = end_time - timedelta(days=days)
            else:
                start_time = end_time - timedelta(hours=24)
            
            # Get quality metrics from time series
            filters = {'domain': domain} if domain else None
            
            quality_data = await self.time_series.query_metrics(
                measurement="data_quality",
                start_time=start_time,
                end_time=end_time,
                filters=filters,
                aggregation="mean",
                window="1h"
            )
            
            # Calculate trend metrics
            if quality_data:
                values = [item['value'] for item in quality_data]
                trend = {
                    'current_score': values[-1] if values else 0,
                    'average_score': np.mean(values),
                    'trend_direction': 'improving' if len(values) > 1 and values[-1] > values[0] else 'declining',
                    'score_range': [min(values), max(values)],
                    'data_points': len(values)
                }
            else:
                trend = {
                    'current_score': 0,
                    'average_score': 0,
                    'trend_direction': 'unknown',
                    'score_range': [0, 0],
                    'data_points': 0
                }
            
            return {
                'domain': domain or 'all',
                'time_range': time_range,
                'trend': trend,
                'raw_data': quality_data
            }
            
        except Exception as e:
            logger.error(f"Failed to get quality trends: {e}")
            return {'error': str(e)}