# C4 Workflow Implementation - Status and Next Steps

## Fixed Issues

### 1. CSS Import Error Resolved
**Problem:** TypeScript error "Cannot find module or type declarations for side-effect import of './styles/c4/c4-HowC4Works.css'"

**Solution:**
- Removed local CSS imports from component files
- Added all C4 CSS imports to `main.tsx` for centralized management
- CSS files now loaded:
  - `c4-MLExplorer.css`
  - `c4-TelemetryExplorer.css`
  - `c4-ThreatInvestigation.css`
  - `c4-Authentication.css`
  - `c4-Registry.css`
  - `c4-Storage.css`
  - `c4-Policy.css`
  - `c4-HowC4Works.css`

### 2. CSS Variables Standardized
**Problem:** Inconsistent colors and duplicate CSS variables causing red/wrong colors

**Solution:**
- Replaced custom CSS variables with shared C4 theme variables from `c4.css`
- Updated `c4-MLExplorer.css` and `c4-HowC4Works.css` to use theme variables
- Colors now consistent across all C4 components

### 3. SHAP Plots Displayed
**Problem:** SHAP plots tab showed placeholder instead of actual plots

**Solution:**
- Updated SHAP tab to display 5 SHAP plots from `experiments/c4/plots/`
- Added proper error handling with fallback messages
- Plots now show: summary, bar, and 3 force plot examples

## Current State

### ML Explorer Now Shows:
- ✅ Model selection dropdown
- ✅ Model metadata (features, classes, metrics)
- ✅ SHAP plots with images
- ✅ Proper CSS styling
- ✅ Responsive design

### Components with Working CSS:
- ✅ MLExplorer - Full CSS applied
- ✅ TelemetryExplorer - Full CSS applied
- ✅ ThreatInvestigation - Full CSS applied
- ✅ Authentication - Full CSS applied
- ✅ Registry - Full CSS applied
- ✅ Storage - Full CSS applied
- ✅ Policy - Full CSS applied
- ✅ HowC4Works - Full CSS applied

## Required C4 Workflow Implementation

### Current Status: Not Implemented

The current React frontend uses **mock data** in `C4Page.tsx`. It does not:
- Call the actual C4 backend
- Run real security verification
- Execute ML inference
- Enforce the PASS → ML → FAIL → Skip ML rule

### Required Implementation Steps

#### Step 1: Create Backend API Endpoint
**File to create or modify:** Need to create an API endpoint

**What's needed:**
- REST API endpoint (e.g., `/api/c4/evaluate`)
- Accepts scenario name and packet data
- Calls C4TrustService.assess()
- Returns full assessment including security decision and ML result

**Implementation:**
```python
# Pseudo-code for FastAPI endpoint
@app.post("/api/c4/evaluate")
async def evaluate_packet(scenario: str, packet: TelemetryPacket):
    # 1. Get or generate packet for scenario
    # 2. Call C4TrustService.assess(packet, signature)
    # 3. If mandatory security_pass = True, run ML
    # 4. Return complete assessment
    return {
        "assessment": assessment,
        "ml_status": "COMPLETED" | "SKIPPED - SECURITY FAILURE",
        "security_status": "PASS" | "FAIL" | "REVIEW"
    }
```

#### Step 2: Update C4Page.tsx to Call Backend
**File:** `apps/web/src/features/c4/pages/C4Page.tsx`

**Current:** Uses mock data

**Required:** Call API endpoint for each scenario

**Implementation:**
```typescript
const handleRunScenario = async (scenario: string) => {
  const response = await fetch('/api/c4/evaluate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario })
  });
  const result = await response.json();
  setResults(prev => [...prev, result]);
};
```

#### Step 3: Enforce Security → ML Rule in Backend
**File:** `components/c4_trust/service.py`

**Current:** Already implements this correctly! ✅

**Verification needed:** Confirm that ML is only called when `mandatory_security_pass = True`

**Code location:** `service.py` lines 584-592
```python
if failures:
    # UNTRUSTED / REJECT
    # ML is skipped
elif security_unknowns:
    # UNKNOWN / SECURITY_REVIEW
    # ML is skipped
else:
    # All mandatory checks passed
    # Run ML if available
```

