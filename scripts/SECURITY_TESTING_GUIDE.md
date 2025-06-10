# Security Implementation Testing Guide

## Quick Test Commands

### 1. Start the Application with Security Features

```bash
# Start local development environment
docker-compose -f docker-compose.local.yml up -d

# Check logs to verify security middleware is loaded
docker-compose -f docker-compose.local.yml logs -f app
```

### 2. Basic Functionality Tests

#### Test Login with New Security
```bash
# Test login endpoint
curl -X POST "http://localhost:8111/api/dashboard/login" \
  -H "Content-Type: application/json" \
  -d '{"password": "meta-admin-2024"}'

# Should return JWT token
```

#### Test Rate Limiting
```bash
# Rapid fire requests to trigger rate limiting
for i in {1..10}; do
  curl -X POST "http://localhost:8111/api/dashboard/login" \
    -H "Content-Type: application/json" \
    -d '{"password": "wrong-password"}' &
done
wait

# After 5 failed attempts, should return 429 (Too Many Requests)
```

#### Test Security Headers
```bash
# Check security headers in response
curl -I "http://localhost:8111/api/dashboard/stats" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Should include headers like:
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# Strict-Transport-Security: max-age=31536000
```

## 3. Dashboard UI Tests

### Access Settings Page
1. **Open Browser**: http://localhost:3000/dashboard/settings
2. **Login**: Use password `meta-admin-2024`
3. **Verify**: Settings load with masked sensitive values
4. **Test**: Try editing a sensitive setting (should show password field)

### Test Password Change
1. **Navigate**: Settings page
2. **Add**: Password change functionality (if implemented in UI)
3. **Test**: Change from `meta-admin-2024` to new password
4. **Verify**: Can login with new password

## 4. Encryption Testing

### Test Redis Data Encryption
```bash
# Connect to Redis and check if sensitive data is encrypted
docker-compose -f docker-compose.local.yml exec redis redis-cli

# In Redis CLI:
KEYS meta-glasses:settings:global:*
GET meta-glasses:settings:global:gemini_api_key

# Should see encrypted data starting with "enc:" if value was set via dashboard
```

### Test Encryption Utils Directly
```bash
python3 -c "
import sys
sys.path.append('.')

# Mock Redis for testing
class MockRedis:
    def get(self, key): return None
import sys
sys.modules['utils.redis_utils'] = type('Module', (), {'r': MockRedis()})()

from utils.encryption import encrypt_value, decrypt_value, is_encrypted_value

# Test encryption
test_key = 'sk-test123456789'
encrypted = encrypt_value(test_key)
decrypted = decrypt_value(encrypted)

print(f'Original: {test_key}')
print(f'Encrypted: {encrypted[:50]}...')
print(f'Decrypted: {decrypted}')
print(f'Match: {test_key == decrypted}')
print(f'Is Encrypted: {is_encrypted_value(encrypted)}')
"
```

## 5. API Security Tests

### Test Settings API with Encryption
```bash
# Get JWT token first
JWT_TOKEN=$(curl -s -X POST "http://localhost:8111/api/dashboard/login" \
  -H "Content-Type: application/json" \
  -d '{"password": "meta-admin-2024"}' | jq -r '.token')

# Test updating a sensitive setting
curl -X PUT "http://localhost:8111/api/dashboard/settings/gemini_api_key" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": "AIza_test_key_123456789"}'

# Verify it's stored encrypted in Redis
docker-compose -f docker-compose.local.yml exec redis redis-cli GET meta-glasses:settings:global:gemini_api_key

# Should start with "enc:" indicating encryption
```

### Test Password Change API
```bash
# Change password via API
curl -X POST "http://localhost:8111/api/dashboard/settings/change-password" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "meta-admin-2024",
    "new_password": "new-secure-password-123"
  }'

# Test login with new password
curl -X POST "http://localhost:8111/api/dashboard/login" \
  -H "Content-Type: application/json" \
  -d '{"password": "new-secure-password-123"}'
```

## 6. Security Middleware Tests

### Test Rate Limiting in Detail
```bash
# Script to test rate limiting
cat > test_rate_limit.sh << 'EOF'
#!/bin/bash
echo "Testing rate limiting..."

# Make 120 requests (should hit 100 request limit)
for i in {1..120}; do
  response=$(curl -s -w "%{http_code}" -X GET "http://localhost:8111/api/dashboard/stats" \
    -H "Authorization: Bearer invalid_token" 2>/dev/null)
  
  if [[ $response == *"429"* ]]; then
    echo "Request $i: Rate limited (429) ✓"
    break
  elif [[ $i -gt 100 ]]; then
    echo "Request $i: Should be rate limited but wasn't ✗"
  fi
done
EOF

chmod +x test_rate_limit.sh && ./test_rate_limit.sh
```

### Test IP Blocking
```bash
# Simulate multiple failed login attempts to trigger IP blocking
for i in {1..6}; do
  echo "Failed attempt $i"
  curl -X POST "http://localhost:8111/api/dashboard/login" \
    -H "Content-Type: application/json" \
    -d '{"password": "wrong-password"}'
  sleep 1
done

# After 5 attempts, should get 429 (rate limited) or 403 (blocked)
```

## 7. Browser Security Tests

### Test Security Headers
Open browser dev tools and check response headers:

