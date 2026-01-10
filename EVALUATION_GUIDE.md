# How to Run Evaluation

This guide explains how to run the WebAppEval evaluator on PrestaShop tasks.

## Prerequisites

1. **PrestaShop Running:**
   ```bash
   cd environments/prestashop
   docker-compose up -d
   ```
   Wait until PrestaShop is accessible at http://localhost:8001

2. **Python Dependencies:**
   ```bash
   pip install playwright asyncio python-dotenv google-generativeai
   playwright install chromium
   ```

## Method 1: Manual Evaluation

**Use Case:** You perform tasks manually, evaluator validates results.

```bash
python run_evaluation.py
```

**Process:**
1. Script opens browser
2. Prompts you to select which tasks to run
3. For each task:
   - Shows task description
   - Navigates to start URL
   - Pauses for you to complete the task manually
   - Press Enter when done
   - Evaluator checks if task succeeded
4. Shows summary at the end

**Example:**
```
$ python run_evaluation.py
Loading tasks...
Loaded 25 tasks

Available tasks: 1-25
Enter task IDs to run: 1,2,3

Task 1: Navigate to 'Clothes > Women' category...
⏸️  PAUSED - Please perform the task manually
✅ Press Enter when completed...
✅ Task 1: PASSED
```

## Method 2: Agent Evaluation

**Use Case:** AI agent performs tasks automatically.

```bash
python run_agent_evaluation.py
```

**Process:**
1. Script opens browser
2. Prompts you to select which tasks to run
3. For each task:
   - Agent simulates performing the task
   - Evaluator validates the result
   - Saves result to JSON file
4. Generates report in `result/` folder

**Example:**
```
$ python run_agent_evaluation.py
🚀 Starting Agent Evaluation on PrestaShop
Loaded 25 tasks

Available tasks: 1-25
Enter task IDs to run: all

[1/25] Running task 1...
🤖 Agent simulating task 1...
✅ PASSED - Task 1

📊 EVALUATION SUMMARY
Total Tasks:  25
✅ Passed:    18
❌ Failed:    7
📈 Pass Rate: 72.0%

💾 Results saved to: result/agent_eval_20260109_223045.json
```

## Task Selection Options

When prompted "Enter task IDs to run":

- **Single task:** `1`
- **Multiple tasks:** `1,2,3,5,8`
- **Range:** `1-10` (runs tasks 1 through 10)
- **All tasks:** `all`

## Understanding Results

### Console Output

Each task shows:
- ✅ PASSED - Task completed successfully
- ❌ FAILED - Task did not meet evaluation criteria
- ❌ ERROR - Exception occurred during execution

### JSON Output (Agent mode)

Results saved to `result/agent_eval_TIMESTAMP.json`:

```json
{
  "start_time": "2026-01-09T22:30:00",
  "results": [
    {
      "task_id": "1",
      "description": "Navigate to...",
      "success": true,
      "error": null,
      "steps_used": 3,
      "max_steps": 10,
      "timestamp": "2026-01-09T22:30:15"
    }
  ],
  "summary": {
    "total_tasks": 25,
    "passed": 18,
    "failed": 7,
    "pass_rate": "72.0%"
  }
}
```

## Evaluation Methods

The evaluator uses three strategies defined in each task's `eval` block:

### 1. string_match
Validates text output from the agent.
```json
{
  "eval_type": ["string_match"],
  "string_match": {
    "match_type": "exact",
    "match_value": "Hummingbird printed t-shirt"
  }
}
```

### 2. url_match
Verifies browser navigated to correct page.
```json
{
  "eval_type": ["url_match"],
  "url_match": {
    "match_type": "contains",
    "match_value": "order-confirmation"
  }
}
```

### 3. dom_match
Executes JavaScript to extract and validate DOM elements.
```json
{
  "eval_type": ["dom_match"],
  "dom_match": {
    "url": "last",
    "dom_extractor": "document.querySelector('.product-price')?.innerText",
    "match_type": "contains",
    "match_value": "$25.00"
  }
}
```

## Troubleshooting

### Browser doesn't open
```bash
playwright install chromium
```

### Connection refused to localhost:8001
Check PrestaShop is running:
```bash
cd environments/prestashop
docker-compose ps
```

### Evaluation fails immediately
Check the task's `eval` block in `dataset/tasks.json` - ensure URLs and selectors are correct.

### Import errors
Install dependencies:
```bash
pip install -r requirements.txt
```

## Tips for Giáo Viên

When evaluating this project:

1. **Test Docker Setup:**
   ```bash
   cd environments/prestashop
   docker-compose up -d
   # Wait 2-3 minutes
   # Visit http://localhost:8001
   ```

2. **Run a Quick Test:**
   ```bash
   python run_evaluation.py
   # Enter: 1,2,3
   # Manually complete 3 simple tasks
   ```

3. **Check Results:**
   - See if evaluation logic works correctly
   - Review `result/` folder for saved outputs

4. **Review Code:**
   - `evaluate/evaluator.py` - Core evaluation class
   - `evaluate/handlers.py` - Handler functions
   - `evaluate/matchers.py` - Matching logic
