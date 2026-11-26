# Day 14 Lab - Mission Answers

> Bản ghi phần CP0–CP4 đã thực hiện trong workspace. Số đo bên dưới lấy từ các lệnh chạy ngày 2026-11-25.

## CP0 — Setup

- Repo hiện tại đã có tên theo mẫu K5-L3A và remote GitHub cá nhân; branch: `main`.
- Miniconda base: Python 3.13.2. Docker: 29.9.3; Docker Compose: v5.7.0.
- `docker run --rm hello-world`: thành công.
- Để chạy checker Part 6 trong môi trường POSIX, WSL2 distro `AndroidBox` đã được cài Miniconda Python 3.13.18 (`os.name == "posix"`) và bật Docker Desktop WSL integration. Docker trong WSL kết nối Docker Engine 29.9.3.

## Part 1 — Localhost vs Production

### Exercise 1.1: Anti-patterns trong bản develop

1. API key và database URL được ghi cứng trong source; nếu commit/push thì secret có thể bị lộ.
2. `DEBUG` và `MAX_TOKENS` là cấu hình cố định, không đọc từ environment.
3. Dùng `print()` để log và còn in cả API key, làm lộ thông tin nhạy cảm.
4. Không có endpoint health/readiness để nền tảng biết tiến trình còn sống và sẵn sàng nhận traffic không.
5. Bind vào `localhost`, cố định cổng 8000 và bật `reload=True`; không phù hợp chạy trong container/cloud.
6. Thiếu quản lý vòng đời/shutdown có kiểm soát; request đang chạy có thể bị cắt khi dừng.

### Exercise 1.2: Chạy bản develop

- Gọi `POST /ask?question=Hello`: nhận **HTTP 200**.
- Mock response: “Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.”
- Console Windows cần `PYTHONIOENCODING=utf-8`; lần chạy đầu dùng encoding mặc định và lỗi khi in tiếng Việt, sau đó chạy lại thành công.

### Exercise 1.3: So sánh develop và production

| Hạng mục | Develop | Production | Vì sao quan trọng |
|---|---|---|---|
| Cấu hình | Hardcode trong file | Tập trung trong `config.py`, đọc biến môi trường | Có thể cấu hình riêng cho từng môi trường |
| Secret | Ghi trong source | Lấy từ environment; không log | Tránh lộ key khi chia sẻ code/log |
| Host/port | `localhost:8000` | `0.0.0.0`, port từ `PORT` | Container/cloud có thể nhận traffic bên ngoài |
| Health | Không có | Có `/health`, `/ready`, `/metrics` | Health phục vụ liveness; readiness điều khiển nhận traffic |
| Logging | `print()`, có thể lộ key | Logging có cấu trúc, không ghi secret | Dễ truy vấn và an toàn hơn |
| Shutdown | Không quản lý rõ | Lifespan và handler cho SIGTERM | Hoàn tất request và đóng tài nguyên có kiểm soát |
| Debug | Reload/debug bật cứng | Reload chỉ bật khi debug | Tránh debug server trên môi trường production |

- Bản production đã trả HTTP 200 cho `/health`, `/ready`, và `POST /ask`.

## Part 2 — Docker

### Exercise 2.1: Dockerfile cơ bản

1. Base image: `python:3.11`.
2. Working directory: `/app`.
3. Copy `requirements.txt` và cài dependencies trước khi copy source để thay đổi source không làm mất cache layer cài packages.
4. `CMD` đặt lệnh/mặc định có thể thay khi chạy container; `ENTRYPOINT` xác định executable chính và thường vẫn chạy kể cả khi truyền tham số khác.

### Exercise 2.2–2.3: Build và so sánh image

Đã build từ gốc repo:

- `my-agent:develop`: **1667796279 bytes** (xấp xỉ 1.55 GiB).
- `my-agent:advanced`: **239835510 bytes** (xấp xỉ 228.6 MiB).
- Bản multi-stage nhỏ hơn **85.62%** theo dung lượng image Docker đo được.

