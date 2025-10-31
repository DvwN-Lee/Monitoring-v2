// TItanium-v2/api-gateway/main.go

package main

import (
	"encoding/json"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"strings"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
	httpRequestsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "http_requests_total",
			Help: "Total number of HTTP requests",
		},
		[]string{"method", "status"},
	)
	httpRequestDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "http_request_duration_seconds",
			Help:    "Duration of HTTP requests",
			Buckets: prometheus.DefBuckets,
		},
		[]string{"method"},
	)
)

func getEnv(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	return fallback
}

func newProxy(target *url.URL) *httputil.ReverseProxy {
	return httputil.NewSingleHostReverseProxy(target)
}

// statusRecorder records the status code of the response
type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(status int) {
	r.status = status
	r.ResponseWriter.WriteHeader(status)
}

func prometheusMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		recorder := &statusRecorder{
			ResponseWriter: w,
			status:         http.StatusOK,
		}
		timer := prometheus.NewTimer(httpRequestDuration.WithLabelValues(r.Method))
		next.ServeHTTP(recorder, r)
		timer.ObserveDuration()

		// Record status code
		statusClass := "unknown"
		if recorder.status >= 500 {
			statusClass = "5xx"
		} else if recorder.status >= 400 {
			statusClass = "4xx"
		} else if recorder.status >= 300 {
			statusClass = "3xx"
		} else if recorder.status >= 200 {
			statusClass = "2xx"
		}
		httpRequestsTotal.WithLabelValues(r.Method, statusClass).Inc()
	})
}

func main() {
	port := getEnv("API_GATEWAY_PORT", "8000")

	// 각 서비스 URL 파싱
	userServiceURL, _ := url.Parse(getEnv("USER_SERVICE_URL", "http://user-service:8001"))
	authServiceURL, _ := url.Parse(getEnv("AUTH_SERVICE_URL", "http://auth-service:8002"))
	blogServiceURL, _ := url.Parse(getEnv("BLOG_SERVICE_URL", "http://blog-service:8005"))

	transport := &http.Transport{
		ResponseHeaderTimeout: 2 * time.Second,
		IdleConnTimeout:       30 * time.Second,
		ExpectContinueTimeout: 1 * time.Second,
	}
	userProxy := httputil.NewSingleHostReverseProxy(userServiceURL)
	userProxy.Transport = transport
	authProxy := httputil.NewSingleHostReverseProxy(authServiceURL)
	authProxy.Transport = transport
	blogProxy := httputil.NewSingleHostReverseProxy(blogServiceURL)
	blogProxy.Transport = transport

	mux := http.NewServeMux()

	apiHandler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		path := r.URL.Path
		trimmedPath := strings.TrimPrefix(path, "/api")

		if strings.HasPrefix(trimmedPath, "/login") {
			r.URL.Path = trimmedPath
			authProxy.ServeHTTP(w, r)
		} else if strings.HasPrefix(trimmedPath, "/register") {
			r.URL.Path = "/users"
			userProxy.ServeHTTP(w, r)
		} else if strings.HasPrefix(trimmedPath, "/users") {
			r.URL.Path = trimmedPath
			userProxy.ServeHTTP(w, r)
		} else if strings.HasPrefix(trimmedPath, "/posts") {
			r.URL.Path = path
			blogProxy.ServeHTTP(w, r)
		} else {
			http.NotFound(w, r)
		}
})

	mux.Handle("/api/", apiHandler)
	mux.Handle("/metrics", promhttp.Handler())

	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	mux.HandleFunc("/stats", func(w http.ResponseWriter, r *http.Request) {
		stats := map[string]interface{}{
			"api-gateway": map[string]interface{}{
				"service_status": "online",
				"info":           "Proxying API requests",
			},
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(stats)
	})

	log.Printf("Go API Gateway started on :%s", port)
	srv := &http.Server{
		Addr:              ":" + port,
		Handler:           prometheusMiddleware(mux),
		ReadHeaderTimeout: 2 * time.Second,
		WriteTimeout:      10 * time.Second,
		IdleTimeout:       60 * time.Second,
	}
	if err := srv.ListenAndServe(); err != nil {
		log.Fatal(err)
	}
}
