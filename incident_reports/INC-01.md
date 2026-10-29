# INC-01: B+ Tree Range Searches Traverse Unnecessary Nodes

## Summary

The B+ tree's range-search implementation was inefficient because it recursively traversed the entire tree rather than using the linked leaf nodes. This caused range and prefix searches to visit significantly more nodes than necessary. After changing the traversal method, range searches became approximately 26 times faster and prefix searches approximately 158 times faster in our CORE benchmarks.

## Detection

The E6 B+ tree order experiment highlighted unusually expensive range searches, especially at smaller tree orders. The pre-fix range-search figure (analysis/e6_range_search.png) showed that range searches at order 3 took approximately 26,000 microseconds, compared with approximately 1,700 microseconds at order 512.

This prompted us to investigate the range-search implementation. Examining _collect_range() revealed that it recursively visited every subtree instead of using the linked leaf nodes.

## Expected vs. observed

A B+ tree should locate the starting leaf of a range query in approximately O(logₘ n) time, where m represents the tree's branching factor. It should then scan only the relevant leaf entries, giving an expected range-search cost of approximately O(logₘ n + k), where k represents the number of entries examined or returned, assuming a fixed leaf capacity.

The original implementation instead traversed the entire tree, producing approximately O(n) work even when the requested range contained relatively few results.

In our CORE benchmarks, the median counters for range-search batches decreased from 439,400 to 5,001 nodes visited and from 9,130,600 to 96,005 comparisons after the fix.

For prefix-search batches, nodes visited decreased from 699,400 to 2,185, while comparisons decreased from 14,479,200 to 34,959.

These results show that the original implementation performed substantially more work than necessary.

## Evidence

The before-and-after CORE benchmarks on the same Apple M4 MacBook Air showed significant improvements in B+ tree performance. Range searches decreased from approximately 3.00 ms to 0.115 ms per operation (26× faster), while prefix searches decreased from 7.79 ms to 0.049 ms (158× faster).

Performance counters confirmed the improvement. For range searches, median nodes visited decreased from 439,400 to 5,001, and comparisons decreased from 9,130,600 to 96,005. For prefix searches, nodes visited decreased from 699,400 to 2,185, and comparisons decreased from 14,479,200 to 34,959. These counters represent benchmark batches, not individual operations.

Both sessions were recorded under code_version 7d98672-dirty, with session IDs 9c12510126aa (before) and 4e62119aa32b (after). Overall, the results demonstrate that linked-leaf traversal substantially reduced unnecessary work and improved search performance.

To examine the B+ tree's structure, I created a separate test tree containing 1,000 keys with an order of 32. The `structure_info()` method reported a height of 3, 62 leaf nodes, and an average leaf fill of approximately 52%. This confirms that the tree maintained a multi-level structure with linked leaves that could be used for efficient range searches.

## Root cause 

The bug was located in indexes/bplus_tree.py, in the _collect_range() function, which begins at line 180 in the corrected version. The range_search() function at line 173 calls this method.

Originally, _collect_range() recursively visited every child of each internal node and examined every leaf. Although this produced correct results by checking whether each key fell within the requested range, it performed unnecessary work.

The B+ tree already maintained linked leaf nodes through their next pointers. However, the original range-search implementation did not use these links.

As a result, even searches covering a small range traversed the entire tree.

## Fix

I modified _collect_range() to use the B+ tree's linked leaf nodes.

The corrected implementation:

Calls _find_leaf(lo) to locate the leaf containing the beginning of the requested range.

Examines keys in that leaf and adds matching values to the results.

Uses leaf.next to move to subsequent leaves.

Stops when it encounters a key greater than the upper bound hi.

This avoids visiting unrelated subtrees and reduces the number of comparisons required for range searches.

The corrected implementation was committed in 35349d9. The changes to indexes/bplus_tree.py can be reviewed in that commit's Git diff.

## Verification

I ran the CORE benchmark before and after modifying _collect_range(), using the same machine and benchmark configuration.

The results showed substantial improvements in both range and prefix search performance, along with large reductions in node visits and comparisons.

After the fix and subsequent code cleanup, I ran make test, which returned:

168 passed, 3 skipped in 2.58 seconds.

This confirmed that the existing correctness tests continued to pass.

Both benchmark sessions were recorded with the same uncommitted code_version label, so the session identifiers are used to distinguish the original and corrected implementations.


## Impact on recommendations

This bug could make the B+ tree appear less suitable for features that require range or prefix searches.

Because the original implementation visited the entire tree, its measured performance did not reflect the efficiency expected from a correctly implemented B+ tree.

After the fix, range and prefix searches became significantly faster. This strengthens the case for recommending the B+ tree for features involving ordered searches, rather than rejecting it based on the original benchmark results.


## Why the tests didn't catch it

The existing tests focused on whether range searches returned the correct values, rather than how efficiently those values were found.

The original implementation still returned correct results, so it passed the correctness tests despite traversing unnecessary nodes.

A performance-oriented test could catch this bug by constructing a large B+ tree, running a range search that returns relatively few values, and checking the number of nodes visited.

If a small range query visits nearly every node in the tree, that would indicate that the implementation is not taking advantage of the B+ tree's structure.
