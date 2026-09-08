# README_submission — Lab 17 Multi-Memory Agent

## 3 câu lý thuyết

**Layer quan trọng nhất:** `long_term`, vì nó chiếm 4/11 case (E02, E03, E08, E09) — nhiều nhất — và duy nhất phải xử lý cả cross-session preference (E02), open-loop task (E03), conflict/recency (E08: `BLUEBIRD-42` đổi Python → TypeScript/NestJS) lẫn user isolation (E09: query của `lan-lab17` không leak `ORCHID-27` của `minh-lab17`). Sai `user_id` hay bỏ recency ở đây hỏng nhiều điểm nhất.

**Trade-off Context Block (Zep) vs tự build Redis+Qdrant:** Zep cho relevance ranking, conflict/recency và provenance (`valid_at`/`invalid_at`) "miễn phí" qua `thread.get_user_context`, đổi lại latency cao hơn (long_term ~1.1–1.5s) và phụ thuộc nhà cung cấp. Redis/Qdrant nhanh, tự chủ nhưng phải tự viết ranking/conflict resolution — chỉ hợp baseline KV/vector đơn giản, không thay được knowledge graph khi cần suy luận quan hệ.

**Guardrail chống memory poisoning:** opt-in consent trước ingest (`consent.json`); redact PII trước khi lưu; user-scoped namespace nghiêm ngặt (mọi call truyền đúng `user_id`) chống leak/poison chéo user; heartbeat chỉ de-duplicate/mark stale, không tự thêm instruction mới vào durable memory.

## 4 câu phân tích benchmark

1. **Layer hit rate thấp nhất:** với `--impl student` cả 4 layer đạt 100%. So `no_memory` baseline, `long_term`/`episodic`/`semantic` rơi về 0% (chỉ `short_term` còn pass) — 3 layer này phụ thuộc hoàn toàn vào retrieval.
2. **Query nhiều token nhất:** E03 (`long_term`, 1568 token) vì Context Block gộp toàn bộ `USER_SUMMARY` nhiều sự kiện (ORCHID-27, BLUEBIRD-42, ASYNC-FIX-20, LAB-REPORT-1600) vào một context.
3. **E07 (mixed)** cần `long_term` + `semantic`. Evidence bắt buộc: `Python` (long_term) và `Idempotency-Key` (semantic), cả hai phải còn sau `assemble_context`.
4. **Token reduction vs hit rate:** `no_memory` giảm 81.8% token (cao hơn 14.2% của student) nhưng hit rate chỉ 18.2% — vì nó "giảm" bằng cách không retrieve gì. Reduction chỉ có ý nghĩa khi đi kèm hit rate cao; mất evidence là retrieval hỏng, không phải tối ưu.

## E08 (recency) & E10 (compaction)

- **E08:** fact cũ (`ORCHID-27`/Python) và fact mới (`BLUEBIRD-42`/TypeScript+NestJS) cùng tồn tại trong graph; Context Block ưu tiên fact có `valid_at` mới hơn nên trả đúng `BLUEBIRD-42, TypeScript, NestJS` không lẫn fact cũ — "recency wins".
- **E10:** giảm `max_recent_messages` 6→4 khiến raw turn chứa `REVIEW-DEADLINE-1600` bị evict khỏi `RECENT_TURNS`, nhưng `DURABLE_NOTES` (trích lúc compact) vẫn giữ constraint này — compaction ưu tiên state/constraint/TODO, không chỉ cắt theo thời gian như buffer.
