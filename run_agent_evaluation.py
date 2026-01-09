"""
Agent-based Evaluation Script for PrestaShop Tasks
AI Agent performs tasks automatically while the evaluator validates results.
"""

import json
import asyncio
from datetime import datetime
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


async def simulate_agent_actions(task, page):
    """
    Simulate AI agent performing the task.
    In production, this would be replaced with actual agent code.
    For now, this is a placeholder that waits for manual completion.
    """
    print(f"\n🤖 Agent simulating task {task['task_id']}...")
    print(f"   Description: {task['task_description'][:100]}...")
    
    # Navigate to start URL
    await page.goto(task['start_url'], wait_until='domcontentloaded', timeout=30000)
    
    # In a real implementation, the agent would:
    # 1. Analyze the task description
    # 2. Execute steps using vision + browser automation
    # 3. Return the result
    
    # For now, wait for manual completion as placeholder
    print(f"   ⏸️  Waiting for task completion (manual mode)...")
    await asyncio.sleep(2)  # Simulate some work
    
    # Return None for string_match tasks (agent should extract result)
    return None


async def run_agent_evaluation(task, evaluator, page, max_retries=1):
    """Run evaluation for a single task with agent execution"""
    print(f"\n{'='*80}")
    print(f"Task {task['task_id']}: {task['task_description'][:80]}...")
    print(f"{'='*80}")
    
    for attempt in range(max_retries):
        try:
            # Agent performs the task
            agent_result = await simulate_agent_actions(task, page)
            
            # Evaluate the result
            result = await evaluator.evaluate_with_playwright(
                task_id=task['task_id'],
                agent_result=agent_result,
                page=page
            )
            
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"\n{status} - Task {task['task_id']}")
            
            return {
                'task_id': task['task_id'],
                'description': task['task_description'],
                'success': result,
                'error': None,
                'steps_used': int(task.get('steps', 10)),
                'max_steps': int(task.get('steps', 10)),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"\n❌ ERROR - Task {task['task_id']}: {error_msg}")
            
            if attempt < max_retries - 1:
                print(f"   Retrying... (Attempt {attempt + 2}/{max_retries})")
                await asyncio.sleep(2)
            else:
                return {
                    'task_id': task['task_id'],
                    'description': task['task_description'],
                    'success': False,
                    'error': error_msg,
                    'steps_used': int(task.get('steps', 10)),
                    'max_steps': int(task.get('steps', 10)),
                    'timestamp': datetime.now().isoformat()
                }


async def main():
    """Main function to run agent-based evaluation"""
    # Configuration
    config = {
        'prestashop_url': 'http://localhost:8001',
        'prestashop_admin_url': 'http://localhost:8001/admin-dev',
        'tasks_file': 'dataset/tasks.json',
        'output_dir': 'result'
    }
    
    # Load and prepare tasks
    print("🚀 Starting Agent Evaluation on PrestaShop")
    print("="*80)
    print("Loading tasks...")
    tasks = await load_tasks(config['tasks_file'])
    tasks = await replace_url_placeholders(tasks, config)
    print(f"✅ Loaded {len(tasks)} tasks\n")
    
    # Initialize evaluator
    evaluator = Evaluator(tasks)
    
    # Ask which tasks to run
    print(f"Available tasks: 1-{len(tasks)}")
    choice = input("Enter task IDs to run (e.g., '1,2,3' or 'all' or '1-5'): ").strip().lower()
    
    task_ids = []
    if choice == 'all':
        task_ids = [str(i+1) for i in range(len(tasks))]
    elif '-' in choice:
        start, end = choice.split('-')
        task_ids = [str(i) for i in range(int(start), int(end)+1)]
    else:
        task_ids = [tid.strip() for tid in choice.split(',')]
    
    # Filter tasks
    tasks_to_run = [t for t in tasks if t['task_id'] in task_ids]
    
    # Start browser
    print(f"\n🌐 Launching browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Run tasks
        start_time = datetime.now()
        results = []
        
        for i, task in enumerate(tasks_to_run, 1):
            print(f"\n[{i}/{len(tasks_to_run)}] Running task {task['task_id']}...")
            result = await run_agent_evaluation(task, evaluator, page)
            results.append(result)
            
            # Small delay between tasks
            if i < len(tasks_to_run):
                await asyncio.sleep(1)
        
        await browser.close()
        
        # Calculate summary
        passed = sum(1 for r in results if r['success'])
        failed = len(results) - passed
        pass_rate = f"{passed/len(results)*100:.1f}%" if results else "0%"
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{config['output_dir']}/agent_eval_{timestamp}.json"
        
        output_data = {
            'start_time': start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'results': results,
            'summary': {
                'total_tasks': len(results),
                'passed': passed,
                'failed': failed,
                'pass_rate': pass_rate
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        # Print summary
        print(f"\n{'='*80}")
        print("📊 EVALUATION SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tasks:  {len(results)}")
        print(f"✅ Passed:    {passed}")
        print(f"❌ Failed:    {failed}")
        print(f"📈 Pass Rate: {pass_rate}")
        print(f"\n💾 Results saved to: {output_file}")
        print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