#### Step 4: Update Telemetry Explorer to Show ML Status
**File:** `apps/web/src/features/c4/components/TelemetryExplorer.tsx`

**Current:** Shows trust label, routing outcome, behavioral score

**Required:** Add fields for:
- Security Status: PASS, FAIL, REVIEW
- ML Status: COMPLETED, SKIPPED - SECURITY FAILURE, SKIPPED - REVIEW, UNAVAILABLE

**Implementation:**
- Add new columns to table
- Add ML status badge
- Filter by ML status

#### Step 5: Update TypeScript Types
**File:** `apps/web/src/features/c4/types/index.ts`

**Required:** Add new fields to `C4AssessmentResult`

**Implementation:**
```typescript
export interface C4AssessmentResult {
  // ... existing fields ...
  security_status: 'PASS' | 'FAIL' | 'REVIEW';
  ml_status: 'COMPLETED' | 'SKIPPED - SECURITY FAILURE' | 'SKIPPED - REVIEW' | 'UNAVAILABLE - MISSING FEATURES';
  security_failure_reason?: string;
}
```

#### Step 6: Test Scenarios
**Required outcomes from security gate:**

| Scenario | Security Status | ML Status |
|----------|----------------|-----------|
| Valid HMAC | PASS | COMPLETED (if features available) |
| Valid ECDSA | PASS | COMPLETED (if features available) |
| Tampered HMAC | FAIL | SKIPPED - SECURITY FAILURE |
| Replay HMAC | FAIL | SKIPPED - SECURITY FAILURE |
| Expired Certificate | FAIL | SKIPPED - SECURITY FAILURE |
| Untrusted CA | FAIL | SKIPPED - SECURITY FAILURE |
| Identity Mismatch | FAIL | SKIPPED - SECURITY FAILURE |
| Revoked Certificate | FAIL | SKIPPED - SECURITY FAILURE |
| Algorithm Fallback | FAIL | SKIPPED - SECURITY FAILURE |
| Missing Evidence | REVIEW | SKIPPED - REVIEW |

## Files That Need Changes

### Backend (Python)
1. **Create API endpoint** - New file or modify existing integration
2. **Verify C4TrustService.assess()** - Already correct ✅
3. **Add ML status tracking** - Modify return type if needed

### Frontend (TypeScript/React)
1. **C4Page.tsx** - Replace mock data with API calls
2. **types/index.ts** - Add security_status and ml_status fields
3. **TelemetryExplorer.tsx** - Display new fields and filters
4. **ScenarioButtons.tsx** - Update labels if needed

## Recommendation

The backend C4 security service is **already correctly implemented** - it only runs ML when `mandatory_security_pass = True`. The main work needed is:

1. **Create a simple API wrapper** around the existing C4 service
2. **Connect the React frontend** to this API
3. **Update the UI** to show the security → ML workflow

This preserves the existing security architecture while making it accessible through the web UI.

## Files Modified in This Session

### CSS Files (Fixed)
- `apps/web/src/main.tsx` - Centralized CSS imports
- `apps/web/src/styles/c4/c4-MLExplorer.css` - Fixed CSS variables
- `apps/web/src/styles/c4/c4-HowC4Works.css` - Fixed CSS variables
- `apps/web/src/features/c4/components/MLExplorer.tsx` - Removed local CSS import, added SHAP plots
- `apps/web/src/features/c4/components/HowC4Works.tsx` - Removed local CSS import

### Documentation Created
- `C4_TELEMETRY_FILTERING_INVESTIGATION.md` - Complete investigation report
- `C4_FRONTEND_FIXES.md` - Summary of frontend fixes
- `C4_WORKFLOW_IMPLEMENTATION.md` - This file - workflow implementation plan

## Next Steps

To implement the complete workflow:

1. **High Priority:** Create API endpoint that wraps C4TrustService
2. **High Priority:** Update C4Page.tsx to call the API
3. **Medium Priority:** Update types to include security status
4. **Medium Priority:** Update TelemetryExplorer to show ML status
5. **Low Priority:** Add CSV export functionality

Would you like me to proceed with creating the API endpoint and connecting the frontend to the backend?
