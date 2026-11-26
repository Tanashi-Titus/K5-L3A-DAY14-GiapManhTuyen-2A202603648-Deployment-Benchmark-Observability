# Benchmark & Observability Report — Day 14

**Họ tên:** Giáp Mạnh Tuyên
**Ngày chạy:** 2026-11-25
**Môi trường:** Windows 11, Miniconda Python 3.13; Docker Desktop 29.9.3. Benchmark develop chạy local; observability và Locust chạy trong Docker Compose.

## 1. SLO của agent

| SLI | SLO | Lý do |
|---|---:|---|
| p95 latency `/ask` | < 500 ms | Phản ánh tail latency cho đa số request. |
| Error rate `/ask` | < 2% | Ngưỡng phát hiện lỗi upstream/app trong lab. |
| Accuracy golden dataset | ≥ 80% | Quality gate; eval cuối đạt 100% trên 23 câu. |

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 2.90 | 210.1 | 1708.0 | 1725.4 | 2.33% | FAIL |
| 10 | 26.01 | 211.4 | 1699.4 | 1725.5 | 1.33% | FAIL |
| 50 | 90.91 | 224.3 | 1708.4 | 1788.6 | 1.33% | FAIL |
| 100 | 43.83 | 763.2 | 4758.4 | 5259.4 | 0.33% | FAIL |

**Nhận xét:** RPS tăng đến concurrency 50 rồi giảm ở 100; p95/p99 tăng mạnh. Giới hạn tài nguyên/worker, mock slow requests và timeout khiến throughput không tăng tuyến tính. Tất cả cấu hình fail SLO latency; cấu hình concurrency 1/10/50 còn error rate 1.33–2.33%.

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) | Error rate | Ghi chú |
|---:|---:|---:|---:|---:|---|
| 0 | 212.9 | 248.0 | 272.7 | 1.00% | PASS |
| 0.03 (mặc định) | 11810.3 | 1452.3 | 1727.6 | 7.33% | FAIL; có 19 ReadTimeout, 3 HTTP 503 và max 3,172,411.9 ms trong report. |
| 0.1 | 414.6 | 1741.7 | 1888.2 | 1.33% | FAIL |

**Nhận xét:** p95/p99 nhạy với request chậm và thể hiện trải nghiệm ở phần đuôi phân phối. Average che khuất nhóm request timeout. Kết quả mặc định 0.03 là một lần chạy bất thường, được giữ nguyên theo JSON gốc chứ không coi là hành vi điển hình.

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 sau khi sửa KB |
|---|---:|---:|---:|
| Accuracy | 4.35% (1/23) | 91.30% (21/23) | 100% (23/23) |
| Avg tokens / câu | 57.7 | 108.8 | 114.2 |
| Tổng cost (USD) | $0.000412 | $0.000758 | $0.000795 |
| Cost / câu đúng (USD) | $0.00041175 | $0.00003607 | $0.00003458 |
| Quality gate | FAIL | PASS (min 80%) | PASS (min 100%, không regression) |

| ID sai ban đầu | Keyword thiếu | Sửa knowledge base |
|---|---|---|
| security-02 | token, expiration, signature | Bổ sung phân biệt JWT/API key và token, chữ ký, thời hạn. |
| scaling-03 | CPU, memory, custom metrics | Bổ sung cách Kubernetes HPA scale theo CPU, memory, custom metrics. |

**Trade-off:** v2 tăng accuracy nhưng dùng nhiều token hơn và chi phí tổng cao hơn v1. Sau khi bổ sung hai mục KB, accuracy 100%; cost/câu đúng giảm so với v2 ban đầu. p95 eval cuối là 243.9 ms; bộ 23 câu không thay thế load test.

## 4. Observability stack (production)

### 4.1 Screenshot

- [x] Grafana: [screenshots/grafana-dashboard.png](screenshots/grafana-dashboard.png)
- [x] Trace chậm Jaeger: [screenshots/jaeger-slow-trace.png](screenshots/jaeger-slow-trace.png)
- [x] Trace lỗi Jaeger: [screenshots/jaeger-error-trace.png](screenshots/jaeger-error-trace.png)
- [x] Prometheus alert firing: [screenshots/prometheus-alert-firing.png](screenshots/prometheus-alert-firing.png)

### 4.2 Thí nghiệm phá hệ thống