Stage builder cài compiler/build dependencies và Python packages. Stage runtime dùng `python:3.11-slim`, copy packages/source cần chạy, dùng user không phải root và không mang theo compiler cùng header build; vì vậy image cuối nhỏ hơn.

Đã chạy image develop trên host port 18001: `GET /health` và `POST /ask?question=What%20is%20Docker%3F` đều trả HTTP 200.

### Exercise 2.4: Docker Compose

Stack có Agent, Redis, Qdrant và Nginx. Các service nối trong network nội bộ; Agent chờ Redis/Qdrant healthy; Nginx public cổng 80/443 và proxy đến Agent. Redis giữ cache/session, Qdrant là vector database, Nginx làm reverse proxy/load balancer.

Đã chạy stack với Compose project riêng `k5-day14-docker`:

- `GET http://localhost/health` qua Nginx: **HTTP 200**.
- `POST http://localhost/ask` qua Nginx: **HTTP 200**.
- Đã dừng stack và xóa các volume do lần chạy này tạo.

## Part 3 — Cloud Deployment (CP6)

### Exercise 3.1–3.2: Railway / Render

- Đã tạo Railway project và Redis service, cấu hình public domain cho agent. URL dự kiến: `https://exquisite-embrace-production-d20b42aa.up.railway.app`.
- Ngày 2026-11-25 đã sửa biến production `REDIS_URL` trên Railway bằng các biến private của service Redis (`REDISUSER`, `REDISPASSWORD`, `REDISHOST`, `REDISPORT`) và apply/redeploy. Deployment đang Online. Kiểm tra public sau redeploy: `/health` **200**, `/ready` **200**, `POST /ask` thiếu key **401**, key sai **401**, key đúng **200**. API key được dùng trong request kiểm tra nhưng không ghi vào báo cáo. CP6 đạt.
- `railway.toml` cấu hình builder Dockerfile, health check `/health` và dùng `PORT` của platform. Railway TOML đặt cấu hình theo format Railway; Render Blueprint thường khai báo `services`, runtime/build, health check và `envVars` trong YAML. Cả hai cùng mô tả cách build/deploy và kiểm tra health, nhưng schema và tên thuộc tính theo từng nền tảng.

### Exercise 3.3: Cloud Run pipeline

`cloudbuild.yaml` mô tả pipeline: cài dependencies và chạy pytest; nếu pass thì build image gắn `$COMMIT_SHA` và `latest`; push image lên Container Registry; deploy Cloud Run ở `asia-southeast1` với min 1/max 10 instances, 512 MiB, 1 CPU và secret từ Secret Manager. `service.yaml` mô tả Service tương ứng, concurrency 80, timeout 60 giây, secret refs và probe `/health`/`/ready`. Đây là mô tả pipeline trong lab; chưa deploy lên GCP.

## Part 4 — API Security

### Exercise 4.1: API key

Dùng biến môi trường lab `AGENT_API_KEY=secret-key-123`:

| Trường hợp | Kết quả |
|---|---:|
| Thiếu `X-API-Key` | HTTP 401 |
| Key đúng | HTTP 200 |
| Key sai | HTTP 403 |

### Exercise 4.2–4.3: JWT và rate limit

- Đăng nhập bằng tài khoản lab `student`; token được giữ trong biến PowerShell, không ghi vào file hay in ra.
- Gửi 12 request liên tiếp: request 1–10 trả HTTP 200; request 11–12 trả HTTP 429.
- JWT mang thông tin user/role và hết hạn sau 60 phút. Request được xác thực qua `Authorization: Bearer <token>`.
- Rate limiter mẫu dùng sliding window trong memory: user 10 request/60 giây, admin 100 request/60 giây.

### Exercise 4.4: Cost guard

