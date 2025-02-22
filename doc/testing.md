# API Testing Guidelines with cURL

## Overview
This document outlines the testing standards for AnythingAgent API using cURL. The tests cover basic functionality, error handling, and performance aspects of the API endpoints.

## Test Environment Setup

### Prerequisites
```bash
# Environment variables
export API_BASE_URL="http://localhost:8000"
export API_KEY="your-api-key"
```

### Test Data
```bash
# Create test data directory
mkdir -p test/data
# Create sample test files
echo '{"test": "data"}' > test/data/sample.json
```

## Test Categories

### 1. Basic Functionality Tests

#### Chat Completions
```bash
# Basic chat completion
curl -X POST "${API_BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello!"}
    ]
  }'

# Stream response
curl -X POST "${API_BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "stream": true,
    "messages": [{"role": "user", "content": "Count to 5"}]
  }'
```

#### File Operations
```bash
# Upload file
curl -X POST "${API_BASE_URL}/v1/files" \
  -H "Authorization: Bearer ${API_KEY}" \
  -F "file=@test/data/sample.json" \
  -F "purpose=fine-tune"

# List files
curl -X GET "${API_BASE_URL}/v1/files" \
  -H "Authorization: Bearer ${API_KEY}"

# Delete file
curl -X DELETE "${API_BASE_URL}/v1/files/file-id" \
  -H "Authorization: Bearer ${API_KEY}"
```

### 2. Error Handling Tests

```bash
# Invalid API key
curl -X POST "${API_BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer invalid-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# Missing required fields
curl -X POST "${API_BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# Invalid model name
curl -X POST "${API_BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "invalid-model",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### 3. Performance Tests

```bash
# Response time test (using time command)
time curl -X POST "${API_BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Quick test"}]
  }'

# Concurrent requests (using parallel processing)
for i in {1..10}; do
  curl -X POST "${API_BASE_URL}/v1/chat/completions" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
      "model": "gpt-3.5-turbo",
      "messages": [{"role": "user", "content": "Concurrent test '"$i"'"}]
    }' &
done
wait
```

## Test Automation Script

```bash
#!/bin/bash
# test_api.sh

# Set variables
API_BASE_URL="http://localhost:8000"
API_KEY="your-api-key"

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Test function
run_test() {
    local test_name=$1
    local curl_cmd=$2
    
    echo "Running test: $test_name"
    if eval "$curl_cmd"; then
        echo -e "${GREEN}✓ Test passed: $test_name${NC}"
    else
        echo -e "${RED}✗ Test failed: $test_name${NC}"
    fi
    echo "----------------------------------------"
}

# Basic functionality tests
run_test "Chat Completion" "curl -s -X POST '${API_BASE_URL}/v1/chat/completions' \
  -H 'Authorization: Bearer ${API_KEY}' \
  -H 'Content-Type: application/json' \
  -d '{\"model\":\"gpt-3.5-turbo\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}]}'"

# Error handling tests
run_test "Invalid API Key" "curl -s -X POST '${API_BASE_URL}/v1/chat/completions' \
  -H 'Authorization: Bearer invalid-key' \
  -H 'Content-Type: application/json' \
  -d '{\"model\":\"gpt-3.5-turbo\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}]}'"

# Performance tests
run_test "Response Time" "time curl -s -X POST '${API_BASE_URL}/v1/chat/completions' \
  -H 'Authorization: Bearer ${API_KEY}' \
  -H 'Content-Type: application/json' \
  -d '{\"model\":\"gpt-3.5-turbo\",\"messages\":[{\"role\":\"user\",\"content\":\"Quick test\"}]}'"
```

## Test Documentation Requirements

### Test Case Template
```markdown
## Test Case: [Name]
- **Description**: Brief description of what is being tested
- **Endpoint**: API endpoint being tested
- **Method**: HTTP method
- **Expected Response**: Expected response format and status code
- **curl Command**: Complete curl command for the test
- **Validation Criteria**: What determines if the test passes or fails
```

### Example Test Case Documentation
```markdown
## Test Case: Basic Chat Completion
- **Description**: Test basic chat completion functionality
- **Endpoint**: /v1/chat/completions
- **Method**: POST
- **Expected Response**: 
  - Status: 200
  - JSON response with message content
- **curl Command**: [Include the curl command used]
- **Validation Criteria**:
  - Response status is 200
  - Response contains valid JSON
  - Response includes message content
```

## Best Practices
1. Always use environment variables for sensitive data
2. Document all test cases thoroughly
3. Include both positive and negative test cases
4. Test rate limiting and error responses
5. Monitor response times and performance metrics
6. Keep test data separate and well-organized
7. Use automated scripts for regular testing
8. Maintain a log of test results 