# Codebase Cleanup Analysis

## Files to Remove (Redundant/Obsolete)

### Backend Main Files
1. **`src/backend/main_foundry.py`** - Large complex version with multi-agent orchestration
   - Superseded by `main_simple_foundry.py` which works correctly
   - Contains unfinished orchestration logic that we don't need yet
   - **REMOVE**: Too complex for current needs

2. **`src/backend/main_simple_with_agents.py`** - Agent creation capabilities
   - Was for testing agent creation, not needed for production
   - We're using pre-existing agents in Azure AI Foundry
   - **REMOVE**: Development/testing artifact

### Test/Debug Files
3. **`test_foundry_direct.py`** - Early connection testing
   - Uses wrong endpoint format (azureml.ms instead of services.ai.azure.com)
   - Superseded by `debug_agents.py` which works correctly
   - **REMOVE**: Obsolete connection method

4. **`test_create_agent.py`** - Agent creation testing
   - Not needed since we use pre-existing agents
   - Was for development/exploration only
   - **REMOVE**: Development artifact

5. **`check_thread_api.py`** - API structure discovery
   - Served its purpose (helped fix the API calls)
   - Now that we know the correct API structure, not needed
   - **REMOVE**: One-time diagnostic tool

6. **`test_complete_flow.py`** - Detailed API exploration
   - Very detailed debug output, superseded by simpler tests
   - `test_simple_agent.py` covers the same functionality more cleanly
   - **REMOVE**: Verbose debugging artifact

### Configuration Files
7. **`ai_foundry_agents_config.json`** - Agent configuration
   - Appears to be unused configuration
   - We're discovering agents dynamically from Azure AI Foundry
   - **KEEP**: May be needed for future configuration

### Files to Keep
- **`src/backend/main_simple_foundry.py`** - ✅ MAIN PRODUCTION FILE
- **`src/backend/main.py`** - ✅ Original backend (may be needed for comparison)
- **`debug_agents.py`** - ✅ Useful diagnostic tool
- **`test_simple_agent.py`** - ✅ Clean integration test
- **`test_agent_integration.py`** - ✅ Comprehensive pytest suite

## Summary
**Remove 6 files** that are redundant development/testing artifacts:
- 2 superseded backend files
- 4 obsolete test/debug files

This will clean up the codebase while keeping the working production code and useful utilities.