Code mẫu tính chi phí từ input/output tokens, theo dõi ngân sách hằng ngày ($1/user, $10 tổng) và cảnh báo từ 80%. Khi quá ngân sách user trả 402; global budget trả 503. Hiện số liệu nằm trong memory nên mất khi restart và không đồng bộ khi scale nhiều instance; production nên lưu và cập nhật usage nguyên tử trong Redis/DB, đặt TTL đến khi hết kỳ ngân sách.

## Part 5 — Scaling & Reliability

### Exercise 5.1: Health/readiness

- `/health` là liveness: cho biết tiến trình còn hoạt động; platform dùng để quyết định restart.
- `/ready` là readiness: cho biết instance đã sẵn sàng nhận traffic; load balancer bỏ route khi endpoint chưa ready.
- Trong lần chạy, cả hai trả HTTP 200. Payload `/health` báo `degraded` vì máy ghi nhận RAM 93.4%; status HTTP vẫn 200. `/ready` trả `{"ready":true,...}`.

### Exercise 5.2: Graceful shutdown

Gửi hai request `/ask?question=hello` đang xử lý rồi dừng server bằng Ctrl+C. Cả hai request hoàn tất với **HTTP 200**; server log ghi nhận cả hai trước khi thoát. Đây là kiểm tra SIGINT trên Windows. Đã chỉnh `05-scaling-reliability/production/app.py` để tắt autoreload và đặt thời gian graceful shutdown 30 giây; Uvicorn nhận SIGTERM, drain request đang chạy rồi gọi lifespan shutdown. **Bài test SIGTERM riêng cho sample CP4 chưa chạy được lại** trong phiên hoàn thiện này vì Docker Engine/WSL bị hệ thống từ chối quyền; lần checker CP5 đầy đủ trước đó đã xác nhận SIGTERM cho final project.

### Exercise 5.3–5.5: Stateless, Redis và load balancing

- Trong production sample, session history được lưu ở Redis thay vì biến memory của từng process; vì vậy instance nào nhận request kế tiếp cũng đọc được cùng lịch sử.
- Chạy Compose project `k5-day14-scaling` với 3 agent, Redis và Nginx. `test_stateless.py` gửi 5 request qua 3 instance ID khác nhau và đọc lại được 10 message trong cùng session.
- Kết luận: session được giữ qua Redis khi Nginx phân phối request tới các agent khác nhau.
- Ghi chú: script `test_stateless.py` hiện tại xác nhận nhiều instance và history; nó **không tự kill một instance**, dù phần mô tả trong CODE_LAB.md nói vậy.

## Part 6 — Final Project (CP5)

Đã chạy checker đầy đủ trong WSL2 bằng Miniconda Python 3.13.18 và Docker (không dùng `--static-only` hoặc `--skip-docker`) ngày 2026-11-25.

- Kết quả: **PASS 12/12 tiêu chí, 41/41 checks passed**.
- Docker image: build thành công, **238 MB**; container chạy được và `/health` trả 200.
- Redis readiness: `/ready` trả 200 khi Redis hoạt động; trả 503 khi Redis mất kết nối, trong khi `/health` vẫn 200.
- API key: thiếu/sai key trả 401; key đúng trả 200.
- Rate limit: Redis giữ state qua lần restart agent; cấu hình test 5 request/phút, request vượt ngưỡng trả 429.
- Cost guard: khi budget hết, request trả 402.
- Config và logging: cấu hình đọc từ environment; 7 dòng log kiểm tra được là JSON hợp lệ.
- Graceful shutdown: SIGTERM trong lúc có request cho request hoàn tất 200 và process thoát với mã 0; `docker stop` thoát mã 0 trong 1.6 giây.
- Deploy config: `railway.toml` hợp lệ, health check `/health`, port lấy từ biến `PORT`.

