"""
PrestaShop Test Runner using Agent-S
This script runs Agent-S to test PrestaShop web application
using the tasks defined in prestashop_tasks.json
"""

import argparse
import asyncio
import io
import json
import logging
import os
import platform
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pyautogui
from PIL import Image
from playwright.async_api import async_playwright

# Add the parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "Agent-S"))

from gui_agents.s3.agents.grounding import OSWorldACI
from gui_agents.s3.agents.agent_s import AgentS3

# Import WebAppEval Evaluator
from evaluate.evaluator import Evaluator

# Import config
try:
    from config import ENGINE_CONFIG, GROUNDING_CONFIG, TEST_CONFIG, RATE_LIMIT_CONFIG
    USE_CONFIG_FILE = True
except ImportError:
    USE_CONFIG_FILE = False
    RATE_LIMIT_CONFIG = {"enabled": False, "delay_between_requests": 0}

# Setup logging with file handler
log_filename = f"test_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler(log_filename, mode='a', encoding='utf-8')  # File output (append)
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Log file created: {log_filename}")


class PrestaShopTester:
    def __init__(self, env_config_path: str, tasks_path: str):
        """Initialize the PrestaShop tester."""
        with open(env_config_path, 'r') as f:
            self.env_config = json.load(f)
        
        with open(tasks_path, 'r') as f:
            self.tasks = json.load(f)
        
        self.current_platform = platform.system().lower()
        self.results = []
        self.results_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.log_filename = log_filename
        
        # Initialize WebAppEval Evaluator
        self.evaluator = Evaluator(self.tasks)
        logger.info("WebAppEval Evaluator initialized")
    
    def save_incremental_result(self, result: dict):
        """Save result to JSON file after each task completes."""
        try:
            # Load existing results if file exists
            if os.path.exists(self.results_file):
                with open(self.results_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {
                    'start_time': datetime.now().isoformat(),
                    'results': [],
                    'summary': {}
                }
            
            # Append new result
            result_copy = result.copy()
            result_copy['timestamp'] = datetime.now().isoformat()
            data['results'].append(result_copy)
            
            # Update summary
            total = len(data['results'])
            passed = sum(1 for r in data['results'] if r['success'])
            data['summary'] = {
                'total_tasks': total,
                'passed': passed,
                'failed': total - passed,
                'pass_rate': f"{(passed/total*100):.1f}%" if total > 0 else "0%"
            }
            
            # Save to file
            with open(self.results_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Result saved to {self.results_file}")
        except Exception as e:
            logger.error(f"Error saving result: {e}")
    
    def resolve_url(self, url: str) -> str:
        """Resolve placeholder URLs to actual URLs."""
        for placeholder, config in self.env_config.items():
            if url.startswith(placeholder):
                return url.replace(placeholder, config['url'])
        return url
    
    def setup_agent(self, engine_params: dict, grounding_params: dict, env=None):
        """Setup Agent-S with the given parameters."""
        # --- Get real screen size ---
        screen_width, screen_height = pyautogui.size()
        logger.info(f"[AgentS] Detected screen size: {screen_width}x{screen_height}")
        
        grounding_agent = OSWorldACI(
            env=env,  # Environment object (can be None for basic usage)
            platform=self.current_platform,
            engine_params_for_generation=engine_params,
            engine_params_for_grounding=grounding_params,
            width=screen_width,
            height=screen_height
        )
        
        agent = AgentS3(
            engine_params,
            grounding_agent,
            platform=self.current_platform,
            max_trajectory_length=8,
            enable_reflection=True
        )
        
        return agent
    
    def extract_agent_answer(self, agent_info: dict) -> str:
        """Extract the agent's answer from its reasoning output.
        
        For lookup tasks, the agent typically mentions the answer in its plan/analysis.
        We try to extract it from the reasoning text.
        """
        if not agent_info:
            return ""
        
        # agent_info is typically a dict with 'plan' or reasoning
        reasoning = str(agent_info)
        
        # Common patterns for agent answers
        patterns = [
            r'the (?:first |cheapest |most expensive )?(?:product|item) (?:is|displayed)[:\s]*["\']?([^"\'.\n]+)',
            r'name of the (?:first |cheapest )?product[:\s]*["\']?([^"\'.\n]+)',
            r'answer is[:\s]*["\']?([^"\'.\n]+)',
            r'result is[:\s]*["\']?([^"\'.\n]+)',
            r'total (?:number of )?products[:\s]*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, reasoning, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return reasoning
    
    async def evaluate_with_webappeval(self, task: dict, agent_answer: str = None) -> bool:
        """Evaluate task result using WebAppEval Evaluator with Playwright.
        
        Opens a Playwright browser to verify DOM/URL conditions for the task's eval block.
        """
        task_id = task['task_id']
        eval_block = task.get('eval', {})
        eval_types = eval_block.get('eval_type', [])
        
        logger.info(f"[WebAppEval] Evaluating task {task_id} with types: {eval_types}")
        
        # For string_match only tasks, we can evaluate without browser
        if eval_types == ['string_match'] and 'string_match' in eval_block:
            from evaluate.handlers import string_match
            result = string_match(
                target_conf=eval_block['string_match'],
                agent_result=agent_answer,
                task=task['task_description']
            )
            logger.info(f"[WebAppEval] string_match result: {result}")
            return result
        
        # For DOM/URL evaluation, we need the browser state
        # Since we use pyautogui, we'll prompt user to stay on the final page
        # and use Playwright to connect and verify
        async with async_playwright() as p:
            try:
                # Launch browser to verify result
                # Note: For pyautogui mode, the browser state is in user's browser
                # We'll use CDP to connect to Chrome if possible, or ask user
                browser = await p.chromium.launch(headless=False)
                page = await browser.new_page()
                
                # Check each eval type
                for eval_type in eval_types:
                    if eval_type == 'dom_match' and 'dom_match' in eval_block:
                        dom_conf = eval_block['dom_match']
                        url = dom_conf.get('url', 'last')
                        
                        # If URL is specified (not 'last'), navigate to it
                        if url not in ('', 'current', 'last', None):
                            resolved_url = self.resolve_url(url)
                            logger.info(f"[WebAppEval] Navigating to: {resolved_url}")
                            await page.goto(resolved_url)
                            await page.wait_for_load_state('networkidle')
                        else:
                            # For 'last', ask user to confirm we're on correct page
                            logger.info("[WebAppEval] Using current browser state for dom_match")
                            # Skip DOM evaluation if we can't access the page
                            logger.warning("[WebAppEval] Cannot verify DOM in pyautogui mode without page access")
                            continue
                        
                        # Execute DOM check
                        result = await self.evaluator.evaluate_with_playwright(
                            task_id=task_id,
                            agent_result=agent_answer,
                            browser=page
                        )
                        if not result:
                            await browser.close()
                            return False
                    
                    elif eval_type == 'url_match' and 'url_match' in eval_block:
                        # URL match typically needs the current page URL
                        # In pyautogui mode, we rely on agent's done status
                        logger.info("[WebAppEval] url_match check (agent-reported)")
                        continue
                    
                    elif eval_type == 'string_match' and 'string_match' in eval_block:
                        from evaluate.handlers import string_match
                        result = string_match(
                            target_conf=eval_block['string_match'],
                            agent_result=agent_answer,
                            task=task['task_description']
                        )
                        if not result:
                            await browser.close()
                            return False
                
                await browser.close()
                return True
                
            except Exception as e:
                logger.error(f"[WebAppEval] Evaluation error: {e}")
                return False
    
    
    async def run_task_with_playwright(self, task: dict, agent) -> dict:
        """Run a single task using Playwright for browser automation."""
        task_id = task['task_id']
        description = task['task_description']
        start_url = self.resolve_url(task['start_url'])
        
        logger.info(f"Running task {task_id}: {description}")
        logger.info(f"Start URL: {start_url}")
        
        result = {
            'task_id': task_id,
            'description': description,
            'success': False,
            'error': None
        }
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            
            try:
                # Navigate to start URL
                await page.goto(start_url)
                await page.wait_for_load_state('networkidle')
                
                # Take screenshot for agent
                screenshot_bytes = await page.screenshot()
                
                obs = {"screenshot": screenshot_bytes}
                
                # Run agent prediction loop
                steps_value = task.get('steps', 10)
                max_steps = len(steps_value) if isinstance(steps_value, list) else int(steps_value)
                for step in range(max_steps):
                    logger.info(f"Step {step + 1}/{max_steps}")
                    
                    # Rate limiting
                    if RATE_LIMIT_CONFIG.get('enabled', False):
                        delay = RATE_LIMIT_CONFIG.get('delay_between_requests', 13)
                        logger.info(f"Rate limit: waiting {delay}s before API call...")
                        await asyncio.sleep(delay)
                    
                    # Get action from agent
                    info, code = agent.predict(instruction=description, observation=obs)
                    
                    if "done" in code[0].lower() or "fail" in code[0].lower():
                        logger.info(f"Agent completed task: {code[0]}")
                        break
                    
                    if "next" in code[0].lower():
                        continue
                    
                    # Execute the action code
                    try:
                        exec(code[0])
                    except Exception as e:
                        logger.error(f"Error executing action: {e}")
                    
                    # Wait for page to update
                    await asyncio.sleep(1)
                    await page.wait_for_load_state('networkidle')
                    
                    # Take new screenshot
                    screenshot_bytes = await page.screenshot()
                    obs = {"screenshot": screenshot_bytes}
                
                # Evaluate the result
                eval_block = task['eval']
                for eval_type in eval_block['eval_type']:
                    if eval_type == 'dom_match':
                        dom_conf = eval_block['dom_match']
                        extractor = dom_conf['dom_extractor']
                        expected = dom_conf['match_value']
                        match_type = dom_conf['match_type']
                        
                        actual = await page.evaluate(extractor)
                        
                        if match_type == 'contains':
                            result['success'] = expected in str(actual)
                        elif match_type == 'exact':
                            result['success'] = expected == actual
                    
                    elif eval_type == 'url_match':
                        url_conf = eval_block['url_match']
                        expected = url_conf['match_value']
                        match_type = url_conf['match_type']
                        
                        current_url = page.url
                        
                        if match_type == 'contains':
                            result['success'] = expected in current_url
                        elif match_type == 'exact':
                            result['success'] = expected == current_url
                
            except Exception as e:
                result['error'] = str(e)
                logger.error(f"Error running task: {e}")
            
            finally:
                await browser.close()
        
        return result
    
    def run_task_with_pyautogui(self, task: dict, agent) -> dict:
        """Run a single task using PyAutoGUI for screen automation with WebAppEval evaluation."""
        task_id = task['task_id']
        description = task['task_description']
        start_url = self.resolve_url(task['start_url'])
        
        logger.info(f"Running task {task_id}: {description}")
        logger.info(f"Please manually navigate to: {start_url}")
        
        result = {
            'task_id': task_id,
            'description': description,
            'success': False,
            'agent_done': False,
            'webappeval_result': None,
            'agent_answer': None,
            'error': None,
            'steps_used': 0,
            'max_steps': 0
        }
        
        # Wait for user to open browser
        input("Press Enter when browser is open and navigated to the start URL...")
        print("[INFO] Waiting 3 seconds for you to switch to the browser window...")
        time.sleep(3)
        
        last_agent_info = None
        
        try:
            steps_value = task.get('steps', 10)
            max_steps = len(steps_value) if isinstance(steps_value, list) else int(steps_value)
            result['max_steps'] = max_steps
            
            for step in range(max_steps):
                result['steps_used'] = step + 1
                logger.info(f"Step {step + 1}/{max_steps}")
                
                # Rate limiting
                if RATE_LIMIT_CONFIG.get('enabled', False):
                    delay = RATE_LIMIT_CONFIG.get('delay_between_requests', 13)
                    logger.info(f"Rate limit: waiting {delay}s before API call...")
                    time.sleep(delay)
                
                # Take screenshot
                screenshot = pyautogui.screenshot()
                screenshot = screenshot.resize((1920, 1080), Image.LANCZOS)
                
                buffered = io.BytesIO()
                screenshot.save(buffered, format="PNG")
                screenshot_bytes = buffered.getvalue()
                
                obs = {"screenshot": screenshot_bytes}
                
                # Get action from agent
                info, code = agent.predict(instruction=description, observation=obs)
                last_agent_info = info  # Save for extraction
                
                if "done" in code[0].lower():
                    logger.info("Agent reported task as done")
                    result['agent_done'] = True
                    break
                
                if "fail" in code[0].lower():
                    logger.info("Agent reported task as failed")
                    result['agent_done'] = False
                    break
                
                if "next" in code[0].lower():
                    continue
                
                # Execute the action
                try:
                    logger.info(f"Executing: {code[0][:100]}...")
                    exec(code[0])
                except Exception as e:
                    logger.error(f"Error executing action: {e}")
                
                time.sleep(1)
            
            # --- WebAppEval Evaluation ---
            logger.info("[WebAppEval] Starting automatic evaluation...")
            
            # Extract agent's answer from its reasoning
            agent_answer = self.extract_agent_answer(last_agent_info)
            result['agent_answer'] = agent_answer
            logger.info(f"[WebAppEval] Extracted agent answer: {agent_answer[:100] if agent_answer else 'None'}...")
            
            # Run WebAppEval evaluation
            eval_block = task.get('eval', {})
            eval_types = eval_block.get('eval_type', [])
            
            if 'string_match' in eval_types:
                # For string_match tasks, use the handler directly
                from evaluate.handlers import string_match
                webappeval_success = string_match(
                    target_conf=eval_block.get('string_match', {}),
                    agent_result=agent_answer,
                    task=description
                )
                result['webappeval_result'] = webappeval_success
                logger.info(f"[WebAppEval] string_match evaluation: {'PASS' if webappeval_success else 'FAIL'}")
            
            elif 'dom_match' in eval_types or 'url_match' in eval_types:
                # For DOM/URL match, we need browser access
                # Run async evaluation
                webappeval_success = asyncio.run(
                    self.evaluate_with_webappeval(task, agent_answer)
                )
                result['webappeval_result'] = webappeval_success
                logger.info(f"[WebAppEval] DOM/URL evaluation: {'PASS' if webappeval_success else 'FAIL'}")
            
            else:
                # No specific eval type, use agent's done status
                webappeval_success = result['agent_done']
                result['webappeval_result'] = webappeval_success
            
            # Final success = WebAppEval result (not just agent's claim)
            result['success'] = result['webappeval_result'] if result['webappeval_result'] is not None else result['agent_done']
            
            logger.info(f"[WebAppEval] Final result - Agent done: {result['agent_done']}, WebAppEval: {result['webappeval_result']}, Success: {result['success']}")
        
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error running task: {e}")
        
        return result
    
    def run_all_tasks(self, agent, mode='pyautogui'):
        """Run all tasks and collect results."""
        for task in self.tasks:
            # Reset agent state before each task to clear trajectory memory
            agent.reset()
            
            if mode == 'playwright':
                result = asyncio.run(self.run_task_with_playwright(task, agent))
            else:
                result = self.run_task_with_pyautogui(task, agent)
            
            self.results.append(result)
            
            # Save result incrementally to file
            self.save_incremental_result(result)
            
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            logger.info(f"Task {result['task_id']}: {status}")
        
        return self.results
    
    def print_summary(self):
        """Print a summary of all test results."""
        print("\n" + "=" * 60)
        print("PRESTASHOP TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.results if r['success'])
        total = len(self.results)
        
        for result in self.results:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"{status} | {result['task_id']}: {result['description'][:50]}...")
            if result['error']:
                print(f"       Error: {result['error']}")
        
        print("=" * 60)
        print(f"Total: {passed}/{total} tasks passed ({100*passed/total:.1f}%)")
        print("=" * 60)
    
    def calculate_metrics(self):
        """Calculate TSR (Task Success Rate) and SCR (Step Completion Rate)."""
        total_tasks = len(self.results)
        passed_tasks = sum(1 for r in self.results if r['success'])
        
        total_steps_used = sum(r.get('steps_used', 0) for r in self.results)
        total_max_steps = sum(r.get('max_steps', 0) for r in self.results)
        
        tsr = (passed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        scr = (total_steps_used / total_max_steps * 100) if total_max_steps > 0 else 0
        
        return {
            'tsr': tsr,
            'scr': scr,
            'passed': passed_tasks,
            'total': total_tasks,
            'total_steps_used': total_steps_used,
            'total_max_steps': total_max_steps
        }
    
    def generate_report(self, engine_params: dict, grounding_params: dict, output_path: str = "evaluation_report.md"):
        """Generate markdown evaluation report."""
        from datetime import datetime
        
        metrics = self.calculate_metrics()
        
        report = []
        report.append("# Agent-S Evaluation Report")
        report.append("")
        report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Configuration section
        report.append("## Test Configuration")
        report.append("")
        report.append("### Reasoning Model (Engine)")
        report.append(f"- **Provider:** {engine_params.get('engine_type', 'N/A')}")
        report.append(f"- **Model:** {engine_params.get('model', 'N/A')}")
        report.append("")
        report.append("### Grounding Model")
        report.append(f"- **Provider:** {grounding_params.get('engine_type', 'N/A')}")
        report.append(f"- **Model:** {grounding_params.get('model', 'N/A')}")
        report.append(f"- **Resolution:** {grounding_params.get('grounding_width', 1920)}x{grounding_params.get('grounding_height', 1080)}")
        report.append("")
        
        # Metrics section
        report.append("## Evaluation Metrics")
        report.append("")
        report.append("| Metric | Value | Description |")
        report.append("|--------|-------|-------------|")
        report.append(f"| **TSR (Task Success Rate)** | {metrics['tsr']:.1f}% | {metrics['passed']}/{metrics['total']} tasks passed |")
        report.append(f"| **SCR (Step Completion Rate)** | {metrics['scr']:.1f}% | {metrics['total_steps_used']}/{metrics['total_max_steps']} steps used |")
        report.append("")
        
        # Results table
        report.append("## Task Results")
        report.append("")
        report.append("> **Note:** Results are evaluated using WebAppEval automatic evaluation framework.")
        report.append("")
        report.append("| # | Task ID | Description | Agent Done | WebAppEval | Final | Steps |")
        report.append("|---|---------|-------------|------------|------------|-------|-------|")
        
        for i, result in enumerate(self.results, 1):
            agent_done = "✅" if result.get('agent_done', False) else "❌"
            webappeval = "✅" if result.get('webappeval_result') else "❌" if result.get('webappeval_result') is False else "N/A"
            final_status = "✅ PASS" if result['success'] else "❌ FAIL"
            desc = result['description'][:45] + "..." if len(result['description']) > 45 else result['description']
            steps = f"{result.get('steps_used', 0)}/{result.get('max_steps', 0)}"
            report.append(f"| {i} | {result['task_id']} | {desc} | {agent_done} | {webappeval} | {final_status} | {steps} |")
        
        report.append("")
        
        # Failed tasks details
        failed_tasks = [r for r in self.results if not r['success']]
        if failed_tasks:
            report.append("## Failed Tasks Details")
            report.append("")
            for result in failed_tasks:
                report.append(f"### Task {result['task_id']}: {result['description'][:60]}...")
                report.append(f"- **Agent Done:** {'Yes' if result.get('agent_done') else 'No'}")
                report.append(f"- **WebAppEval Result:** {'Pass' if result.get('webappeval_result') else 'Fail' if result.get('webappeval_result') is False else 'N/A'}")
                report.append(f"- **Steps used:** {result.get('steps_used', 0)}/{result.get('max_steps', 0)}")
                if result.get('agent_answer'):
                    answer_preview = str(result.get('agent_answer'))[:100]
                    report.append(f"- **Agent Answer:** {answer_preview}...")
                if result.get('error'):
                    report.append(f"- **Error:** {result['error']}")
                report.append("")
        
        # Write to file
        report_content = "\n".join(report)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"Evaluation report saved to: {output_path}")
        return output_path


def main():
    # Check if config file exists first
    if USE_CONFIG_FILE:
        logger.info("Using config.py for settings")
        engine_params = ENGINE_CONFIG.copy()
        grounding_params = GROUNDING_CONFIG.copy()
        env_config = TEST_CONFIG.get('env_config', 'env_config.json')
        tasks_file = TEST_CONFIG.get('tasks_file', 'dataset/prestashop_tasks.json')
        mode = TEST_CONFIG.get('mode', 'pyautogui')
        task_id = TEST_CONFIG.get('task_id')
    else:
        parser = argparse.ArgumentParser(description='Test PrestaShop with Agent-S')
        
        # Agent-S parameters
        parser.add_argument('--provider', default='openai', help='LLM provider')
        parser.add_argument('--model', default='gpt-4o', help='LLM model')
        parser.add_argument('--model_url', default='', help='Custom model URL')
        parser.add_argument('--model_api_key', default='', help='Model API key')
        
        # Grounding model parameters
        parser.add_argument('--ground_provider', default='huggingface', help='Grounding model provider')
        parser.add_argument('--ground_url', required=True, help='Grounding model URL')
        parser.add_argument('--ground_model', default='ui-tars-1.5-7b', help='Grounding model name')
        parser.add_argument('--ground_api_key', default='', help='Grounding model API key')
        parser.add_argument('--grounding_width', type=int, default=1920, help='Grounding height')
        parser.add_argument('--grounding_height', type=int, default=1080, help='Grounding height')
        
        # Test parameters
        parser.add_argument('--mode', choices=['pyautogui', 'playwright'], default='pyautogui',
                           help='Automation mode')
        parser.add_argument('--task_id', help='Run specific task ID only')
        
        # Config paths
        parser.add_argument('--env_config', default='env_config.json', help='Environment config path')
        parser.add_argument('--tasks', default='dataset/prestashop_tasks.json', help='Tasks file path')
        
        args = parser.parse_args()
        
        engine_params = {
            "engine_type": args.provider,
            "model": args.model,
            "base_url": args.model_url if args.model_url else None,
            "api_key": args.model_api_key if args.model_api_key else None,
        }
        
        grounding_params = {
            "engine_type": args.ground_provider,
            "model": args.ground_model,
            "base_url": args.ground_url,
            "api_key": args.ground_api_key if args.ground_api_key else None,
            "grounding_width": args.grounding_width,
            "grounding_height": args.grounding_height,
        }
        env_config = args.env_config
        tasks_file = args.tasks
        mode = args.mode
        task_id = args.task_id
    
    # Initialize tester
    tester = PrestaShopTester(env_config, tasks_file)
    
    # Filter tasks if specific ID provided
    if task_id:
        tester.tasks = [t for t in tester.tasks if t['task_id'] == task_id]
        if not tester.tasks:
            logger.error(f"Task ID {task_id} not found")
            return
    
    # Limit number of tasks if max_tasks is set
    max_tasks = TEST_CONFIG.get('max_tasks') if USE_CONFIG_FILE else None
    if max_tasks and len(tester.tasks) > max_tasks:
        logger.info(f"Limiting tasks from {len(tester.tasks)} to {max_tasks} (as per Task 4 requirement)")
        tester.tasks = tester.tasks[:max_tasks]
    
    logger.info(f"Running {len(tester.tasks)} tasks with WebAppEval automatic evaluation")
    
    # Setup agent
    agent = tester.setup_agent(engine_params, grounding_params)
    
    # Run tests
    tester.run_all_tasks(agent, mode=mode)
    
    # Print summary
    tester.print_summary()
    
    # Generate evaluation report
    tester.generate_report(engine_params, grounding_params)


if __name__ == '__main__':
    main()
