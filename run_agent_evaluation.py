"""
Agent-S Based Evaluation Script for PrestaShop Tasks
Uses Agent-S framework with WebAppEval evaluator for automated testing.
Requires Agent-S to be installed in the project directory.
"""

import argparse
import asyncio
import io
import json
import logging
import os
import platform
import sys
from datetime import datetime
from pathlib import Path

try:
    import pyautogui
    from PIL import Image
    PYAUTOGUI_AVAILABLE = True
except:
    PYAUTOGUI_AVAILABLE = False

from playwright.async_api import async_playwright

# Add Agent-S to path if available
agent_s_path = Path(__file__).parent / "Agent-S"
if agent_s_path.exists():
    sys.path.insert(0, str(agent_s_path))
    try:
        from gui_agents.s3.agents.grounding import OSWorldACI
        from gui_agents.s3.agents.agent_s import AgentS3
        AGENT_S_AVAILABLE = True
    except:
        AGENT_S_AVAILABLE = False
else:
    AGENT_S_AVAILABLE = False

# Import WebAppEval evaluator
from evaluate.evaluator import Evaluator

# Setup logging
log_filename = f"result/agent_eval_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
os.makedirs("result", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_filename, mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


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
        
        # Replace in eval block URLs
        if 'eval' in task:
            for eval_type, eval_config in task['eval'].items():
                if eval_type.startswith('eval_'):
                    continue
                if isinstance(eval_config, dict) and 'url' in eval_config:
                    eval_config['url'] = eval_config['url'].replace('__PRESTASHOP__', prestashop_url)
                    eval_config['url'] = eval_config['url'].replace('__PRESTASHOP_ADMIN__', prestashop_admin_url)
    
    return tasks


def setup_agent_s(engine_params, grounding_params):
    """Setup Agent-S with the given parameters"""
    if not AGENT_S_AVAILABLE:
        logger.warning("Agent-S not available")
        return None
    
    if not PYAUTOGUI_AVAILABLE:
        logger.warning("PyAutoGUI not available")
        return None
    
    screen_width, screen_height = pyautogui.size()
    logger.info(f"[AgentS] Screen size: {screen_width}x{screen_height}")
    
    current_platform = platform.system().lower()
    
    grounding_agent = OSWorldACI(
        env=None,
        platform=current_platform,
        engine_params_for_generation=engine_params,
        engine_params_for_grounding=grounding_params,
        width=screen_width,
        height=screen_height
    )
    
    agent = AgentS3(
        engine_params,
        grounding_agent,
        platform=current_platform,
        max_trajectory_length=8,
        enable_reflection=True
    )
    
    return agent


async def run_task_with_agent_s(task, agent, evaluator, page):
    """Run task using Agent-S and evaluate with WebAppEval evaluator"""
    task_id = task['task_id']
    description = task['task_description']
    
    logger.info(f"\n{'='*80}")
    logger.info(f"Task {task_id}: {description[:80]}...")
    logger.info(f"{'='*80}")
    
    result = {
        'task_id': task_id,
        'description': description,
        'success': False,
        'error': None,
        'steps_used': 0,
        'max_steps': 0
    }
    
    try:
        # Navigate to start URL
        await page.goto(task['start_url'], wait_until='domcontentloaded', timeout=60000)
        logger.info(f"[OK] Loaded {task['start_url']}")
        
        # Agent execution loop
        steps_value = task.get('steps', 10)
        max_steps = len(steps_value) if isinstance(steps_value, list) else int(steps_value)
        result['max_steps'] = max_steps
        
        for step in range(max_steps):
            result['steps_used'] = step + 1
            logger.info(f"Step {step + 1}/{max_steps}")
            
            # Take screenshot
            screenshot_bytes = await page.screenshot()
            obs = {"screenshot": screenshot_bytes}
            
            # Get action from agent
            info, code = agent.predict(instruction=description, observation=obs)
            
            if "done" in code[0].lower():
                logger.info("Agent completed task")
                break
            
            if "fail" in code[0].lower():
                logger.info("Agent failed task")
                break
            
            if "next" in code[0].lower():
                continue
            
            # Execute action
            try:
                logger.info(f"Executing: {code[0][:100]}...")
                exec(code[0])
            except Exception as e:
                logger.error(f"Error executing action: {e}")
            
            await asyncio.sleep(1)
            try:
                await page.wait_for_load_state('networkidle', timeout=5000)
            except:
                pass
        
        # Evaluate using WebAppEval evaluator
        result['success'] = await evaluator.evaluate_with_playwright(
            task_id=task_id,
            agent_result=None,  # Agent-S performs actions, doesn't return text
            browser=page
        )
        
        status = "[PASSED]" if result['success'] else "[FAILED]"
        logger.info(f"\n{status} - Task {task_id}")
        
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"[ERROR] Task {task_id}: {e}")
    
    return result


