"# Bonus Assignment: AI Agent Evaluation on PrestaShop

This project implements WebAppEval framework for testing AI agents on PrestaShop e-commerce platform with 25 comprehensive tasks covering both storefront and admin panel operations.

## 📋 Project Structure

```
Bonus_Assignment_AI_agent/
├── dataset/
│   ├── tasks.json              # 25 PrestaShop tasks in WebAppEval format
│   └── tasksexample.json       # Original Magento tasks reference
├── environments/
│   ├── env_config.json         # Environment configuration
│   └── prestashop/
│       ├── docker-compose.yml  # Docker setup for PrestaShop
│       └── env                 # Environment variables
├── evaluate/
│   ├── evaluator.py           # Main evaluator class
│   ├── matchers.py            # Matching functions (string, url, dom)
│   └── handlers.py            # Evaluation handlers
├── result/
│   ├── test_results_*.json    # Test execution results
│   └── test_log_*.txt         # Detailed test logs
├── run_evaluation.py          # Manual evaluation script
├── run_agent_evaluation.py    # Agent evaluation script
├── EVALUATION_GUIDE.md        # Comprehensive evaluation guide
├── REPORT.md                  # Final evaluation report with results
└── README.md                  # This file
```

## 🚀 Quick Start

### 1. Prerequisites
- Docker and Docker Compose
- Python 3.8+
- Required Python packages:
  ```bash
  pip install playwright asyncio google-generativeai python-dotenv
  playwright install chromium
  ```

### 2. Start PrestaShop Environment
```bash
cd environments/prestashop
docker-compose up -d
```

Wait for PrestaShop to initialize (2-3 minutes), then access:
- **Storefront:** http://localhost:8080
- **Admin Panel:** http://localhost:8080/admin
- **Admin Credentials:** 
  - Email: `demo@prestashop.com`
  - Password: `prestashop_demo`

### 3. Run Evaluation

#### Option A: Manual Testing (Human performs tasks)
```bash
python run_evaluation.py
```
Follow prompts to manually perform each task while the evaluator validates results.

#### Option B: Agent Testing (AI agent performs tasks)
```bash
python run_agent_evaluation.py
```
The agent will attempt to complete all tasks automatically with evaluation results.

## 📊 Test Results

**Latest Test Run:** January 9, 2026

| Metric | Value |
|--------|-------|
| Total Tasks | 25 |
| Passed | 18 (72%) |
| Failed | 7 (28%) |
| Avg Steps Used | 10.6 |

See [REPORT.md](REPORT.md) for detailed analysis.

## 📝 Task Categories

### Storefront Tasks (11 tasks)
- Product navigation and search
- Cart and wishlist operations
- Checkout and order placement
- Newsletter subscription
- Product reviews
- Customer account management

### Admin Tasks (14 tasks)
- Product management (create, edit, disable)
- Order management (view, status change, refunds)
- Customer management
- Cart rules and discounts
- Stock management
- CMS page editing

## 🔧 Configuration

### Environment Variables (environments/prestashop/env)
```env
PS_DOMAIN=localhost:8080
PS_LANGUAGE=en
PS_INSTALL_AUTO=1
DB_SERVER=mysql
DB_NAME=prestashop
DB_USER=prestashop
DB_PASSWD=prestashop
```

### URL Placeholders in tasks.json
- `__PRESTASHOP__` → http://localhost:8080
- `__PRESTASHOP_ADMIN__` → http://localhost:8080/admin

## 📖 Task Format

Each task in `dataset/tasks.json` follows WebAppEval structure:

```json
{
  "task_id": "1",
  "task_description": "Detailed step-by-step instructions...",
  "task_type": "lookup|operation|form",
  "start_url": "__PRESTASHOP__",
  "steps": "10",
  "require_login": false,
  "eval": {
    "eval_type": ["string_match", "url_match", "dom_match"],
    "string_match": {
      "match_type": "exact|contains",
      "match_value": "Expected result"
    },
    "url_match": {
      "match_type": "contains",
      "match_value": "url-pattern"
    },
    "dom_match": {
      "url": "last|__PRESTASHOP__/specific-page",
      "dom_extractor": "JavaScript to extract DOM data",
      "match_type": "exact|contains",
      "match_value": "Expected value"
    }
  }
}
```

## 🧪 Evaluation Methods

### 1. String Match
Validates agent's text output against expected value.

### 2. URL Match
Verifies navigation to correct page by checking URL patterns.

### 3. DOM Match
Executes JavaScript in browser to extract and validate page elements.

## 📚 Documentation

- [REPORT.md](REPORT.md) - Complete evaluation report with 25 tasks results
- [EVALUATION_GUIDE.md](EVALUATION_GUIDE.md) - Detailed guide for using the evaluator
- [dataset/tasks.json](dataset/tasks.json) - All 25 PrestaShop tasks

## 🐛 Troubleshooting

### PrestaShop not loading
```bash
docker-compose down -v
docker-compose up -d
```

### Database connection issues
Check `environments/prestashop/env` file and verify MySQL container is running:
```bash
docker ps
```

### Evaluation timeout
Increase `steps` value in tasks.json for complex operations.

### Admin panel 404
PrestaShop admin URL changes on each install. Check actual admin URL:
```bash
docker-compose logs prestashop | grep "Admin"
```

## 🤝 Contributing

This is a course assignment, but improvements are welcome:
1. Additional task scenarios
2. Enhanced evaluation matchers
3. Better error handling
4. Support for more PrestaShop versions

## 📄 License

This project is for educational purposes as part of the course assignment.

## 👤 Author

[Your Name]  
[Your Student ID]  
[Your Email]

## 🙏 Acknowledgments

- WebAppEval framework for the evaluation methodology
- PrestaShop team for the demo platform
- Course instructors for guidance

---

**Last Updated:** January 9, 2026
" 
