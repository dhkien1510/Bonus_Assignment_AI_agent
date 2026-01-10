# Agent-S Evaluation Report

**Generated:** 2026-01-10 00:47:56

## Test Configuration

### Reasoning Model (Engine)
- **Provider:** open_router
- **Model:** google/gemini-2.5-flash

### Grounding Model
- **Provider:** open_router
- **Model:** bytedance/ui-tars-1.5-7b
- **Resolution:** 1920x1080

## Evaluation Metrics

| Metric | Value | Description |
|--------|-------|-------------|
| **TSR (Task Success Rate)** | 65.0% | 13/20 tasks passed |
| **SCR (Step Completion Rate)** | 56.5% | 252/446 steps used |

## Task Results

> **Note:** Results are evaluated using WebAppEval automatic evaluation framework.

| # | Task ID | Description | Agent Done | WebAppEval | Final | Steps |
|---|---------|-------------|------------|------------|-------|-------|
| 1 | 1 | Navigate to the 'Clothes > Women' category an... | ✅ | ❌ | ❌ FAIL | 4/10 |
| 2 | 2 | Add 2 units of 'Hummingbird printed sweater' ... | ✅ | ✅ | ✅ PASS | 9/30 |
| 3 | 3 | Navigate to 'Accessories > Stationery' catego... | ✅ | ✅ | ✅ PASS | 4/15 |
| 4 | 4 | Add product 'The best is yet to come' framed ... | ✅ | ❌ | ❌ FAIL | 6/20 |
| 5 | 5 | Subscribe to the newsletter using a unique em... | ✅ | ✅ | ✅ PASS | 5/14 |
| 6 | 6 | Apply promo code (Product customization) '20O... | ❌ | ✅ | ✅ PASS | 12/20 |
| 7 | 7 | Place an order as a guest customer for 'Mount... | ✅ | ✅ | ✅ PASS | 31/35 |
| 8 | 8 | Navigate to the 'Catalog', choose 'Products' ... | ✅ | ❌ | ❌ FAIL | 9/40 |
| 9 | 9 | Navigate to the 'Catalog', choose 'Discounts'... | ✅ | ✅ | ✅ PASS | 21/35 |
| 10 | 10 | Navigate to Orders page in back office, open ... | ✅ | ✅ | ✅ PASS | 4/15 |
| 11 | 11 | Navigate to Orders page in back office, selec... | ✅ | ✅ | ✅ PASS | 5/20 |
| 12 | 12 | Disable the product 'Customizable mug' from t... | ✅ | ❌ | ❌ FAIL | 6/25 |
| 13 | 13 | Navigate to the 'Catalog', choose 'Products'.... | ✅ | ✅ | ✅ PASS | 23/25 |
| 14 | 14 | Navigate to Orders page in back office, selec... | ❌ | ✅ | ✅ PASS | 10/10 |
| 15 | 15 | Navigate to the 'Customers', choose 'Customer... | ✅ | ✅ | ✅ PASS | 27/30 |
| 16 | 16 | Edit the CMS page 'About us' and change the p... | ✅ | ❌ | ❌ FAIL | 11/25 |
| 17 | 17 | Sort products in 'Clothes' category by 'Price... | ❌ | ❌ | ❌ FAIL | 20/20 |
| 18 | 18 | Navigate to page 2 of the 'Clothes' category ... | ✅ | ❌ | ❌ FAIL | 4/12 |
| 19 | 19 | Create a new order from back office for custo... | ✅ | ✅ | ✅ PASS | 21/25 |
| 20 | 20 | Navigate to Orders page in back office, selec... | ❌ | ✅ | ✅ PASS | 20/20 |

## Failed Tasks Details

### Task 1: Navigate to the 'Clothes > Women' category and return only t...
- **Agent Done:** Yes
- **WebAppEval Result:** Fail
- **Steps used:** 4/10
- **Agent Answer:** by default position...

### Task 4: Add product 'The best is yet to come' framed poster to wishl...
- **Agent Done:** Yes
- **WebAppEval Result:** Fail
- **Steps used:** 6/20
- **Agent Answer:** {'plan': '(Previous action verification)\nClicking "My wishlist (1)" successfully displayed the cont...

### Task 8: Navigate to the 'Catalog', choose 'Products' and clicks on '...
- **Agent Done:** Yes
- **WebAppEval Result:** Fail
- **Steps used:** 9/40
- **Agent Answer:** {'plan': '(Previous action verification)\nThe previous action of clicking "Save" was successful. A "...

### Task 12: Disable the product 'Customizable mug' from the back office ...
- **Agent Done:** Yes
- **WebAppEval Result:** Fail
- **Steps used:** 6/25
- **Agent Answer:** not found on the storefront, which is the expected behavior for a disabled product...

### Task 16: Edit the CMS page 'About us' and change the page title to 'A...
- **Agent Done:** Yes
- **WebAppEval Result:** Fail
- **Steps used:** 11/25
- **Agent Answer:** {'plan': '(Previous action verification)\nThe previous action of clicking the "Save" button was succ...

### Task 17: Sort products in 'Clothes' category by 'Price, low to high' ...
- **Agent Done:** No
- **WebAppEval Result:** Fail
- **Steps used:** 20/20
- **Agent Answer:** {'plan': '(Previous action verification)\nThe previous action was successful. The "Sort by" dropdown...

### Task 18: Navigate to page 2 of the 'Clothes' category and return the ...
- **Agent Done:** Yes
- **WebAppEval Result:** Fail
- **Steps used:** 4/12
- **Agent Answer:** {'plan': '(Previous action verification)\nThe previous action of scrolling down was successful, but ...