Checklist CP5: Dockerfile ✅ · Compose agent + Redis ✅ · `.dockerignore` ✅ · `/health` ✅ · `/ready` ✅ · API key ✅ · rate limit ✅ · cost guard ✅ · environment config ✅ · structured logging ✅ · graceful shutdown ✅ · Railway/Render config ✅.

## Part 7 — Benchmark & Observability (CP7–CP8)

### CP7: Benchmark local

- Eval trên golden dataset 23 câu: v1 **1/23 (4.35%)**, v2 trước khi sửa KB **21/23 (91.30%)**, v2 sau khi sửa **23/23 (100%)**; quality gate cuối PASS với min accuracy 1.0 và không regression.
- Hai câu v2 sai ban đầu: `security-02` (JWT token/expiration/signature) và `scaling-03` (Kubernetes HPA CPU/memory/custom metrics); đã bổ sung kiến thức và chạy eval lại.
- Đã chạy load test 300 request ở concurrency 1/10/50/100 và ba lượt `MOCK_SLOW_RATE`. Các kết quả/SLO được chép trong `BENCHMARK_REPORT.md`; lần `0.03` có 19 ReadTimeout và 3 HTTP 503, được đánh dấu bất thường.
- Report JSON đã được lưu tại `reports/`; file `eval_v2_fixed.json` là kết quả cuối cùng.
- Quality gate nằm trong eval/run_eval.py: exit code 1 nếu accuracy thấp hơn ngưỡng hoặc có regression; exit code 0 khi đạt. Khi gọi trong GitHub Actions, exit code khác 0 làm workflow/job FAIL, nên required status check có thể chặn merge/deploy.
- eval_v1.json, eval_v2.json, eval_v2_fixed.json lưu kết quả và trạng thái gate; eval cuối đạt 23/23, ngưỡng 100%, không regression.

### CP8: Observability stack, chaos, scale

- Compose stack chạy Grafana, Prometheus, Jaeger, Locust, Nginx và ba agent. Grafana có Golden Signals; Jaeger có trace chậm `d0525745543602ef11c6d02650e124c5` và trace lỗi `3087bc6b31f8442844cb6705b1856f24`, kèm event `exception`.
- Trong fault injection đã lưu, Prometheus hiển thị đồng thời `AgentHighErrorRate` và `AgentInstanceDown` firing. Ảnh trong `screenshots/prometheus-alert-firing.png`.
- Fault `MOCK_SLOW_RATE=0.30` với Locust 100 users cũng làm `AgentHighLatencyP95` firing sau khi p95 > 1 giây duy trì 2 phút; p95 quan sát khoảng 1.96 giây. CSV riêng được lưu trong `benchmark-results/`.
- Locust headless 100 users / 2 phút: 1 instance đạt 48.10 RPS, p95 2300 ms; 3 instances đạt 56.79 RPS, p95 890 ms. Chi tiết tại CSV trong `benchmark-results/` và báo cáo.
- SLO về tail latency chưa đạt ở benchmark concurrency và có một lần chạy slow-rate timeout bất thường. Scale ngang cải thiện throughput và p95 trong lần đo này, không loại bỏ lỗi upstream mock.

## AI log

- Dùng Codex để đọc yêu cầu lab, rà soát source và hỗ trợ soạn câu trả lời CP0–CP4.
- Dùng Codex hỗ trợ triển khai/rà soát Part 6, gồm FastAPI endpoints, Redis rate limit/cost guard, JSON logging, graceful shutdown và cấu hình Docker/Compose. Các thay đổi được kiểm tra bằng checker chính thức đầy đủ trong WSL2.
- Tự kiểm tra kết quả bằng `python check_production_ready.py`: **PASS 12/12, 41/41**. Số liệu ghi ở Part 6 lấy trực tiếp từ output checker; không dùng AI để bịa số đo.
- Dùng Codex hỗ trợ chạy benchmark local/Locust, kiểm tra metrics, traces, alerts và điền báo cáo bằng dữ liệu JSON/CSV đã lưu.
