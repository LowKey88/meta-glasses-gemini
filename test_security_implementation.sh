#!/bin/bash

# Meta Glasses Security Implementation Test Suite
echo "🔒 Meta Glasses Security Implementation Test Suite"
echo "=================================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to print test results
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ $2${NC}"
        ((TESTS_FAILED++))
    fi
}

# Test 1: Check if services are running
echo -e "\n${BLUE}Test 1: Service Availability${NC}"
echo "----------------------------------------"

# Check backend
if curl -s http://localhost:8111/ > /dev/null; then
    print_result 0 "Backend service running"
else
    print_result 1 "Backend service not accessible"
    exit 1
fi

# Check dashboard
if curl -s http://localhost:3000/ > /dev/null; then
    print_result 0 "Dashboard service running"
else
    print_result 1 "Dashboard service not accessible"
fi

# Test 2: Authentication System
echo -e "\n${BLUE}Test 2: Authentication Security${NC}"
echo "----------------------------------------"

# Test login with correct password
LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8111/api/dashboard/login" \
  -H "Content-Type: application/json" \
  -d '{"password": "meta-admin-2024"}')

if echo "$LOGIN_RESPONSE" | grep -q "token"; then
    print_result 0 "Login with correct password successful"
    TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])" 2>/dev/null)
else
    print_result 1 "Login with correct password failed"
    echo "Response: $LOGIN_RESPONSE"
fi

# Test login with wrong password
WRONG_LOGIN=$(curl -s -w "%{http_code}" -X POST "http://localhost:8111/api/dashboard/login" \
  -H "Content-Type: application/json" \
  -d '{"password": "wrong-password"}' -o /dev/null)

if [ "$WRONG_LOGIN" = "401" ]; then
    print_result 0 "Login with wrong password correctly rejected"
else
    print_result 1 "Login with wrong password not properly rejected (got $WRONG_LOGIN)"
fi

# Test 3: Security Headers
echo -e "\n${BLUE}Test 3: Security Headers${NC}"
echo "----------------------------------------"

if [ ! -z "$TOKEN" ]; then
    HEADERS=$(curl -s -I "http://localhost:8111/api/dashboard/stats" \
      -H "Authorization: Bearer $TOKEN")
    
    # Check for security headers
    if echo "$HEADERS" | grep -qi "X-Frame-Options"; then
        print_result 0 "X-Frame-Options header present"
    else
        print_result 1 "X-Frame-Options header missing"
    fi
    
    if echo "$HEADERS" | grep -qi "X-Content-Type-Options"; then
        print_result 0 "X-Content-Type-Options header present"
    else
        print_result 1 "X-Content-Type-Options header missing"
    fi
    
    if echo "$HEADERS" | grep -qi "Strict-Transport-Security"; then
        print_result 0 "Strict-Transport-Security header present"
    else
        print_result 1 "Strict-Transport-Security header missing"
    fi
else
    print_result 1 "Cannot test security headers - no valid token"
fi

# Test 4: Settings API and Encryption
echo -e "\n${BLUE}Test 4: Settings API and Encryption${NC}"
echo "----------------------------------------"

if [ ! -z "$TOKEN" ]; then
    # Test settings endpoint
    SETTINGS_RESPONSE=$(curl -s -X GET "http://localhost:8111/api/dashboard/settings/" \
      -H "Authorization: Bearer $TOKEN")
    
    if echo "$SETTINGS_RESPONSE" | grep -q "settings"; then
        print_result 0 "Settings API accessible"
        
        # Check if sensitive values are masked
        if echo "$SETTINGS_RESPONSE" | grep -q "\*\*\*"; then
            print_result 0 "Sensitive values properly masked"
        else
            print_result 1 "Sensitive values not masked"
        fi
    else
        print_result 1 "Settings API not accessible"
    fi
    
    # Test updating a setting (encryption test)
    UPDATE_RESPONSE=$(curl -s -X PUT "http://localhost:8111/api/dashboard/settings/gemini_api_key" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"value": "AIza_test_key_123456789"}')
    
    if echo "$UPDATE_RESPONSE" | grep -q "success"; then
        print_result 0 "Settings update successful"
    else
        print_result 1 "Settings update failed"
    fi
