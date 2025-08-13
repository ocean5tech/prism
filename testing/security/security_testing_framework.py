"""
Security and Compliance Testing Framework
Comprehensive security validation for content generation platform
"""

import asyncio
import json
import hashlib
import secrets
import jwt
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import httpx
import sqlalchemy
from sqlalchemy import text
import re
from urllib.parse import urlparse, parse_qs
import base64
import requests

from shared.logging import get_logger
from shared.config import TestSettings

logger = get_logger(__name__)

@dataclass
class SecurityTestResult:
    """Security test result data structure"""
    test_name: str
    category: str  # 'authentication', 'authorization', 'injection', 'xss', 'data_protection'
    severity: str  # 'critical', 'high', 'medium', 'low', 'info'
    status: str  # 'passed', 'failed', 'warning'
    description: str
    details: Dict[str, Any]
    remediation: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

@dataclass
class ComplianceCheckResult:
    """Compliance check result"""
    regulation: str  # 'GDPR', 'CCPA', 'SOC2', 'FINRA'
    requirement: str
    status: str  # 'compliant', 'non_compliant', 'partial'
    evidence: Dict[str, Any]
    gap_analysis: Optional[str] = None

class AuthenticationTester:
    """Test authentication and session management security"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_jwt_token_validation(self) -> List[SecurityTestResult]:
        """Test JWT token security"""
        results = []
        
        # Test 1: Invalid JWT token
        try:
            invalid_token = "invalid.jwt.token"
            headers = {"Authorization": f"Bearer {invalid_token}"}
            
            response = await self.client.get(
                f"{self.base_url}/api/v1/content/generate",
                headers=headers
            )
            
            if response.status_code == 401:
                results.append(SecurityTestResult(
                    test_name="invalid_jwt_rejection",
                    category="authentication",
                    severity="high",
                    status="passed",
                    description="Invalid JWT tokens are properly rejected",
                    details={"response_code": response.status_code}
                ))
            else:
                results.append(SecurityTestResult(
                    test_name="invalid_jwt_rejection",
                    category="authentication", 
                    severity="critical",
                    status="failed",
                    description="Invalid JWT tokens are accepted",
                    details={"response_code": response.status_code},
                    remediation="Implement proper JWT validation"
                ))
        except Exception as e:
            results.append(SecurityTestResult(
                test_name="invalid_jwt_rejection",
                category="authentication",
                severity="high",
                status="failed",
                description="JWT validation test failed",
                details={"error": str(e)}
            ))
        
        # Test 2: Expired JWT token
        try:
            expired_payload = {
                "sub": "test_user",
                "exp": int(time.time()) - 3600,  # Expired 1 hour ago
                "iat": int(time.time()) - 7200
            }
            expired_token = jwt.encode(expired_payload, "test_secret", algorithm="HS256")
            headers = {"Authorization": f"Bearer {expired_token}"}
            
            response = await self.client.get(
                f"{self.base_url}/api/v1/content/generate",
                headers=headers
            )
            
            if response.status_code == 401:
                results.append(SecurityTestResult(
                    test_name="expired_jwt_rejection",
                    category="authentication",
                    severity="high", 
                    status="passed",
                    description="Expired JWT tokens are properly rejected",
                    details={"response_code": response.status_code}
                ))
            else:
                results.append(SecurityTestResult(
                    test_name="expired_jwt_rejection",
                    category="authentication",
                    severity="critical",
                    status="failed", 
                    description="Expired JWT tokens are accepted",
                    details={"response_code": response.status_code},
                    remediation="Implement JWT expiration validation"
                ))
        except Exception as e:
            results.append(SecurityTestResult(
                test_name="expired_jwt_rejection",
                category="authentication",
                severity="high",
                status="failed",
                description="Expired JWT test failed",
                details={"error": str(e)}
            ))
        
        # Test 3: JWT secret brute force protection
        try:
            weak_secrets = ["secret", "password", "123456", "", "jwt_secret"]
            valid_payload = {
                "sub": "test_user",
                "exp": int(time.time()) + 3600,
                "iat": int(time.time())
            }
            
            for secret in weak_secrets:
                try:
                    token = jwt.encode(valid_payload, secret, algorithm="HS256")
                    headers = {"Authorization": f"Bearer {token}"}
                    
                    response = await self.client.get(
                        f"{self.base_url}/api/v1/content/generate",
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        results.append(SecurityTestResult(
                            test_name="jwt_weak_secret",
                            category="authentication",
                            severity="critical",
                            status="failed",
                            description=f"JWT accepts weak secret: {secret}",
                            details={"weak_secret": secret},
                            remediation="Use strong, randomly generated JWT secrets"
                        ))
                        break
                except:
                    continue
            else:
                results.append(SecurityTestResult(
                    test_name="jwt_weak_secret",
                    category="authentication",
                    severity="high",
                    status="passed",
                    description="JWT uses strong secret protection",
                    details={"tested_secrets": len(weak_secrets)}
                ))
        except Exception as e:
            results.append(SecurityTestResult(
                test_name="jwt_weak_secret",
                category="authentication",
                severity="medium",
                status="warning",
                description="Could not test JWT secret strength",
                details={"error": str(e)}
            ))
        
        return results
    
    async def test_session_security(self) -> List[SecurityTestResult]:
        """Test session security mechanisms"""
        results = []
        
        # Test session timeout
        try:
            # Test with a long-duration request simulation
            response = await self.client.get(
                f"{self.base_url}/health",
                headers={"Authorization": "Bearer test_token"}
            )
            
            # Check for security headers
            security_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY", 
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": "max-age=31536000",
                "Content-Security-Policy": True
            }
            
            for header, expected in security_headers.items():
                if header in response.headers:
                    if expected is True or response.headers[header] == expected:
                        results.append(SecurityTestResult(
                            test_name=f"security_header_{header.lower().replace('-', '_')}",
                            category="authentication",
                            severity="medium",
                            status="passed",
                            description=f"Security header {header} is present",
                            details={"header_value": response.headers[header]}
                        ))
                    else:
                        results.append(SecurityTestResult(
                            test_name=f"security_header_{header.lower().replace('-', '_')}",
                            category="authentication",
                            severity="medium",
                            status="warning",
                            description=f"Security header {header} has unexpected value",
                            details={"expected": expected, "actual": response.headers[header]}
                        ))
                else:
                    results.append(SecurityTestResult(
                        test_name=f"security_header_{header.lower().replace('-', '_')}",
                        category="authentication",
                        severity="medium",
                        status="failed",
                        description=f"Missing security header: {header}",
                        details={"missing_header": header},
                        remediation=f"Add {header} security header"
                    ))
        except Exception as e:
            results.append(SecurityTestResult(
                test_name="session_security_headers",
                category="authentication",
                severity="medium",
                status="failed",
                description="Session security test failed",
                details={"error": str(e)}
            ))
        
        return results

class AuthorizationTester:
    """Test authorization and access control"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_rbac_enforcement(self) -> List[SecurityTestResult]:
        """Test Role-Based Access Control"""
        results = []
        
        # Test endpoints with different permission levels
        test_scenarios = [
            {
                "endpoint": "/api/v1/content/generate",
                "method": "POST",
                "required_role": "content_creator",
                "payload": {"domain": "test", "source_content": "test"}
            },
            {
                "endpoint": "/api/v1/admin/users",
                "method": "GET", 
                "required_role": "admin",
                "payload": None
            },
            {
                "endpoint": "/api/v1/analytics/reports",
                "method": "GET",
                "required_role": "analyst",
                "payload": None
            }
        ]
        
        # Test with different user roles
        test_roles = ["guest", "content_creator", "analyst", "admin"]
        
        for scenario in test_scenarios:
            for role in test_roles:
                try:
                    # Create token for specific role
                    token_payload = {
                        "sub": f"test_user_{role}",
                        "role": role,
                        "exp": int(time.time()) + 3600,
                        "iat": int(time.time())
                    }
                    
                    # Note: In real implementation, use proper secret
                    token = jwt.encode(token_payload, "test_secret", algorithm="HS256")
                    headers = {"Authorization": f"Bearer {token}"}
                    
                    if scenario["method"] == "GET":
                        response = await self.client.get(
                            f"{self.base_url}{scenario['endpoint']}",
                            headers=headers
                        )
                    elif scenario["method"] == "POST":
                        response = await self.client.post(
                            f"{self.base_url}{scenario['endpoint']}",
                            headers=headers,
                            json=scenario["payload"]
                        )
                    
                    # Evaluate authorization result
                    should_allow = role == scenario["required_role"] or role == "admin"
                    is_allowed = response.status_code not in [401, 403]
                    
                    if should_allow == is_allowed:
                        status = "passed"
                        severity = "low"
                    else:
                        status = "failed"
                        severity = "high" if not should_allow and is_allowed else "medium"
                    
                    results.append(SecurityTestResult(
                        test_name=f"rbac_{role}_{scenario['endpoint'].replace('/', '_')}",
                        category="authorization",
                        severity=severity,
                        status=status,
                        description=f"RBAC test for {role} accessing {scenario['endpoint']}",
                        details={
                            "role": role,
                            "endpoint": scenario["endpoint"],
                            "required_role": scenario["required_role"],
                            "should_allow": should_allow,
                            "is_allowed": is_allowed,
                            "response_code": response.status_code
                        }
                    ))
                    
                except Exception as e:
                    results.append(SecurityTestResult(
                        test_name=f"rbac_{role}_{scenario['endpoint'].replace('/', '_')}",
                        category="authorization",
                        severity="medium",
                        status="failed",
                        description=f"RBAC test failed for {role}",
                        details={"error": str(e), "role": role, "endpoint": scenario["endpoint"]}
                    ))
        
        return results
    
    async def test_horizontal_privilege_escalation(self) -> List[SecurityTestResult]:
        """Test for horizontal privilege escalation vulnerabilities"""
        results = []
        
        try:
            # Create tokens for different users
            user1_token = jwt.encode({
                "sub": "user_001",
                "role": "content_creator",
                "exp": int(time.time()) + 3600
            }, "test_secret", algorithm="HS256")
            
            user2_token = jwt.encode({
                "sub": "user_002", 
                "role": "content_creator",
                "exp": int(time.time()) + 3600
            }, "test_secret", algorithm="HS256")
            
            # Test accessing another user's resources
            test_endpoints = [
                "/api/v1/user/user_001/content",
                "/api/v1/user/user_001/profile",
                "/api/v1/user/user_001/settings"
            ]
            
            for endpoint in test_endpoints:
                # User2 trying to access User1's resources
                response = await self.client.get(
                    f"{self.base_url}{endpoint}",
                    headers={"Authorization": f"Bearer {user2_token}"}
                )
                
                if response.status_code in [403, 404]:
                    results.append(SecurityTestResult(
                        test_name=f"horizontal_privilege_escalation_{endpoint.replace('/', '_')}",
                        category="authorization",
                        severity="high",
                        status="passed",
                        description="Horizontal privilege escalation properly prevented",
                        details={"endpoint": endpoint, "response_code": response.status_code}
                    ))
                else:
                    results.append(SecurityTestResult(
                        test_name=f"horizontal_privilege_escalation_{endpoint.replace('/', '_')}",
                        category="authorization",
                        severity="critical",
                        status="failed",
                        description="Horizontal privilege escalation vulnerability detected",
                        details={"endpoint": endpoint, "response_code": response.status_code},
                        remediation="Implement proper user context validation"
                    ))
        
        except Exception as e:
            results.append(SecurityTestResult(
                test_name="horizontal_privilege_escalation",
                category="authorization",
                severity="high",
                status="failed",
                description="Horizontal privilege escalation test failed",
                details={"error": str(e)}
            ))
        
        return results

