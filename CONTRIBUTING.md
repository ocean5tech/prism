# 贡献指南 | Contributing Guide

感谢您对 Prism 项目的关注！我们欢迎所有形式的贡献，包括但不限于代码提交、问题反馈、功能建议和文档改进。

## 🤝 如何贡献

### 报告问题 | Report Issues

如果您发现了 bug 或有功能建议，请：

1. 检查 [Issues](https://github.com/ocean5tech/prism/issues) 中是否已有相似问题
2. 如果没有，请创建新的 Issue 并提供：
   - 清晰的问题描述
   - 复现步骤（对于 bug）
   - 预期行为 vs 实际行为
   - 环境信息（操作系统、Python版本等）
   - 相关截图（如适用）

### 代码贡献 | Code Contribution

#### 开发环境设置

1. **Fork 项目**
```bash
# 在 GitHub 上 Fork 项目，然后克隆到本地
git clone https://github.com/your-username/prism.git
cd prism
```

2. **创建开发环境**
```bash
# 创建虚拟环境
python -m venv prism_venv
source prism_venv/bin/activate  # Linux/Mac
# prism_venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

3. **配置开发环境**
```bash
# 复制环境变量模板
cp .env.example .env
# 编辑 .env 文件，配置开发环境变量
```

#### 开发流程

1. **创建分支**
```bash
# 从 main 分支创建新的功能分支
git checkout -b feature/your-feature-name
# 或修复分支
git checkout -b fix/issue-description
```

2. **编写代码**
   - 遵循项目的代码规范
   - 添加必要的注释
   - 编写相应的测试用例

3. **代码质量检查**
```bash
# 代码格式化
python -m black src/

# 代码风格检查
python -m flake8 src/

# 运行测试
pytest tests/
```

4. **提交更改**
```bash
# 添加修改的文件
git add .

# 提交更改（使用有意义的提交信息）
git commit -m "feat: add progressive UI for stock analysis"
# 或
git commit -m "fix: resolve CORS configuration issue"
```

5. **推送分支**
```bash
git push origin feature/your-feature-name
```

6. **创建 Pull Request**
   - 在 GitHub 上创建 Pull Request
   - 填写详细的 PR 描述
   - 关联相关的 Issues

#### 提交信息规范

我们使用约定式提交（Conventional Commits）规范：

```
<类型>(<范围>): <描述>

[可选正文]

[可选脚注]
```

**类型：**
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式调整（不影响功能）
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或工具更改

**示例：**
```
feat(ui): add progressive analysis interface
fix(api): resolve stock data validation error
docs: update installation guide
refactor(cache): optimize Redis connection pooling
```

#### 代码规范

- **Python 代码风格**: 遵循 PEP 8 规范
- **命名约定**: 
  - 函数和变量使用 `snake_case`
  - 类名使用 `PascalCase`
  - 常量使用 `UPPER_CASE`
- **注释**: 
  - 关键函数添加 docstring
  - 复杂逻辑添加行内注释
  - 使用中文或英文，保持一致
- **导入顺序**:
  ```python
  # 标准库
  import os
  import sys
  
  # 第三方库
  import fastapi
  import redis
  
  # 本地模块
  from src.core import config
  ```

#### 测试要求

- 为新功能添加相应的单元测试
- 确保所有现有测试通过
- 测试覆盖率应保持在合理水平
- 测试文件命名：`test_*.py`

```bash
# 运行所有测试
pytest tests/

# 运行特定测试文件
pytest tests/test_stock_api.py

# 查看测试覆盖率
pytest --cov=src tests/
```

### 文档贡献 | Documentation

文档同样重要！您可以帮助：

- 改进 README.md
- 完善 API 文档
- 添加使用示例
- 翻译文档
- 修复文档中的错误

### 前端贡献 | Frontend

前端使用原生 HTML/CSS/JavaScript：

- **HTML**: 语义化标签，良好的可访问性
- **CSS**: 
  - 使用 CSS Grid 和 Flexbox
  - 响应式设计
  - 遵循 BEM 命名约定
- **JavaScript**: 
  - ES6+ 语法
  - 模块化代码组织
  - 良好的错误处理

## 🎯 贡献重点领域

我们特别欢迎以下方面的贡献：

### 🚀 高优先级
- [ ] 增加单元测试覆盖率
- [ ] 性能优化和监控
- [ ] API 安全性增强
- [ ] 移动端用户体验优化

### 📊 功能增强
- [ ] 更多技术指标支持
- [ ] 数据可视化图表
- [ ] 用户个性化设置
- [ ] 多语言支持

### 🛠️ 基础设施
- [ ] Docker 部署配置
- [ ] CI/CD 流水线
- [ ] 监控告警系统
- [ ] 文档网站建设

## 🔍 Pull Request 审查

您的 PR 将会被项目维护者审查：

1. **自动检查**: 代码风格、测试通过
2. **人工审查**: 代码质量、功能正确性
3. **测试验证**: 功能测试和回归测试
4. **文档检查**: 相关文档是否更新

请耐心等待审查，我们会尽快回复。

## 🏆 贡献者认可

所有贡献者都会在项目中得到认可：

- README.md 中的贡献者列表
- 发布说明中的致谢
- 社区认可和徽章

## 📞 获得帮助

如果您在贡献过程中遇到问题：

- 查看 [Issues](https://github.com/ocean5tech/prism/issues) 寻找答案
- 创建新的 Issue 寻求帮助
- 在 PR 中 @mention 维护者

## 📋 贡献者协议

通过向本项目提交贡献，您同意：

- 您的贡献将按照项目的 MIT 许可证进行许可
- 您拥有提交内容的权利
- 您的贡献不违反任何第三方权利

---

再次感谢您的贡献！每一个贡献都让 Prism 变得更好。🚀