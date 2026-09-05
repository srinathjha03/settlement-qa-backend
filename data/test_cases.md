# Test Case Reference

Use this list when picking demo txn_ids and when testing your /trace endpoint.

| txn_id  | Expected Result | Why |
|---------|-----------------|-----|
| TXN1001 | SUCCESS | Everything matches normally |
| TXN1002 | SUCCESS | Everything matches normally |
| TXN1003 | DELAY | Bank held due to bank_holiday |
| TXN1004 | SUCCESS | Everything matches normally |
| TXN1005 | DELAY | Bank held due to kyc_hold |
| TXN1006 | SUCCESS | Everything matches normally |
| TXN1007 | MISMATCH | Gateway amount 800 - fee 15 = 785 expected, but ledger shows 800 credited |
| TXN1008 | SUCCESS | Everything matches normally |
| TXN1009 | REQUIRES_HUMAN_REVIEW | Missing from ledger_logs.csv entirely |
| TXN1010 | SUCCESS | Everything matches normally |

Demo picks for the pitch (Person 2, Phase 4):
- Demo 1 (Standard Delay): TXN1003 (bank holiday) or TXN1005 (KYC hold)
- Demo 2 (Mismatch): TXN1007
- Demo 3 (Exception Handling): TXN1009
