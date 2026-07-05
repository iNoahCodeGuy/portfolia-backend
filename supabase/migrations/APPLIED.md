# Applied migrations — production (project tjnlusesinzzlwvlbnnm)

The record of what has actually run against prod. Update this whenever a
migration is applied. There is no CLI state tracking — this file is it.

| Migration | Status | Evidence / notes |
| --- | --- | --- |
| 001_initial_schema | applied | kb_chunks serves retrieval in prod |
| 002_add_confessions_and_sms | applied | assumed with 001 (pre-rename era) |
| 003_fix_session_id_type | applied | assumed (fix for a live bug at the time) |
| 004_analytics_helpers | unverified | check Dashboard → Database → Functions |
| 005_crush_confessions_table | applied | crush flow writes + dashboard reads the table |
| 006_recruiter_leads_table | applied | contact capture writes + dashboard reads the table |
| 007_add_referral_source | applied | dashboard renders referral_source on leads |
| 008_conversation_analytics | unverified | check Dashboard for the analytics views |
| 009_fix_match_kb_chunks_type | applied | match_kb_chunks works in prod (retrieval healthy) |

Statuses marked *assumed*/*unverified* were reconstructed on 2026-07-04 during
the repo audit (files were renumbered from a state with duplicate 002/003
numbers). Two minutes in the Dashboard SQL Editor settles the unverified rows:

```sql
select proname from pg_proc where proname like '%analytics%';
select table_name from information_schema.tables where table_schema = 'public';
```