| # | Thay đổi | Alert | Thời gian tới firing | Tín hiệu |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.30` | `AgentHighErrorRate` firing | Rule yêu cầu duy trì 1 phút; thời điểm bắt đầu cấu hình không được ghi chính xác. | Error rate `/ask` |
| B | `MOCK_SLOW_RATE=0.30`, Locust 100 users trong 2 phút | `AgentHighLatencyP95` firing | **Khoảng 139.829 giây (tính từ log):** fault bắt đầu `2026-11-25T16:09:07.573Z`; Prometheus chuyển sang pending lúc `16:09:27.402Z`; rule yêu cầu giữ điều kiện thêm 120 giây. Mốc firing suy ra khoảng `16:11:27.402Z`, không phải timestamp firing được chụp trực tiếp. | p95 `/ask` khoảng 1.96 s; alert firing |
| C | LLM_MODEL=mock-llm-large, Locust 100 users trong 3 phút | AgentHighLatencyP95 firing; cost burn alert đã bắt đầu từ B | Không tách được cho C: alert cost đã firing trước khi đổi model; latency alert xác nhận trong lượt C. | p95 2700 ms; 86/7099 lỗi /ask (1.21%); 77 HTTP 503, 9 HTTP 502; 1 lỗi health 502 |
| D | Pause một agent replica | `AgentInstanceDown` và `AgentHighErrorRate` firing | Rule giữ điều kiện down 30 giây; elapsed chính xác không lưu. | Instance health, Prometheus Alerts |
| E | `AGENT_VERSION=v1` | Không chạy riêng trong phiên có evidence | — | Accuracy eval theo version |

Screenshot Prometheus cho thấy `AgentHighErrorRate` và `AgentInstanceDown` cùng firing. `activeAt` tương ứng là `2026-11-25T15:59:12.401Z` và `2026-11-25T15:58:57.401Z`; không có timestamp thao tác A/D bắt đầu để tính elapsed chính xác. Bắt đầu fault B lúc `2026-11-25T16:09:07.573Z`; `AgentHighLatencyP95` đã được xác nhận firing sau khi điều kiện p95 > 1 s duy trì đủ 2 phút. Với C (LLM_MODEL=mock-llm-large, 100 users / 3 phút), Locust ghi 7,099 request /ask, 86 lỗi (1.21%), median 600 ms, average 1,021 ms, p95 2,700 ms, p99 5,300 ms, max 7,022 ms và 39.63 RPS. Có 77 lỗi 503 và 9 lỗi 502 trên /ask; /health có 1 lỗi 502 trong 729 request. AgentHighLatencyP95 firing trong lượt này. Cost burn alert có từ bài B, nên không quy thời điểm firing cho model lớn.

Các mã 502 ở Scenario C được ghi trong lượt chaos/load test đó; chúng không phản ánh trạng thái Railway sau khi sửa `REDIS_URL`. Kiểm tra CP6 public sau redeploy trả `/health` 200 và `/ready` 200.

**Phân tích thí nghiệm E:** lượt đổi `AGENT_VERSION=v1` không được chạy riêng trong phiên có evidence. Dự kiến health, latency và error-rate alert không phát hiện việc chất lượng câu trả lời giảm nếu service vẫn khỏe; golden eval/quality gate mới bắt được regression (v1 chỉ đạt 1/23 so với v2 đã sửa 23/23). Khi rollout thật, cần gắn `agent_version` vào metrics, chạy golden eval trước rollout, so sánh accuracy/cost bằng canary và chặn deploy nếu quality gate fail.

### 4.3 Debug bằng trace

- Trace chậm: `d0525745543602ef11c6d02650e124c5`.
- Tổng thời gian HTTP: khoảng 1742.5 ms.
- Span lâu nhất: `chat mock-llm-small`, khoảng 1704.6 ms (~97.8% tổng thời gian).
- Log JSON có cùng trace ID:

```json
{"event":"llm_call","trace_id":"d0525745543602ef11c6d02650e124c5","instance":"cdcac3f99bb5","llm_ms":1698.6}
{"event":"http_request","trace_id":"d0525745543602ef11c6d02650e124c5","method":"POST","path":"/ask","status":200,"ms":1738.7}
```

Trace lỗi `3087bc6b31f8442844cb6705b1856f24`: upstream mock LLM trả 503, request `/ask` trả 503 sau khoảng 126.7 ms; Jaeger hiển thị exception.

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures `/ask` |
|---:|---:|---:|---:|---:|---:|
| 1 | 48.10 | 220 | 2300 | 3800 | 59 / 5736 (1.03%) |
| 3 | 56.79 | 210 | 890 | 1700 | 72 / 6738 (1.07%) |

**Giải thích:** Ba instance tăng throughput khoảng 18%, giảm p95 khoảng 61% và p99 khoảng 55%. Failure rate gần 1% ở cả hai lượt, phù hợp với mock error rate mặc định 1%; scale ngang giảm tail latency nhưng không loại bỏ lỗi upstream.

## 6. Kết luận

- p95/p99 cho thấy tail latency mà average che khuất; concurrency cao có thể làm p95 xấu dù RPS tăng.
- Golden dataset và quality gate phát hiện regression mà health/error metrics có thể bỏ sót.
- Distributed tracing nối request với span LLM chậm/lỗi; metrics alert phát hiện xu hướng và instance unhealthy.
- Nên bổ sung alert saturation (CPU/RAM/event-loop/connection pool), Redis readiness, budget burn rate, auth failures và accuracy regression theo version.

**Giới hạn:** Benchmark dùng mock LLM trên máy local nên không dự báo trực tiếp latency/cost của nhà cung cấp thật. Một lần chạy `MOCK_SLOW_RATE=0.03` có timeout bất thường; báo cáo giữ nguyên số liệu JSON gốc.
