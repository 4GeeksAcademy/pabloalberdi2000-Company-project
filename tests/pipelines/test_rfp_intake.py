"""
Test Suite - RFP Intake Pipeline (Deterministic)

Tests DETERMINISTAS para el sistema multi-agente de RFPs.

CRÍTICO:
- Tests NO invocan LLM en vivo (usar mocks o fixtures fijas)
- Validar comportamiento del pipeline sin variabilidad estocástica
- Cobertura: Classifier, Orchestrator, Workers, Synthesizer
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json

from data.pipelines.rfp_intake.graph import (
    classifier_node,
    orchestrator_node,
    department_worker_node,
    synthesizer_node,
    RFPState
)
from services.models.rfp import DepartmentType


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def sample_rfp_text():
    """
    Fixture: RFP válida de muestra.

    Contiene solicitud explícita, especificaciones técnicas,
    plazos y datos del solicitante.
    """
    return """
# REQUEST FOR PROPOSAL - Digital Restaurant Management System

**Client**: Acme Corporation
**Contact**: john.doe@acme.com
**Project Title**: Multi-Location Digital Menu & Operations System
**Submission Deadline**: December 15, 2024
**Budget Range**: $50,000 - $100,000

## Project Overview

Acme Corporation seeks proposals for implementing a comprehensive digital management system for our restaurant chain operations.

## Requirements by Department

### Operations Management
- Real-time inventory management across 14 locations
- Sales dashboard with multi-currency support (COP/USD)
- Automated alerts for low stock situations
- Integration with existing POS systems in Colombia and Florida

### Technology Infrastructure
- Central API for menus, sales, and customer data
- Real-time telemetry and monitoring
- Mobile app backend with scalability for 10,000+ concurrent users
- Integration with third-party delivery platforms

### Marketing & Customer Experience
- Mobile application for iOS and Android
- Digital loyalty program with points system
- CRM integration with purchase history tracking
- Personalized promotions engine

### Human Resources
- Employee portal for schedule management
- Onboarding automation workflows
- Multi-location staff directory
- Bi-lingual support (Spanish/English)

## Technical Constraints
- Must support legacy POS systems
- Data residency requirements for Colombian customer data
- SOC 2 compliance required
- Maximum 99.5% uptime SLA

## Deliverables
1. Technical architecture document
2. Detailed project timeline
3. Cost breakdown by phase
4. Risk assessment and mitigation plan

## Evaluation Criteria
- Technical capability (40%)
- Cost competitiveness (30%)
- Implementation timeline (20%)
- Post-launch support (10%)
"""


@pytest.fixture
def invalid_document_text():
    """
    Fixture: Documento NO RFP (manual de empleado).

    No contiene solicitud de propuesta ni requerimientos contractuales.
    """
    return """
# EMPLOYEE HANDBOOK - Acme Corporation

## Welcome to Acme

Welcome to Acme Corporation. This handbook contains important information about your employment.

## Company Policies

### Work Hours
Standard work hours are Monday to Friday, 9 AM to 5 PM.

### Dress Code
Business casual attire is required in the office.

### Vacation Policy
Employees accrue 15 days of vacation per year.

