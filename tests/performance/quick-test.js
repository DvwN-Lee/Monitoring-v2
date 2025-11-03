import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');

// Quick test configuration - shorter duration
export const options = {
  stages: [
    { duration: '30s', target: 10 },   // Ramp up to 10 users
    { duration: '1m', target: 10 },    // Stay at 10 users
    { duration: '30s', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests should be below 500ms
    http_req_failed: ['rate<0.01'],   // Error rate should be less than 1%
    errors: ['rate<0.01'],
  },
};

const BASE_URL = 'http://10.0.11.168:31304';

export default function () {
  // Test 1: Dashboard
  let dashboardRes = http.get(`${BASE_URL}/`);
  check(dashboardRes, {
    'dashboard status 200': (r) => r.status === 200,
    'dashboard response time < 1s': (r) => r.timings.duration < 1000,
  }) || errorRate.add(1);

  sleep(1);

  // Test 2: Blog
  let blogRes = http.get(`${BASE_URL}/blog/`);
  check(blogRes, {
    'blog status 200': (r) => r.status === 200,
    'blog response time < 1s': (r) => r.timings.duration < 1000,
  }) || errorRate.add(1);

  sleep(1);

  // Test 3: Blog API
  let blogApiRes = http.get(`${BASE_URL}/blog/api/posts`);
  check(blogApiRes, {
    'blog api status 200': (r) => r.status === 200,
    'blog api response time < 500ms': (r) => r.timings.duration < 500,
  }) || errorRate.add(1);

  sleep(1);

  // Test 4: Load Balancer Health
  let lbHealthRes = http.get(`${BASE_URL}/lb-health`);
  check(lbHealthRes, {
    'lb-health status 200': (r) => r.status === 200,
    'lb-health response time < 200ms': (r) => r.timings.duration < 200,
  }) || errorRate.add(1);

  sleep(1);
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'tests/performance/quick-results.json': JSON.stringify(data),
  };
}

function textSummary(data, options) {
  const indent = options.indent || '';
  const enableColors = options.enableColors || false;

  let output = '\n' + indent + '=== Performance Test Summary ===\n\n';

  // Metrics
  for (const [name, metric] of Object.entries(data.metrics)) {
    if (metric.values) {
      output += indent + `${name}:\n`;
      output += indent + `  min: ${metric.values.min.toFixed(2)}\n`;
      output += indent + `  avg: ${metric.values.avg.toFixed(2)}\n`;
      output += indent + `  max: ${metric.values.max.toFixed(2)}\n`;
      if (metric.values.p95) {
        output += indent + `  p95: ${metric.values.p95.toFixed(2)}\n`;
      }
      if (metric.values.p99) {
        output += indent + `  p99: ${metric.values.p99.toFixed(2)}\n`;
      }
    }
  }

  return output;
}