class InjectionTester:
    """Test for injection vulnerabilities"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_sql_injection(self) -> List[SecurityTestResult]:
        """Test for SQL injection vulnerabilities"""
        results = []
        
        # SQL injection payloads
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "1' OR 1=1#",
            "'; WAITFOR DELAY '00:00:10'; --"
        ]
        
        # Test endpoints that might be vulnerable
        test_endpoints = [
            {
                "path": "/api/v1/content/search",
                "method": "GET",
                "param": "query"
            },
            {
                "path": "/api/v1/user/profile",
                "method": "GET",
                "param": "user_id"
            }
        ]
        
        for endpoint in test_endpoints:
            for payload in sql_payloads:
                try:
                    start_time = time.time()
                    
                    if endpoint["method"] == "GET":
                        params = {endpoint["param"]: payload}
                        response = await self.client.get(
                            f"{self.base_url}{endpoint['path']}",
                            params=params,
                            headers={"Authorization": "Bearer test_token"}
                        )
                    
                    response_time = time.time() - start_time
                    
                    # Check for SQL injection indicators
                    is_vulnerable = False
                    vulnerability_indicators = []
                    
                    # Time-based detection
                    if response_time > 5.0 and "WAITFOR" in payload:
                        is_vulnerable = True
                        vulnerability_indicators.append("time_based_delay")
                    
                    # Error-based detection
                    if response.status_code == 500:
                        response_text = response.text.lower()
                        sql_error_patterns = [
                            "sql syntax", "mysql", "postgresql", "sqlite",
                            "ora-", "microsoft", "driver", "database"
                        ]
                        
                        for pattern in sql_error_patterns:
                            if pattern in response_text:
                                is_vulnerable = True
                                vulnerability_indicators.append("error_based")
                                break
                    
                    # Content-based detection
                    if response.status_code == 200 and len(response.content) > 10000:
                        # Unusually large response might indicate data extraction
                        vulnerability_indicators.append("potential_data_extraction")
                        is_vulnerable = True
                    
                    test_name = f"sql_injection_{endpoint['path'].replace('/', '_')}_{hash(payload) % 1000}"
                    
                    if is_vulnerable:
                        results.append(SecurityTestResult(
                            test_name=test_name,
                            category="injection",
                            severity="critical",
                            status="failed",
                            description=f"SQL injection vulnerability detected",
                            details={
                                "endpoint": endpoint["path"],
                                "payload": payload,
                                "indicators": vulnerability_indicators,
                                "response_code": response.status_code,
                                "response_time": response_time
                            },
                            remediation="Use parameterized queries and input validation"
                        ))
                    else:
                        results.append(SecurityTestResult(
                            test_name=test_name,
                            category="injection",
                            severity="low",
                            status="passed",
                            description="No SQL injection vulnerability detected",
                            details={
                                "endpoint": endpoint["path"],
                                "payload": payload,
                                "response_code": response.status_code
                            }
                        ))
                
                except Exception as e:
                    results.append(SecurityTestResult(
                        test_name=f"sql_injection_error_{hash(payload) % 1000}",
                        category="injection",
                        severity="medium",
                        status="warning",
                        description="SQL injection test encountered error",
                        details={"error": str(e), "payload": payload}
                    ))
        
        return results
    
    async def test_nosql_injection(self) -> List[SecurityTestResult]:
        """Test for NoSQL injection vulnerabilities"""
        results = []
        
        # NoSQL injection payloads
        nosql_payloads = [
            {"$ne": None},
            {"$regex": ".*"},
            {"$where": "1==1"},
            {"$gt": ""},
            {"username": {"$ne": None}, "password": {"$ne": None}}
        ]
        
        test_endpoints = [
            "/api/v1/content/query",
            "/api/v1/user/search"
        ]
        
        for endpoint in test_endpoints:
            for payload in nosql_payloads:
                try:
                    response = await self.client.post(
                        f"{self.base_url}{endpoint}",
                        json={"query": payload},
                        headers={"Authorization": "Bearer test_token"}
                    )
                    
                    # Check for NoSQL injection indicators
                    is_vulnerable = False
                    if response.status_code == 200:
                        response_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                        
                        # Check for unexpected data exposure
                        if isinstance(response_data, dict) and len(response_data) > 100:
                            is_vulnerable = True
                        elif isinstance(response_data, list) and len(response_data) > 50:
                            is_vulnerable = True
                    
                    test_name = f"nosql_injection_{endpoint.replace('/', '_')}_{hash(str(payload)) % 1000}"
                    
                    if is_vulnerable:
                        results.append(SecurityTestResult(
                            test_name=test_name,
                            category="injection",
                            severity="high",
                            status="failed",
                            description="Potential NoSQL injection vulnerability",
                            details={
                                "endpoint": endpoint,
                                "payload": payload,
                                "response_code": response.status_code
                            },
                            remediation="Implement proper input validation and sanitization"
                        ))
                    else:
                        results.append(SecurityTestResult(
                            test_name=test_name,
                            category="injection",
                            severity="low",
                            status="passed",
                            description="No NoSQL injection vulnerability detected",
                            details={
                                "endpoint": endpoint,
                                "payload": payload
                            }
                        ))
                
                except Exception as e:
                    results.append(SecurityTestResult(
                        test_name=f"nosql_injection_error_{hash(str(payload)) % 1000}",
                        category="injection",
                        severity="medium",
                        status="warning",
                        description="NoSQL injection test encountered error",
                        details={"error": str(e)}
                    ))
        
        return results

class XSSTester:
    """Test for Cross-Site Scripting vulnerabilities"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_reflected_xss(self) -> List[SecurityTestResult]:
        """Test for reflected XSS vulnerabilities"""
        results = []
        
        # XSS payloads
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "<svg onload=alert('XSS')>",
            "<%2Fscript%3E%3Cscript%3Ealert('XSS')%3C%2Fscript%3E"
        ]
        
        test_endpoints = [
            {
                "path": "/api/v1/content/preview",
                "method": "POST",
                "payload_field": "content"
            },
            {
                "path": "/api/v1/search",
                "method": "GET",
                "param_field": "q"
            }
        ]
        
        for endpoint in test_endpoints:
            for payload in xss_payloads:
                try:
                    if endpoint["method"] == "GET":
                        params = {endpoint["param_field"]: payload}
                        response = await self.client.get(
                            f"{self.base_url}{endpoint['path']}",
                            params=params
                        )
                    elif endpoint["method"] == "POST":
                        data = {endpoint["payload_field"]: payload}
                        response = await self.client.post(
                            f"{self.base_url}{endpoint['path']}",
                            json=data
                        )
                    
                    # Check if payload is reflected in response
                    response_text = response.text
                    is_vulnerable = payload in response_text
                    
                    # Check for proper encoding
                    encoded_payload = response_text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
                    is_properly_encoded = payload not in encoded_payload
                    
                    test_name = f"reflected_xss_{endpoint['path'].replace('/', '_')}_{hash(payload) % 1000}"
                    
                    if is_vulnerable and not is_properly_encoded:
                        results.append(SecurityTestResult(
                            test_name=test_name,
                            category="xss",
                            severity="high",
                            status="failed",
                            description="Reflected XSS vulnerability detected",
                            details={
                                "endpoint": endpoint["path"],
                                "payload": payload,
                                "response_contains_payload": is_vulnerable
                            },
                            remediation="Implement proper output encoding and input validation"
                        ))
                    else:
                        results.append(SecurityTestResult(
                            test_name=test_name,
                            category="xss",
                            severity="low",
                            status="passed",
                            description="No reflected XSS vulnerability detected",
                            details={
                                "endpoint": endpoint["path"],
                                "payload": payload,
                                "properly_encoded": is_properly_encoded
                            }
                        ))
                
                except Exception as e:
                    results.append(SecurityTestResult(
                        test_name=f"reflected_xss_error_{hash(payload) % 1000}",
                        category="xss",
                        severity="medium",
                        status="warning",
                        description="Reflected XSS test encountered error",
                        details={"error": str(e)}
                    ))
        
        return results

