# Backlog

Known problems and requested features, written the way they were reported.
Copy the ones you take on into your repository's Issues before you start, and
link the issue from your pull request.

Labels: `bug`, `performance`, `flaky-test`, `feature`, `data-quality`,
`good-first-issue`.

---

## Reported problems

### 1. Page 1 of the hydrant list doesn't start at the beginning
`bug` `good-first-issue`

> "I asked for `/hydrants?size=10` and the first hydrant id I got wasn't the
> lowest one. Where did the first ten go?" — dispatcher

**Done when:** page 1 starts with the first hydrant in id order, and a test
shows pages 1 and 2 are consecutive with nothing skipped.

### 2. Jurisdiction search is picky about capitals
`bug` `good-first-issue`

> "`?jurisdiction=howland township` returns zero hydrants. `Howland Township`
> works. Our dispatch software sends lower case."

**Done when:** jurisdiction filters ignore case on `/hydrants` and
`/hydrants/overdue`, with tests.

### 3. Inspection times entered in Eastern time come out wrong
`bug`

> "Crew logged an inspection at 3:05 PM. The API says 15:05 UTC, which is
> 11:05 AM here. Every inspection we enter is four or five hours off."

**Done when:** an inspection sent with any time-zone offset is stored as the
same instant in UTC, with a test for an offset that crosses midnight.

### 4. The county-wide overdue list is slow
`performance`

> "`/hydrants/overdue` with no jurisdiction takes several seconds. Our nightly
> report times out."

**Done when:** the county-wide request is at least 10× faster on the full
database, the response is unchanged, and the pull request shows before-and-after
timings and explains the cause.

### 5. CI fails now and then on `test_overdue_count_matches_ages`
`flaky-test`

> "Re-running the job makes it pass. It fails maybe one run in ten."

**Done when:** the root cause is found and explained in the pull request, the
test is deterministic, and the service and the test agree on the overdue rule
stated in the README. Re-running until green is not a fix.

### 6. Closing a work order doesn't record when it was closed
`bug`

> "We closed work order 1185 yesterday and `closed_at` is still empty, so it
> never shows up in our time-to-repair report."

**Done when:** setting `status` to `closed` sets `closed_at`, reopening clears
it, and both are tested and audited.

---

## Requested features

### 7. Nearest hydrants
`feature`

`GET /hydrants/near?lat=…&lng=…&radius_m=…` returning hydrants within the
radius, nearest first, with the distance in meters. Engine companies want the
three nearest in-service hydrants to an address.

### 8. Inventory cleanup report
`feature` `data-quality`

The inventory has records that need a human to look at them: hydrants with no
jurisdiction, hydrants recorded in another county or state, and pairs of
hydrants so close together (within 3 meters) that one may be a duplicate. Add
`GET /data-quality` listing each kind with counts and hydrant ids.

### 9. Open work orders on the hydrant detail
`feature` `good-first-issue`

`GET /hydrants/{id}` should include the hydrant's open and assigned work orders.

### 10. CSV export
`feature`

`GET /hydrants.csv` with the same filters as `/hydrants`, RFC 4180 quoting, and
a UTF-8 byte-order mark so Excel opens it cleanly.

### 11. Safe retries for writes
`feature`

Clients retry when a request times out, and a retried `POST /work-orders`
currently opens a second, duplicate work order. Support an `Idempotency-Key`
header on `POST /work-orders` and `POST /inspections`: the same key within 24
hours returns the original result instead of writing again.

### 12. Per-key rate limits
`feature`

Limit each API key to a configurable number of requests per minute and answer
`429` with a `Retry-After` header when it is exceeded.