else
    print_result 1 "Cannot test settings API - no valid token"
fi

# Test 5: Rate Limiting
echo -e "\n${BLUE}Test 5: Rate Limiting${NC}"
echo "----------------------------------------"

echo "Testing rate limiting (this may take a moment)..."

# Make multiple rapid requests to trigger rate limiting
RATE_LIMIT_TRIGGERED=false
for i in {1..15}; do
    RESPONSE=$(curl -s -w "%{http_code}" -X POST "http://localhost:8111/api/dashboard/login" \
      -H "Content-Type: application/json" \
      -d '{"password": "wrong-password"}' -o /dev/null)
    
    if [ "$RESPONSE" = "429" ]; then
        RATE_LIMIT_TRIGGERED=true
        break
    fi
    
    # Small delay to avoid overwhelming
    sleep 0.1
done

if [ "$RATE_LIMIT_TRIGGERED" = true ]; then
    print_result 0 "Rate limiting working (429 response received)"
else
    print_result 1 "Rate limiting not triggered"
fi

# Test 6: Redis Encryption Check
echo -e "\n${BLUE}Test 6: Redis Data Encryption${NC}"
echo "----------------------------------------"

# Check if Redis contains encrypted data
REDIS_ENCRYPTED=$(docker-compose -f docker-compose.local.yml exec -T redis redis-cli SCAN 0 MATCH "meta-glasses:settings:*" | grep -v "meta-glasses:settings:audit" | head -5)

if [ ! -z "$REDIS_ENCRYPTED" ]; then
    # Check if any settings are encrypted
    ENCRYPTED_FOUND=false
    for key in $REDIS_ENCRYPTED; do
        if [ "$key" != "0" ]; then
            VALUE=$(docker-compose -f docker-compose.local.yml exec -T redis redis-cli GET "$key")
            if echo "$VALUE" | grep -q "^enc:"; then
                ENCRYPTED_FOUND=true
                break
            fi
        fi
    done
    
    if [ "$ENCRYPTED_FOUND" = true ]; then
        print_result 0 "Encrypted data found in Redis"
    else
        print_result 1 "No encrypted data found in Redis"
    fi
else
    print_result 1 "No settings data found in Redis"
fi

# Test 7: Password Security
echo -e "\n${BLUE}Test 7: Password Security${NC}"
echo "----------------------------------------"

# Test password change API
if [ ! -z "$TOKEN" ]; then
    PASS_CHANGE_RESPONSE=$(curl -s -X POST "http://localhost:8111/api/dashboard/settings/change-password" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"current_password": "meta-admin-2024", "new_password": "new-secure-password-123"}')
    
    if echo "$PASS_CHANGE_RESPONSE" | grep -q "success"; then
        print_result 0 "Password change API working"
        
        # Test login with new password
        NEW_LOGIN=$(curl -s -X POST "http://localhost:8111/api/dashboard/login" \
          -H "Content-Type: application/json" \
          -d '{"password": "new-secure-password-123"}')
        
        if echo "$NEW_LOGIN" | grep -q "token"; then
            print_result 0 "Login with new password successful"
            
            # Change back to original password for other tests
            NEW_TOKEN=$(echo "$NEW_LOGIN" | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])" 2>/dev/null)
            curl -s -X POST "http://localhost:8111/api/dashboard/settings/change-password" \
              -H "Authorization: Bearer $NEW_TOKEN" \
              -H "Content-Type: application/json" \
              -d '{"current_password": "new-secure-password-123", "new_password": "meta-admin-2024"}' > /dev/null
        else
            print_result 1 "Login with new password failed"
        fi
    else
        print_result 1 "Password change API not working"
    fi
else
    print_result 1 "Cannot test password change - no valid token"
fi

# Final Results
echo -e "\n${BLUE}Test Summary${NC}"
echo "============================================"
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 All security tests passed!${NC}"
    echo -e "${GREEN}✅ Security implementation is working correctly${NC}"
    exit 0
else
    echo -e "\n${YELLOW}⚠️  Some tests failed. Please review the results above.${NC}"
    exit 1
fi