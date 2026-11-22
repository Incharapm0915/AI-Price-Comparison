import axios from "axios";

/** Base Axios client for the FastAPI backend. Every page/service call goes
 * through this — no component should hard-code a URL. */
export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api",
  // Generous: in live mode (MOCK_MODE=false), /search drives real
  // Playwright collectors against Amazon/Flipkart (page loads + throttling
  // between requests), which routinely takes 30-60s+ for a multi-result
  // search — this is not cold-start, the backend also warms its embedding
  // model at startup (see backend/app/main.py).
  timeout: 90000,
});