async def main():
    """Main execution function"""
    
    # Load configuration from env_config.json
    # Try root directory first, then environments folder
    env_config_path = 'env_config.json'
    if not os.path.exists(env_config_path):
        env_config_path = 'environments/env_config.json'
    
    try:
        with open(env_config_path, 'r', encoding='utf-8') as f:
            env_config = json.load(f)
        
        # Support both __PS__ and __PRESTASHOP__ formats
        ps_key = '__PS__' if '__PS__' in env_config else '__PRESTASHOP__'
        admin_key = '__PS_ADMIN__' if '__PS_ADMIN__' in env_config else '__PRESTASHOP_ADMIN__'
        
        config = {
            'prestashop_url': env_config[ps_key]['url'],
            'prestashop_admin_url': env_config[admin_key]['url'],
            'username': env_config[ps_key]['username'],
            'password': env_config[ps_key]['password'],
            'admin_username': env_config[admin_key]['username'],
            'admin_password': env_config[admin_key]['password']
        }
        logger.info(f"Loaded config from {env_config_path}")
        logger.info(f"PrestaShop URL: {config['prestashop_url']}")
    except Exception as e:
        logger.warning(f"Could not load env_config.json: {e}")
        logger.warning("Using default configuration")
        config = {
            'prestashop_url': 'http://localhost:8001',
            'prestashop_admin_url': 'http://localhost:8001/admin-dev'
        }
    
    print("="*80)
    print("PRESTASHOP AI AGENT EVALUATION")
    print("="*80)
    
    # Check if Agent-S is available
    if not AGENT_S_AVAILABLE:
        logger.error("Agent-S framework not found!")
        logger.error("Please clone Agent-S repository to project directory:")
        logger.error("  git clone https://github.com/simular-ai/Agent-S.git")
        print("\n[ERROR] Agent-S is required for automated testing.")
        print("Please install Agent-S and try again.")
        return
    
    print(f"Agent-S: Available")
    print("Mode: Automated Testing")
    print("="*80)
    
    # Load tasks
    tasks = await load_tasks('dataset/tasks.json')
    tasks = await replace_url_placeholders(tasks, config)
    
    # Optional: Filter specific tasks for testing
    # tasks = [t for t in tasks if t['task_id'] in ['1', '2', '3']]
    
    logger.info(f"[OK] Loaded {len(tasks)} tasks")
    
    # Initialize evaluator
    evaluator = Evaluator(tasks)
    
    # Setup Agent-S
    engine_params = {
        "engine_type": "openai",
        "model": "gpt-4o",
        "api_key": os.getenv("OPENAI_API_KEY", "")
    }
    grounding_params = {
        "engine_type": "huggingface",
        "model": "ui-tars-1.5-7b",
        "base_url": os.getenv("GROUNDING_MODEL_URL", "http://localhost:8000"),
        "grounding_width": 1920,
        "grounding_height": 1080
    }
    
    agent = setup_agent_s(engine_params, grounding_params)
    if not agent:
        logger.error("Failed to setup Agent-S")
        return
    
    # Run evaluation
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            for task in tasks:
                # Reset agent state before each task
                agent.reset()
                result = await run_task_with_agent_s(task, agent, evaluator, page)
                results.append(result)
                
                # Save incremental result
                save_results(results)
        
        finally:
            await browser.close()
    
    # Print summary
    print_summary(results)


def save_results(results):
    """Save results to JSON file"""
    output_file = f"result/agent_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    data = {
        'start_time': datetime.now().isoformat(),
        'end_time': datetime.now().isoformat(),
        'results': results,
        'summary': {
            'total_tasks': total,
            'passed': passed,
            'failed': total - passed,
            'pass_rate': f"{(passed/total*100):.1f}%" if total > 0 else "0%"
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Results saved to: {output_file}")


def print_summary(results):
    """Print summary of results"""
    print("\n" + "="*80)
    print("EVALUATION SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    print(f"Total Tasks:  {total}")
    print(f"Passed:    {passed}")
    print(f"Failed:    {total - passed}")
    print(f"Pass Rate: {(passed/total*100):.1f}%" if total > 0 else "0%")
    print("="*80)


if __name__ == '__main__':
    asyncio.run(main())