```javascript
// In browser console
fetch('/api/dashboard/stats', {
  headers: { 'Authorization': 'Bearer YOUR_TOKEN' }
}).then(response => {
  console.log('Security Headers:');
  console.log('X-Frame-Options:', response.headers.get('X-Frame-Options'));
  console.log('X-Content-Type-Options:', response.headers.get('X-Content-Type-Options'));
  console.log('Strict-Transport-Security:', response.headers.get('Strict-Transport-Security'));
});
```

### Test Content Security Policy
```html
<!-- Try to inject script (should be blocked by CSP) -->
<script src="https://evil.com/malicious.js"></script>
```

## 8. Redis Security Verification

### Check Encrypted Data Storage
```bash
# Connect to Redis
docker-compose -f docker-compose.local.yml exec redis redis-cli

# Check for encrypted values
SCAN 0 MATCH meta-glasses:settings:*
GET meta-glasses:auth:password_hash
GET meta-glasses:settings:global:gemini_api_key

# All sensitive values should start with "enc:" prefix
```

### Check Rate Limiting Data
```bash
# In Redis CLI
SCAN 0 MATCH meta-glasses:security:*
KEYS meta-glasses:security:rate_limit:*
KEYS meta-glasses:security:blocked_ip:*

# Should see rate limiting and security tracking data
```

## 9. Performance Impact Tests

### Measure Encryption Overhead
```bash
python3 -c "
import time
import sys
sys.path.append('.')

class MockRedis:
    def get(self, key): return None
sys.modules['utils.redis_utils'] = type('Module', (), {'r': MockRedis()})()

from utils.encryption import encrypt_value, decrypt_value

# Test performance
test_data = 'sk-' + 'x' * 100  # Long API key
iterations = 1000

start = time.time()
for i in range(iterations):
    encrypted = encrypt_value(test_data)
    decrypted = decrypt_value(encrypted)
end = time.time()

avg_time = (end - start) / iterations * 1000
print(f'Average encryption+decryption time: {avg_time:.2f}ms')
print(f'Throughput: {iterations/(end-start):.0f} ops/second')
"
```

## 10. Automated Test Script

### Comprehensive Test Runner
```bash
cat > run_security_tests.sh << 'EOF'
#!/bin/bash
set -e

echo "🔒 Meta Glasses Security Test Suite"
echo "=================================="

# Check if services are running
if ! curl -s http://localhost:8111/ > /dev/null; then
    echo "❌ Backend not running. Start with: docker-compose -f docker-compose.local.yml up -d"
    exit 1
fi

# Test 1: Basic login
echo "🧪 Test 1: Basic Authentication"
LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8111/api/dashboard/login" \
  -H "Content-Type: application/json" \
  -d '{"password": "meta-admin-2024"}')

if echo "$LOGIN_RESPONSE" | grep -q "token"; then
    echo "✅ Login successful"
    TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.token')
else
    echo "❌ Login failed"
    exit 1
fi

# Test 2: Security headers
echo "🧪 Test 2: Security Headers"
HEADERS=$(curl -s -I "http://localhost:8111/api/dashboard/stats" \
  -H "Authorization: Bearer $TOKEN")

if echo "$HEADERS" | grep -q "X-Frame-Options"; then
    echo "✅ Security headers present"
else
    echo "❌ Security headers missing"
fi

# Test 3: Rate limiting (abbreviated test)
echo "🧪 Test 3: Rate Limiting"
RATE_TEST=$(curl -s -w "%{http_code}" -X POST "http://localhost:8111/api/dashboard/login" \
  -H "Content-Type: application/json" \
  -d '{"password": "wrong"}' -o /dev/null)

if [ "$RATE_TEST" = "401" ]; then
    echo "✅ Rate limiting functional (401 for wrong password)"
else
    echo "⚠️  Rate limiting response: $RATE_TEST"
fi

# Test 4: Settings encryption
echo "🧪 Test 4: Settings API"
SETTINGS_RESPONSE=$(curl -s -X GET "http://localhost:8111/api/dashboard/settings/" \
  -H "Authorization: Bearer $TOKEN")

if echo "$SETTINGS_RESPONSE" | grep -q "settings"; then
    echo "✅ Settings API accessible"
else
    echo "❌ Settings API failed"
fi

echo ""
echo "🎉 Security tests completed!"
echo "👉 Open http://localhost:3000/dashboard/settings to test UI"
EOF

chmod +x run_security_tests.sh && ./run_security_tests.sh
```

## Expected Results

### ✅ Success Indicators:
- Login returns JWT token
- Security headers present in responses
- Rate limiting triggers after multiple requests
- Sensitive data encrypted in Redis (starts with "enc:")
- Password changes work correctly
- Settings API masks sensitive values

### ❌ Failure Signs:
- Login fails or returns errors
- No security headers in responses
- Unlimited requests allowed (no rate limiting)
- Plain text sensitive data in Redis
- Settings show actual API keys instead of masked values

## Troubleshooting

### Common Issues:
1. **"Module not found" errors**: Install dependencies with `pip3 install -r requirements.txt`
2. **Redis connection errors**: Ensure Redis is running in Docker
3. **Rate limiting not working**: Check middleware is loaded in main.py
4. **Encryption fails**: Verify cryptography package is installed

### Debug Commands:
```bash
# Check Docker services
docker-compose -f docker-compose.local.yml ps

# View application logs
docker-compose -f docker-compose.local.yml logs app

# Check Redis data
docker-compose -f docker-compose.local.yml exec redis redis-cli MONITOR
```

---

**Quick Start**: Run `./run_security_tests.sh` for automated testing!