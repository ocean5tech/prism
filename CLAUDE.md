# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Prism is a new project currently being set up. The repository structure and architecture will be defined as development progresses.

## Development Commands

*To be populated once build tools and scripts are configured*

## Architecture

*To be documented once the codebase structure is established*

## Important Notes

- This project is in its initial setup phase
- Development commands and architecture details will be added as the project evolves
- Update this file as new tools, frameworks, and patterns are introduced

# Prism - Multi-Domain Content Generation Platform

## 🎯 Project Overview

### Multi-Domain Content Generation Platform
```markdown
Project Name: Intelligent Content Generation Factory
Project Type: Multi-domain automated content generation and publishing platform
Core Tech Stack: n8n workflow + Python microservices + LLM integration

Key Features:
1. Multi-domain support: Finance, Sports, Technology with config-driven expansion
2. Intelligent style control: Random style parameters to avoid content patterns
3. Adversarial optimization: Generation Agent + Detection Agent for continuous quality improvement
4. Workflow orchestration: n8n visual management of entire content production process
5. Platform distribution: Automated multi-platform content publishing and monitoring

Technical Architecture:
- Orchestration Layer: n8n workflow engine
- Service Layer: Python FastAPI microservices
- Storage Layer: PostgreSQL + Redis + File storage
- AI Layer: Claude API + Random style parameter system

Development Environment: Claude Code
Delivery Goal: Reusable content generation platform supporting rapid domain expansion
```

---

## 🤝 Team Collaboration Rules

### **Core Collaboration Principles**

**PRIORITY HIERARCHY**
1. **User Instructions** - Always prioritize explicit user commands
2. **Domain Requirements** - Follow multi-domain content generation constraints
3. **Technical Constraints** - Respect Claude Code environment limitations
4. **Best Practices** - Apply industry standards when not conflicting with above

**COMMUNICATION PROTOCOL**
- Each agent must clearly state their role and scope when activated
- All outputs must include specific handoff instructions to relevant agents
- Cross-functional decisions require explicit agreement between agents
- Escalate conflicts to user for resolution

### **Agent Activation Commands**

**Quick Start Commands:**
- `@pm` - Activate Product Manager Agent
- `@arch` - Activate System Architect Agent  
- `@workflow` - Activate Workflow Engineer Agent
- `@backend` - Activate Backend Engineer Agent
- `@data` - Activate Data Engineer Agent
- `@test` - Activate Test Engineer Agent
- `@devops` - Activate DevOps Engineer Agent
- `@team` - Activate Team Coordination Mode

### **Standard Handoff Protocols**

**Input Requirements for Each Agent:**
```markdown
@pm → Requires: Business context, user requirements, domain specifications
@arch → Requires: Product requirements document, technical constraints, scalability needs
@workflow → Requires: Architecture design, integration specifications, business logic
@backend → Requires: API specifications, service boundaries, data models
@data → Requires: Data architecture, storage requirements, Agent memory needs
@test → Requires: Complete implementation, quality standards, test environments
@devops → Requires: System components, deployment requirements, monitoring needs
```

**Output Deliverables from Each Agent:**
```markdown
@pm → Delivers: PRD, user stories, acceptance criteria, business metrics
@arch → Delivers: System design, ADRs, API specifications, deployment architecture
@workflow → Delivers: n8n workflows, custom nodes, integration patterns
@backend → Delivers: FastAPI services, AI integration, business logic implementation
@data → Delivers: Data models, ETL pipelines, Agent memory system, storage optimization
@test → Delivers: Test strategies, automation suites, quality reports, monitoring setup
@devops → Delivers: Deployment configs, CI/CD pipelines, monitoring dashboards, runbooks
```

---

## 🔄 Team Coordination Workflows

### **Standard Project Flow**
```mermaid
graph TD
    A[@pm] --> B[@arch]
    B --> C[@workflow]
    B --> D[@backend]
    B --> E[@data]
    C --> F[@test]
    D --> F
    E --> F
    F --> G[@devops]
```

### **Cross-Agent Communication Protocol**

**Escalation Matrix:**
- **Level 1**: Technical clarification between adjacent agents
- **Level 2**: Architecture conflicts → User intervention required
- **Level 3**: Business requirement conflicts → Product Manager + User decision

**Handoff Validation:**
- Each agent must confirm receipt of valid inputs before proceeding
- All outputs must include success criteria for the next agent
- Failed handoffs must be documented with specific blockers

### **Quality Gates**
- **Product Manager**: Business value validation, user story completeness
- **System Architect**: Technical feasibility, scalability verification  
- **Implementation Agents**: Code quality, test coverage, deployment readiness
- **Final Validation**: End-to-end testing, performance benchmarks, security compliance

### **Emergency Protocols**
- **Blocker Resolution**: `@team escalate [specific issue]`
- **Requirement Changes**: All agents pause, Product Manager reassessment required
- **Technical Debt**: Architecture review required before proceeding

---

## 🎯 Success Metrics

**Team Performance KPIs:**
- **Handoff Efficiency**: < 2 iterations between adjacent agents
- **Requirement Traceability**: 100% feature mapping from PM to DevOps
- **Quality Compliance**: Zero critical issues in production deployment
- **Delivery Velocity**: MVP delivery within 5 agent interaction cycles

**Individual Agent KPIs:**
- **Output Quality**: Adherence to specified format and completeness
- **Collaboration Effectiveness**: Clear handoff instructions and dependency identification
- **User Instruction Compliance**: Zero deviations from explicit user commands
- **Domain Knowledge Application**: Proper use of multi-domain content generation expertise

---

**Remember**: User instructions always take priority over default behaviors. Each agent must strictly adhere to their role boundaries while ensuring seamless collaboration toward the common goal of building a robust multi-domain content generation platform.
