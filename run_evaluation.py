"""
Manual Evaluation Script for PrestaShop Tasks
User performs tasks manually while the evaluator validates results.
"""

import json
import asyncio
from playwright.async_api import async_playwright
from evaluate.evaluator import Evaluator


async def load_tasks(tasks_file):
    """Load tasks from JSON file"""
    with open(tasks_file, 'r', encoding='utf-8') as f:
        tasks = json.load(f)
    return tasks


async def replace_url_placeholders(tasks, config):
    """Replace URL placeholders with actual URLs"""
    prestashop_url = config.get('prestashop_url', 'http://localhost:8001')
    prestashop_admin_url = config.get('prestashop_admin_url', 'http://localhost:8001/admin-dev')
    
    for task in tasks:
        if 'start_url' in task:
            task['start_url'] = task['start_url'].replace('__PRESTASHOP__', prestashop_url)
            task['start_url'] = task['start_url'].replace('__PRESTASHOP_ADMIN__', prestashop_admin_url)
        
        # Replace in eval URLs
        if 'eval' in task:
            for eval_type, eval_config in task['eval'].items():
                if eval_type.startswith('eval_'):
                    continue
                if isinstance(eval_config, dict) and 'url' in eval_config:
                    eval_config['url'] = eval_config['url'].replace('__PRESTASHOP__', prestashop_url)
                    eval_config['url'] = eval_config['url'].replace('__PRESTASHOP_ADMIN__', prestashop_admin_url)
    
    return tasks


async def run_manual_evaluation(task, evaluator, page):
    """Run evaluation for a single task with manual execution"""
    print(f"\n{'='*80}")
    print(f"Task {task['task_id']}: {task['task_description'][:100]}...")
    print(f"{'='*80}")
    print(f"Start URL: {task['start_url']}")
    print(f"Max Steps: {task['steps']}")
    print(f"Requires Login: {task['require_login']}")
    
    # Navigate to start URL
    await page.goto(task['start_url'], wait_until='domcontentloaded', timeout=30000)
    
    # Pause for manual execution
    print(f"\n⏸️  PAUSED - Please perform the task manually in the browser")
    print(f"Task: {task['task_description']}")
    input("\n✅ Press Enter when you have completed the task...")
    
    # For string_match tasks, get agent result
    agent_result = None
    if 'eval' in task and 'string_match' in task['eval'].get('eval_type', []):
        agent_result = input("\n📝 Enter the result you found (for string_match evaluation): ")
    
    # Run evaluation
    try:
        result = await evaluator.evaluate_with_playwright(
            task_id=task['task_id'],
            agent_result=agent_result,
            page=page
        )
        
        if result:
            print(f"\n✅ Task {task['task_id']}: PASSED")
        else:
            print(f"\n❌ Task {task['task_id']}: FAILED")
        
        return result
    except Exception as e:
        print(f"\n❌ Task {task['task_id']}: ERROR - {str(e)}")
        return False


async def main():
    """Main function to run manual evaluation"""
    # Configuration
    config = {
        'prestashop_url': 'http://localhost:8001',
        'prestashop_admin_url': 'http://localhost:8001/admin-dev',
        'tasks_file': 'dataset/tasks.json'
    }
    
    # Load and prepare tasks
    print("Loading tasks...")
    tasks = await load_tasks(config['tasks_file'])
    tasks = await replace_url_placeholders(tasks, config)
    print(f"Loaded {len(tasks)} tasks")
    
    # Initialize evaluator
    evaluator = Evaluator(tasks)
    
    # Start browser
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Ask which tasks to run
        print(f"\nAvailable tasks: 1-{len(tasks)}")
        choice = input("Enter task IDs to run (e.g., '1,2,3' or 'all' or '1-5'): ").strip().lower()
        
        task_ids = []
        if choice == 'all':
            task_ids = [str(i+1) for i in range(len(tasks))]
        elif '-' in choice:
            start, end = choice.split('-')
            task_ids = [str(i) for i in range(int(start), int(end)+1)]
        else:
            task_ids = [tid.strip() for tid in choice.split(',')]
        
        # Run selected tasks
        results = {}
        for task_id in task_ids:
            task = next((t for t in tasks if t['task_id'] == task_id), None)
            if task:
                result = await run_manual_evaluation(task, evaluator, page)
                results[task_id] = result
            else:
                print(f"\n⚠️  Task {task_id} not found")
        
        # Summary
        print(f"\n{'='*80}")
        print("EVALUATION SUMMARY")
        print(f"{'='*80}")
        passed = sum(1 for r in results.values() if r)
        failed = len(results) - passed
        print(f"Total: {len(results)} | Passed: {passed} | Failed: {failed}")
        print(f"Pass Rate: {passed/len(results)*100:.1f}%")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