## Benefits
- Health insurance
- 401(k) matching
- Gym membership reimbursement
"""


@pytest.fixture
def sample_rfp_state():
    """
    Fixture: Estado inicial para tests de nodos.
    """
    return {
        "ticket_id": 1,
        "markdown_content": "Sample RFP content...",
        "markdown_path": "/tmp/test.md",
        "client_name": "Acme Corp",
        "submission_deadline": "2024-12-15",
        "budget_range": "$50,000 - $100,000",
        "project_title": "Digital Management System",
        "is_valid_rfp": None,
        "classifier_confidence": None,
        "rejection_reason": None,
        "workstreams": {},
        "department_findings": {},
        "executive_summary": None,
        "synthesis_data": None,
        "should_discard": False,
        "error": None
    }


@pytest.fixture
def mock_openai_response():
    """
    Fixture: Mock de respuesta de OpenAI para tests deterministas.
    """
    def _mock_response(content_dict):
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps(content_dict)
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        return mock_response

    return _mock_response


# ============================================================
# TESTS DE CLASSIFIER
# ============================================================

class TestClassifierNode:
    """Tests para el nodo Classifier"""

    @patch('data.pipelines.rfp_intake.graph.openai.OpenAI')
    def test_classifier_accepts_valid_rfp(self, mock_openai, sample_rfp_state, mock_openai_response):
        """
        Test: Classifier acepta RFP válida con confianza alta.
        """
        # Mock de respuesta OpenAI
        mock_client = Mock()
        mock_openai.return_value = mock_client

        mock_client.chat.completions.create.return_value = mock_openai_response({
            "is_valid_rfp": True,
            "confidence": 0.92,
            "rejection_reason": None,
            "detected_project_type": "Digital Management System",
            "requires_manual_review": False,
            "extracted_metadata": {
                "client_name": "Acme Corporation",
                "submission_deadline": "2024-12-15",
                "budget_range": "$50,000 - $100,000",
                "project_title": "Multi-Location Digital Menu System"
            }
        })

        # Ejecutar nodo
        result = classifier_node(sample_rfp_state)

        # Validaciones
        assert result["is_valid_rfp"] == True
        assert result["classifier_confidence"] == 0.92
        assert result["rejection_reason"] is None
        assert result["should_discard"] == False
        assert result["client_name"] == "Acme Corporation"

    @patch('data.pipelines.rfp_intake.graph.openai.OpenAI')
    def test_classifier_rejects_invalid_document(self, mock_openai, sample_rfp_state, mock_openai_response):
        """
        Test: Classifier rechaza documento no-RFP con confianza alta.
        """
        # Mock de respuesta OpenAI
        mock_client = Mock()
        mock_openai.return_value = mock_client

        mock_client.chat.completions.create.return_value = mock_openai_response({
            "is_valid_rfp": False,
            "confidence": 0.95,
            "rejection_reason": "Documento interno (manual de empleado), no es una solicitud de propuesta",
            "detected_project_type": "Employee Handbook",
            "requires_manual_review": False,
            "extracted_metadata": {}
        })

        # Ejecutar nodo
        result = classifier_node(sample_rfp_state)

        # Validaciones
        assert result["is_valid_rfp"] == False
        assert result["classifier_confidence"] == 0.95
        assert result["rejection_reason"] is not None
        assert result["should_discard"] == True  # Confianza >= 0.7

    @patch('data.pipelines.rfp_intake.graph.openai.OpenAI')
    def test_classifier_allows_borderline_for_manual_review(self, mock_openai, sample_rfp_state, mock_openai_response):
        """
        Test: Classifier NO descarta automáticamente documentos con confianza baja (anti-falso-negativo).
        """
        # Mock de respuesta OpenAI
        mock_client = Mock()
        mock_openai.return_value = mock_client

        mock_client.chat.completions.create.return_value = mock_openai_response({
            "is_valid_rfp": False,
            "confidence": 0.55,  # Confianza baja
            "rejection_reason": "Formato no estándar, requiere revisión manual",
            "detected_project_type": "Unclear",
            "requires_manual_review": True,
            "extracted_metadata": {}
        })

        # Ejecutar nodo
        result = classifier_node(sample_rfp_state)

        # Validaciones: NO debe descartar con confianza < 0.7
        assert result["is_valid_rfp"] == False
        assert result["classifier_confidence"] == 0.55
        assert result["should_discard"] == False  # Confianza < 0.7 → permite


# ============================================================
# TESTS DE ORCHESTRATOR
# ============================================================

class TestOrchestratorNode:
    """Tests para el nodo Orchestrator"""

    @patch('data.pipelines.rfp_intake.graph.openai.OpenAI')
    def test_orchestrator_identifies_multiple_departments(self, mock_openai, sample_rfp_state, mock_openai_response):
        """
        Test: Orchestrator identifica correctamente múltiples departamentos involucrados.
        """
        # Mock de respuesta OpenAI
        mock_client = Mock()
        mock_openai.return_value = mock_client

        mock_client.chat.completions.create.return_value = mock_openai_response({
            "workstreams": {
                "operaciones": {
                    "section_title": "Operations Management",
                    "extracted_text": "Real-time inventory management across 14 locations...",
                    "priority": "alta",
                    "metadata": {
                        "deadline": "2024-12-15",
                        "estimated_complexity": "alta"
                    }
                },
                "tecnologia": {
                    "section_title": "Technology Infrastructure",
                    "extracted_text": "Central API for menus, sales, and customer data...",
                    "priority": "alta",
                    "metadata": {
                        "deadline": "2024-12-15",
                        "estimated_complexity": "alta"
                    }
                },
                "marketing": {
                    "section_title": "Marketing & Customer Experience",
                    "extracted_text": "Mobile application for iOS and Android...",
                    "priority": "media",
                    "metadata": {
                        "deadline": "2024-12-15",
                        "estimated_complexity": "media"
                    }
                },
                "rrhh": {
                    "section_title": "Human Resources",
                    "extracted_text": "Employee portal for schedule management...",
                    "priority": "baja",
                    "metadata": {
                        "deadline": "2024-12-15",
                        "estimated_complexity": "baja"
                    }
                }
            },
            "involved_departments": ["operaciones", "tecnologia", "marketing", "rrhh"]
        })

        # Ejecutar nodo
        result = orchestrator_node(sample_rfp_state)

        # Validaciones
        assert "workstreams" in result
        assert len(result["workstreams"]) == 4
        assert "operaciones" in result["workstreams"]
        assert "tecnologia" in result["workstreams"]
        assert "marketing" in result["workstreams"]
        assert "rrhh" in result["workstreams"]

        # Validar estructura de workstream
        ops_workstream = result["workstreams"]["operaciones"]
        assert "section_title" in ops_workstream
        assert "extracted_text" in ops_workstream
        assert "priority" in ops_workstream


# ============================================================
# TESTS DE WORKERS
# ============================================================

class TestDepartmentWorkerNode:
    """Tests para nodos de Workers por departamento"""

    @patch('data.pipelines.rfp_intake.graph.openai.OpenAI')
    def test_worker_does_not_invent_missing_data(self, mock_openai, sample_rfp_state, mock_openai_response):
        """
        Test CRÍTICO: Worker NO inventa datos que no están en el documento.

        Si falta presupuesto específico → debe reportarlo en missing_data.
        """
        # Preparar estado con workstream sin presupuesto detallado
        sample_rfp_state["workstreams"] = {
            "operaciones": {
                "section_title": "Operations",
                "extracted_text": "Necesitamos un dashboard de ventas en tiempo real. No se menciona presupuesto específico para esta sección."
            }
        }

        # Mock de respuesta OpenAI (worker reporta missing_data)
        mock_client = Mock()
        mock_openai.return_value = mock_client

        mock_client.chat.completions.create.return_value = mock_openai_response({
            "requirements": [
                "Dashboard de ventas en tiempo real",
                "Integración multi-local"
            ],
            "constraints": [
                "Debe soportar sistemas POS legacy"
            ],
            "missing_data": [
                "Presupuesto específico para operaciones",
                "Plazo de implementación detallado",
                "Volumen de transacciones esperado"
            ],
            "estimated_effort": "alto",
            "blockers": [],
            "dependencies": ["tecnologia"],
            "notes": "Requerimientos claros pero faltan métricas de carga"
        })

        # Ejecutar worker
        result = department_worker_node(sample_rfp_state, DepartmentType.OPERACIONES)

        # Validaciones
        findings = result["department_findings"]["operaciones"]

        assert "requirements" in findings
        assert len(findings["requirements"]) > 0

        # CRÍTICO: Debe reportar missing_data, NO inventar valores
        assert "missing_data" in findings
        assert len(findings["missing_data"]) > 0
        assert any("presupuesto" in item.lower() or "budget" in item.lower() for item in findings["missing_data"])

    @patch('data.pipelines.rfp_intake.graph.openai.OpenAI')
    def test_worker_extracts_requirements_correctly(self, mock_openai, sample_rfp_state, mock_openai_response):
        """
        Test: Worker extrae correctamente requerimientos explícitos.
        """
        # Preparar estado con workstream detallado
        sample_rfp_state["workstreams"] = {
            "tecnologia": {
                "section_title": "Technology Infrastructure",
                "extracted_text": """
                Central API requirements:
                - RESTful API with JWT authentication
                - Rate limiting: 1000 req/min per client
                - 99.5% uptime SLA
                - PostgreSQL primary database
                - Redis caching layer
                - Docker containerization
                """
            }
        }

        # Mock de respuesta OpenAI
        mock_client = Mock()
        mock_openai.return_value = mock_client

        mock_client.chat.completions.create.return_value = mock_openai_response({
            "requirements": [
                "RESTful API con autenticación JWT",
                "Rate limiting de 1000 req/min",
                "SLA de 99.5% uptime",
                "Base de datos PostgreSQL",
                "Capa de caché Redis",
                "Contenerización Docker"
            ],
            "constraints": [
                "Cumplir SLA de 99.5%"
            ],
            "missing_data": [],
            "estimated_effort": "medio",
            "blockers": [],
            "dependencies": ["operaciones"],
            "notes": "Requerimientos técnicos bien definidos"
        })

        # Ejecutar worker
        result = department_worker_node(sample_rfp_state, DepartmentType.TECNOLOGIA)

        # Validaciones
        findings = result["department_findings"]["tecnologia"]

        assert len(findings["requirements"]) == 6
        assert "estimated_effort" in findings
        assert findings["estimated_effort"] == "medio"
        assert len(findings["missing_data"]) == 0  # No faltan datos


# ============================================================
# TESTS DE SYNTHESIZER
# ============================================================

class TestSynthesizerNode:
    """Tests para el nodo Synthesizer"""

    @patch('data.pipelines.rfp_intake.graph.openai.OpenAI')
    def test_synthesizer_detects_deadline_conflicts(self, mock_openai, sample_rfp_state, mock_openai_response):
        """
        Test: Synthesizer detecta conflictos en plazos reportados por diferentes workers.
        """
        # Preparar estado con findings contradictorios
        sample_rfp_state["department_findings"] = {
            "operaciones": {
                "requirements": ["Dashboard en tiempo real"],
                "missing_data": [],
                "estimated_effort": "alto",
                "notes": "Deadline mencionado: 2024-12-01"
            },
            "tecnologia": {
                "requirements": ["API central"],
                "missing_data": [],
                "estimated_effort": "alto",
                "notes": "Deadline mencionado: 2024-12-15"
            }
        }

        # Mock de respuesta OpenAI (synthesizer detecta conflicto)
        mock_client = Mock()
        mock_openai.return_value = mock_client

        mock_client.chat.completions.create.return_value = mock_openai_response({
            "executive_summary": "Análisis completado para 2 departamentos. Se detectaron conflictos en plazos de entrega.",
            "involved_departments": ["operaciones", "tecnologia"],
            "critical_dependencies": [
                "Tecnología debe entregar API antes que Operaciones integre el dashboard"
            ],
            "identified_risks": [
                {
                    "risk": "Conflicto en deadlines: Operaciones menciona 2024-12-01 pero Tecnología menciona 2024-12-15",
                    "severity": "alta",
                    "mitigation": "Clarificar con cliente el plazo definitivo"
                }
            ],
            "missing_critical_data": [],
            "recommended_workstreams": {
                "operaciones": {
                    "lead": "Felipe Guerrero",
                    "tasks": ["Especificar métricas del dashboard"],
                    "deadline": "Por confirmar con cliente",
                    "dependencies": ["tecnologia"]
                },
                "tecnologia": {
                    "lead": "Nicolás Park",
                    "tasks": ["Diseñar arquitectura API"],
                    "deadline": "Por confirmar con cliente",
                    "dependencies": []
                }
            },
            "synthesis_confidence": 0.85
        })

        # Ejecutar synthesizer
        result = synthesizer_node(sample_rfp_state)

        # Validaciones
        synthesis = result["synthesis_data"]

        assert "identified_risks" in synthesis
        assert len(synthesis["identified_risks"]) > 0

        # CRÍTICO: Debe detectar conflicto de deadlines
        risks_text = json.dumps(synthesis["identified_risks"]).lower()
        assert "deadline" in risks_text or "plazo" in risks_text or "conflict" in risks_text

    @patch('data.pipelines.rfp_intake.graph.openai.OpenAI')
    def test_synthesizer_escalates_multiple_missing_data(self, mock_openai, sample_rfp_state, mock_openai_response):
        """
        Test: Synthesizer escala cuando múltiples departamentos reportan missing_data crítica.
        """
        # Preparar estado con missing_data en múltiples departamentos
        sample_rfp_state["department_findings"] = {
            "operaciones": {
                "requirements": ["Dashboard"],
                "missing_data": ["Presupuesto", "Volumen de transacciones"],
                "estimated_effort": "alto"
            },
            "marketing": {
                "requirements": ["App móvil"],
                "missing_data": ["Presupuesto", "Usuarios objetivo"],
                "estimated_effort": "alto"
            },
            "tecnologia": {
                "requirements": ["API"],
                "missing_data": ["Presupuesto", "Carga esperada"],
                "estimated_effort": "alto"
            }
        }

        # Mock de respuesta OpenAI
        mock_client = Mock()
        mock_openai.return_value = mock_client

        mock_client.chat.completions.create.return_value = mock_openai_response({
            "executive_summary": "Análisis completado para 3 departamentos. CRÍTICO: Múltiples departamentos requieren datos faltantes para cotizar.",
            "involved_departments": ["operaciones", "marketing", "tecnologia"],
            "critical_dependencies": [],
            "identified_risks": [
                {
                    "risk": "Más de 2 departamentos requieren presupuesto específico para cotizar",
                    "severity": "alta",
                    "mitigation": "Solicitar al cliente breakdown de presupuesto por área"
                }
            ],
            "missing_critical_data": [
                "Presupuesto específico por departamento",
                "Volumen de transacciones esperado",
                "Número de usuarios objetivo",
                "Carga esperada del sistema"
            ],
            "recommended_workstreams": {},
            "synthesis_confidence": 0.60
        })

        # Ejecutar synthesizer
        result = synthesizer_node(sample_rfp_state)

        # Validaciones
        synthesis = result["synthesis_data"]

        assert "missing_critical_data" in synthesis
        assert len(synthesis["missing_critical_data"]) >= 3  # Múltiples datos faltantes

        # Debe elevar riesgo cuando > 2 departamentos tienen missing_data
        assert len(synthesis["identified_risks"]) > 0


# ============================================================
# CONFIGURACIÓN DE PYTEST
# ============================================================

@pytest.fixture(autouse=True)
def reset_state():
    """Reset estado entre tests para aislamiento"""
    yield
    # Cleanup si es necesario


if __name__ == "__main__":
    # Ejecutar tests
    pytest.main([__file__, "-v", "--tb=short"])
