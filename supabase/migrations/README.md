# Database Migrations

SQL migrations for the Supabase schema, numbered uniquely and run in order.
There is no CLI-tracked migration state — migrations are applied by pasting
into the Supabase Dashboard SQL Editor — so **[APPLIED.md](APPLIED.md) is the
record of what has run against production. Update it every time you apply
one.**

## How to apply

1. Supabase Dashboard → SQL Editor → New Query
2. Paste the migration file's contents, run it
3. Record it in APPLIED.md

## Migration order

| File | What it does |
| --- | --- |
| `001_initial_schema.sql` | Core tables: kb_chunks, messages, feedback + pgvector setup |
| `002_add_confessions_and_sms.sql` | Confessions + SMS tracking tables |
| `003_fix_session_id_type.sql` | session_id type correction |
| `004_analytics_helpers.sql` | Analytics helper functions |
| `005_crush_confessions_table.sql` | crush_confessions table (the crush-flow FSM writes here) |
| `006_recruiter_leads_table.sql` | recruiter_leads table (contact-capture flow writes here) |
| `007_add_referral_source_to_recruiter_leads.sql` | referral_source column |
| `008_conversation_analytics.sql` | Conversation analytics tables/views |
| `009_fix_match_kb_chunks_type.sql` | match_kb_chunks return type int → bigint |

`archive/` holds superseded one-off setup variants kept for reference —
never run them.

Rules:
- Never edit an applied migration; ship a new numbered file instead
- One concern per migration; the filename says what it does
- pgvector specifics live in [PGVECTOR_SETUP_GUIDE.md](PGVECTOR_SETUP_GUIDE.md)