class DataProtectionTester:
    """Test data protection and privacy controls"""
    
    def __init__(self, base_url: str, database_url: str = None):
        self.base_url = base_url
        self.database_url = database_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_sensitive_data_exposure(self) -> List[SecurityTestResult]:
        """Test for sensitive data exposure"""
        results = []
        
        # Test for sensitive data in API responses
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/user/profile")
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Check for exposed sensitive fields
                sensitive_fields = [
                    "password", "secret", "token", "key", "hash",
                    "ssn", "credit_card", "bank_account", "api_key"
                ]
                
                exposed_fields = []
                for field in sensitive_fields:
                    if self._check_field_in_response(response_data, field):
                        exposed_fields.append(field)
                
                if exposed_fields:
                    results.append(SecurityTestResult(
                        test_name="sensitive_data_exposure_api",
                        category="data_protection",
                        severity="critical",
                        status="failed",
                        description="Sensitive data exposed in API response",
                        details={"exposed_fields": exposed_fields},
                        remediation="Remove sensitive fields from API responses"
                    ))
                else:
                    results.append(SecurityTestResult(
                        test_name="sensitive_data_exposure_api",
                        category="data_protection",
                        severity="low",
                        status="passed",
                        description="No sensitive data exposure detected in API",
                        details={"checked_fields": sensitive_fields}
                    ))
        
        except Exception as e:
            results.append(SecurityTestResult(
                test_name="sensitive_data_exposure_api",
                category="data_protection",
                severity="medium",
                status="warning",
                description="Could not test API for sensitive data exposure",
                details={"error": str(e)}
            ))
        
        return results
    
    def _check_field_in_response(self, data: Any, field_name: str) -> bool:
        """Recursively check for field in response data"""
        if isinstance(data, dict):
            for key, value in data.items():
                if field_name.lower() in key.lower():
                    return True
                if self._check_field_in_response(value, field_name):
                    return True
        elif isinstance(data, list):
            for item in data:
                if self._check_field_in_response(item, field_name):
                    return True
        return False
    
    async def test_data_encryption(self) -> List[SecurityTestResult]:
        """Test data encryption requirements"""
        results = []
        
        # Test HTTPS enforcement
        try:
            http_url = self.base_url.replace("https://", "http://")
            response = await self.client.get(f"{http_url}/api/v1/health")
            
            if response.status_code in [301, 302] and "https" in response.headers.get("location", ""):
                results.append(SecurityTestResult(
                    test_name="https_enforcement",
                    category="data_protection",
                    severity="medium",
                    status="passed",
                    description="HTTPS properly enforced with redirect",
                    details={"redirect_location": response.headers.get("location")}
                ))
            elif self.base_url.startswith("https://"):
                results.append(SecurityTestResult(
                    test_name="https_enforcement",
                    category="data_protection",
                    severity="medium",
                    status="passed",
                    description="HTTPS used for secure communication",
                    details={"base_url": self.base_url}
                ))
            else:
                results.append(SecurityTestResult(
                    test_name="https_enforcement",
                    category="data_protection", 
                    severity="high",
                    status="failed",
                    description="HTTPS not enforced",
                    details={"response_code": response.status_code},
                    remediation="Implement HTTPS enforcement"
                ))
        
        except Exception as e:
            results.append(SecurityTestResult(
                test_name="https_enforcement",
                category="data_protection",
                severity="medium",
                status="warning",
                description="Could not test HTTPS enforcement",
                details={"error": str(e)}
            ))
        
        return results

