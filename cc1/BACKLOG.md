# BACKLOG
_Future features and deferred work. Update when: deferring tasks, planning phases, capturing ideas._

## Product Vision
_What are we building and why?_

[Define your product vision here]

## Future Enhancements

### Phase 1: Core Features
- [ ] User authentication
- [ ] Data persistence patterns
- [ ] Basic CRUD operations

### Phase 2: Improvements
- [ ] Better error handling
- [ ] Request logging
- [ ] Admin interface
- [ ] Export functionality

### Phase 3: Scale (if needed)
- [ ] Redis caching
- [ ] Background jobs
- [ ] Multiple workers
- [ ] Monitoring

## Technical Debt
- [x] Optimize rate limiting and batch size for faster migration #priority:medium
  - ✅ Tested 0.2s rate limiting on 872,571 campaign migration
  - ✅ Discovered smart delay strategy: only delay after successful operations
  - ✅ Reduced processing from 5-10 days to 8-9 hours (~10x improvement)
  - 📊 Results: 1,766 success, 5,008 failed (CONCURRENT_MODIFICATION), 865,797 "not found"
  - Trade-off: 0.2s causes 74% failure rate, but acceptable for fast bulk with retry
  - Recommendation: Use 0.2s + smart delays for bulk ops, 0.5s for higher reliability
  _#claude-session:2025-11-19_
- [ ] Optimize listing tree operations with bulk mutations #priority:medium
  - Current implementation uses separate mutate operations for each level
  - Could combine more operations into single mutate where possible
  - Reduce API calls and improve performance for large trees
  - Consider batching multiple ad group tree operations
  _#claude-session:2025-11-12_
- [ ] Better handling of complex tree hierarchies #priority:medium
  - Current code assumes max 3 levels (CL1 → CL0 → CL3)
  - Add support for arbitrary depth hierarchies
  - Implement recursive tree traversal for collection and rebuilding
  - Add tree structure validation before mutations
  _#claude-session:2025-11-12_
- [ ] Add validation tools for tree structure integrity #priority:low
  - Create diagnostic script to validate tree structures
  - Check for orphaned nodes, missing OTHERS cases, invalid siblings
  - Add pre-flight checks before mutate operations
  - Helpful for debugging tree issues without API calls
  _#claude-session:2025-11-12_
- [ ] Validate Excel column structure before processing #priority:medium
  - Check inclusion sheet has 8 columns (A-H) before processing
  - Check exclusion sheet has 6 columns (A-F) before processing
  - Provide clear error message if column structure doesn't match expected format
  - Prevents cryptic "column index out of range" errors
  _#claude-session:2025-11-11_
- [ ] Add comprehensive error handling for Google Ads API failures #priority:high
  - Implement retry logic for transient failures
  - Better handling of rate limits
  - Graceful degradation when campaigns not found
  _#claude-session:2025-11-11_
- [ ] Add input validation
- [ ] Implement logging
- [ ] Add tests
- [ ] API documentation

## Ideas Parking Lot
_Capture ideas for future consideration_

- Progress monitoring dashboard for long-running migrations
  - Web UI to monitor migration progress in real-time
  - Show campaigns processed, success rate, estimated time remaining
  - Display incremental save checkpoints
  - Alert on high error rates or API issues
  - Useful for 5-10 day migration processes
  _#claude-session:2025-11-19_
- Dynamic bid strategy assignment from Excel
  - Add column to specify bid strategy per row instead of global mapping
  - Allow override of default bid strategy based on custom label 1
  - Support for different bid strategies per shop or category
  - More flexible than hardcoded BID_STRATEGY_MAPPING
  _#claude-session:2025-11-12_
- Support for batch processing multiple Excel files
  - Process multiple campaigns from different Excel files in one run
  - Aggregate results across multiple files
  - Parallel processing for faster execution
  _#claude-session:2025-11-11_

---
_Created: 2025-11-10_
_Updated: 2025-11-12_