class ComplianceTester:
    """Test regulatory compliance requirements"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_gdpr_compliance(self) -> List[ComplianceCheckResult]:
        """Test GDPR compliance requirements"""
        results = []
        
        # Test right to access
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/user/data-export",
                headers={"Authorization": "Bearer test_token"}
            )
            
            if response.status_code in [200, 202]:
                results.append(ComplianceCheckResult(
                    regulation="GDPR",
                    requirement="Right to Access (Article 15)",
                    status="compliant",
                    evidence={"endpoint_available": True, "response_code": response.status_code}
                ))
            else:
                results.append(ComplianceCheckResult(
                    regulation="GDPR",
                    requirement="Right to Access (Article 15)",
                    status="non_compliant",
                    evidence={"endpoint_available": False, "response_code": response.status_code},
                    gap_analysis="Implement user data export functionality"
                ))
        except Exception as e:
            results.append(ComplianceCheckResult(
                regulation="GDPR",
                requirement="Right to Access (Article 15)",
                status="non_compliant",
                evidence={"error": str(e)},
                gap_analysis="Implement user data export endpoint"
            ))
        
        # Test right to erasure
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/user/data",
                headers={"Authorization": "Bearer test_token"}
            )
            
            if response.status_code in [200, 202, 204]:
                results.append(ComplianceCheckResult(
                    regulation="GDPR",
                    requirement="Right to Erasure (Article 17)",
                    status="compliant",
                    evidence={"endpoint_available": True, "response_code": response.status_code}
                ))
            else:
                results.append(ComplianceCheckResult(
                    regulation="GDPR",
                    requirement="Right to Erasure (Article 17)",
                    status="non_compliant",
                    evidence={"endpoint_available": False, "response_code": response.status_code},
                    gap_analysis="Implement user data deletion functionality"
                ))
        except Exception as e:
            results.append(ComplianceCheckResult(
                regulation="GDPR",
                requirement="Right to Erasure (Article 17)",
                status="non_compliant",
                evidence={"error": str(e)},
                gap_analysis="Implement user data deletion endpoint"
            ))
        
        # Test consent management
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/user/consent")
            
            if response.status_code == 200:
                consent_data = response.json()
                has_consent_tracking = "consent_given" in consent_data or "consents" in consent_data
                
                if has_consent_tracking:
                    results.append(ComplianceCheckResult(
                        regulation="GDPR",
                        requirement="Consent Management (Article 7)",
                        status="compliant",
                        evidence={"consent_tracking": True, "consent_data": consent_data}
                    ))
                else:
                    results.append(ComplianceCheckResult(
                        regulation="GDPR",
                        requirement="Consent Management (Article 7)",
                        status="partial",
                        evidence={"consent_tracking": False, "response": consent_data},
                        gap_analysis="Implement comprehensive consent tracking"
                    ))
            else:
                results.append(ComplianceCheckResult(
                    regulation="GDPR",
                    requirement="Consent Management (Article 7)",
                    status="non_compliant",
                    evidence={"endpoint_available": False},
                    gap_analysis="Implement consent management endpoint"
                ))
        except Exception as e:
            results.append(ComplianceCheckResult(
                regulation="GDPR",
                requirement="Consent Management (Article 7)",
                status="non_compliant",
                evidence={"error": str(e)},
                gap_analysis="Implement consent management system"
            ))
        
        return results
    
    async def test_finra_compliance(self) -> List[ComplianceCheckResult]:
        """Test FINRA compliance for financial content"""
        results = []
        
        # Test record keeping requirements
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/audit/records",
                headers={"Authorization": "Bearer admin_token"}
            )
            
            if response.status_code == 200:
                audit_data = response.json()
                has_required_fields = all(field in str(audit_data) for field in [
                    "timestamp", "user_id", "action", "content_id"
                ])
                
                if has_required_fields:
                    results.append(ComplianceCheckResult(
                        regulation="FINRA",
                        requirement="Record Keeping (Rule 4511)",
                        status="compliant",
                        evidence={"audit_logging": True, "required_fields": True}
                    ))
                else:
                    results.append(ComplianceCheckResult(
                        regulation="FINRA",
                        requirement="Record Keeping (Rule 4511)",
                        status="partial",
                        evidence={"audit_logging": True, "required_fields": False},
                        gap_analysis="Include all required audit fields"
                    ))
            else:
                results.append(ComplianceCheckResult(
                    regulation="FINRA",
                    requirement="Record Keeping (Rule 4511)",
                    status="non_compliant",
                    evidence={"audit_endpoint": False},
                    gap_analysis="Implement comprehensive audit logging"
                ))
        except Exception as e:
            results.append(ComplianceCheckResult(
                regulation="FINRA",
                requirement="Record Keeping (Rule 4511)",
                status="non_compliant",
                evidence={"error": str(e)},
                gap_analysis="Implement audit logging system"
            ))
        
        # Test content supervision
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/content/generate",
                json={
                    "domain": "finance",
                    "source_content": "Investment advice content",
                    "compliance_review": True
                }
            )
            
            if response.status_code == 200:
                content_data = response.json()
                has_compliance_review = "compliance_review" in content_data or "supervision" in content_data
                
                if has_compliance_review:
                    results.append(ComplianceCheckResult(
                        regulation="FINRA",
                        requirement="Content Supervision (Rule 3110)",
                        status="compliant",
                        evidence={"supervision_process": True}
                    ))
                else:
                    results.append(ComplianceCheckResult(
                        regulation="FINRA",
                        requirement="Content Supervision (Rule 3110)",
                        status="non_compliant",
                        evidence={"supervision_process": False},
                        gap_analysis="Implement content supervision workflow"
                    ))
            else:
                results.append(ComplianceCheckResult(
                    regulation="FINRA",
                    requirement="Content Supervision (Rule 3110)",
                    status="non_compliant",
                    evidence={"response_code": response.status_code},
                    gap_analysis="Implement financial content generation with supervision"
                ))
        except Exception as e:
            results.append(ComplianceCheckResult(
                regulation="FINRA",
                requirement="Content Supervision (Rule 3110)",
                status="non_compliant",
                evidence={"error": str(e)},
                gap_analysis="Implement supervised content generation"
            ))
        
        return results

class SecurityTestSuite:
    """Complete security testing suite"""
    
    def __init__(self, base_url: str, database_url: str = None):
        self.base_url = base_url
        self.database_url = database_url
        self.auth_tester = AuthenticationTester(base_url)
        self.authz_tester = AuthorizationTester(base_url)
        self.injection_tester = InjectionTester(base_url)
        self.xss_tester = XSSTester(base_url)
        self.data_tester = DataProtectionTester(base_url, database_url)
        self.compliance_tester = ComplianceTester(base_url)
    
    async def run_comprehensive_security_tests(self) -> Dict[str, Any]:
        """Run complete security test suite"""
        logger.info("Starting comprehensive security test suite")
        
        all_security_results = []
        all_compliance_results = []
        
        # Authentication tests
        try:
            auth_results = await self.auth_tester.test_jwt_token_validation()
            auth_results.extend(await self.auth_tester.test_session_security())
            all_security_results.extend(auth_results)
        except Exception as e:
            logger.error(f"Authentication tests failed: {e}")
        
        # Authorization tests
        try:
            authz_results = await self.authz_tester.test_rbac_enforcement()
            authz_results.extend(await self.authz_tester.test_horizontal_privilege_escalation())
            all_security_results.extend(authz_results)
        except Exception as e:
            logger.error(f"Authorization tests failed: {e}")
        
        # Injection tests
        try:
            injection_results = await self.injection_tester.test_sql_injection()
            injection_results.extend(await self.injection_tester.test_nosql_injection())
            all_security_results.extend(injection_results)
        except Exception as e:
            logger.error(f"Injection tests failed: {e}")
        
        # XSS tests
        try:
            xss_results = await self.xss_tester.test_reflected_xss()
            all_security_results.extend(xss_results)
        except Exception as e:
            logger.error(f"XSS tests failed: {e}")
        
        # Data protection tests
        try:
            data_results = await self.data_tester.test_sensitive_data_exposure()
            data_results.extend(await self.data_tester.test_data_encryption())
            all_security_results.extend(data_results)
        except Exception as e:
            logger.error(f"Data protection tests failed: {e}")
        
        # Compliance tests
        try:
            gdpr_results = await self.compliance_tester.test_gdpr_compliance()
            finra_results = await self.compliance_tester.test_finra_compliance()
            all_compliance_results.extend(gdpr_results)
            all_compliance_results.extend(finra_results)
        except Exception as e:
            logger.error(f"Compliance tests failed: {e}")
        
        # Analyze results
        security_summary = self._analyze_security_results(all_security_results)
        compliance_summary = self._analyze_compliance_results(all_compliance_results)
        
        # Generate reports
        await self._generate_security_reports(all_security_results, all_compliance_results, 
                                            security_summary, compliance_summary)
        
        logger.info("Comprehensive security test suite completed")
        return {
            "security_summary": security_summary,
            "compliance_summary": compliance_summary,
            "detailed_security_results": [asdict(r) for r in all_security_results],
            "detailed_compliance_results": [asdict(r) for r in all_compliance_results]
        }
    
    def _analyze_security_results(self, results: List[SecurityTestResult]) -> Dict[str, Any]:
        """Analyze security test results"""
        if not results:
            return {"error": "No security test results"}
        
        # Count by severity and status
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        status_counts = {"passed": 0, "failed": 0, "warning": 0}
        category_results = {}
        
        for result in results:
            severity_counts[result.severity] += 1
            status_counts[result.status] += 1
            
            if result.category not in category_results:
                category_results[result.category] = {"passed": 0, "failed": 0, "warning": 0}
            category_results[result.category][result.status] += 1
        
        # Calculate risk score
        risk_score = (
            severity_counts["critical"] * 10 +
            severity_counts["high"] * 7 +
            severity_counts["medium"] * 4 +
            severity_counts["low"] * 2 +
            severity_counts["info"] * 1
        )
        
        failed_critical = len([r for r in results if r.severity == "critical" and r.status == "failed"])
        failed_high = len([r for r in results if r.severity == "high" and r.status == "failed"])
        
        overall_risk = "critical" if failed_critical > 0 else \
                      "high" if failed_high > 2 else \
                      "medium" if risk_score > 20 else "low"
        
        return {
            "total_tests": len(results),
            "severity_distribution": severity_counts,
            "status_distribution": status_counts,
            "category_results": category_results,
            "risk_score": risk_score,
            "overall_risk_level": overall_risk,
            "critical_failures": failed_critical,
            "high_failures": failed_high,
            "failed_tests": [
                {
                    "name": r.test_name,
                    "category": r.category,
                    "severity": r.severity,
                    "description": r.description
                }
                for r in results if r.status == "failed"
            ]
        }
    
    def _analyze_compliance_results(self, results: List[ComplianceCheckResult]) -> Dict[str, Any]:
        """Analyze compliance test results"""
        if not results:
            return {"error": "No compliance test results"}
        
        regulation_status = {}
        for result in results:
            if result.regulation not in regulation_status:
                regulation_status[result.regulation] = {
                    "compliant": 0, "non_compliant": 0, "partial": 0
                }
            regulation_status[result.regulation][result.status] += 1
        
        overall_compliance = all(
            status["non_compliant"] == 0 
            for status in regulation_status.values()
        )
        
        return {
            "total_checks": len(results),
            "regulation_status": regulation_status,
            "overall_compliance": overall_compliance,
            "compliance_gaps": [
                {
                    "regulation": r.regulation,
                    "requirement": r.requirement,
                    "gap_analysis": r.gap_analysis
                }
                for r in results if r.status == "non_compliant" and r.gap_analysis
            ]
        }
    
    async def _generate_security_reports(self, security_results: List[SecurityTestResult],
                                       compliance_results: List[ComplianceCheckResult],
                                       security_summary: Dict[str, Any],
                                       compliance_summary: Dict[str, Any]):
        """Generate comprehensive security reports"""
        # Generate JSON report
        report_data = {
            "test_timestamp": datetime.now(timezone.utc).isoformat(),
            "security_summary": security_summary,
            "compliance_summary": compliance_summary,
            "detailed_security_results": [asdict(r) for r in security_results],
            "detailed_compliance_results": [asdict(r) for r in compliance_results]
        }
        
        with open("/tmp/security_test_report.json", "w") as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info("Security test reports generated: /tmp/security_test_report.json")

# Main security testing execution
async def main():
    """Main security testing execution"""
    test_settings = TestSettings()
    
    suite = SecurityTestSuite(
        base_url=test_settings.API_BASE_URL,
        database_url=test_settings.DATABASE_URL
    )
    
    results = await suite.run_comprehensive_security_tests()
    
    print("\n" + "="*60)
    print("SECURITY TEST RESULTS SUMMARY")
    print("="*60)
    
    security_summary = results["security_summary"]
    print(f"Total Security Tests: {security_summary['total_tests']}")
    print(f"Overall Risk Level: {security_summary['overall_risk_level'].upper()}")
    print(f"Critical Failures: {security_summary['critical_failures']}")
    print(f"High-Risk Failures: {security_summary['high_failures']}")
    
    compliance_summary = results["compliance_summary"]
    print(f"\nCompliance Checks: {compliance_summary['total_checks']}")
    print(f"Overall Compliance: {'PASS' if compliance_summary['overall_compliance'] else 'FAIL'}")
    
    if security_summary.get("failed_tests"):
        print(f"\nCritical Security Issues:")
        for test in security_summary["failed_tests"][:5]:  # Show top 5
            print(f"  - {test['name']}: {test['description']}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(main())