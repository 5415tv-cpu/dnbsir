#!/bin/bash
set -e

echo "=== 1단계: 공격 IP 즉시 차단 ==="
iptables -I INPUT -s 34.125.246.29 -j DROP 2>/dev/null && echo "IP 차단: 34.125.246.29" || echo "이미 차단됨"

echo "=== 2단계: fail2ban 설치 ==="
apt-get install -y fail2ban -qq 2>/dev/null || true

cat > /etc/fail2ban/filter.d/env-scanner.conf << 'FILTEREOF'
[Definition]
failregex = <HOST> .* "(GET|POST|HEAD) /.*\.env.* HTTP
            <HOST> .* "(GET|POST|HEAD) /.git/.* HTTP
            <HOST> .* "(GET|POST|HEAD) /wp-admin.* HTTP
            <HOST> .* "(GET|POST|HEAD) /phpMyAdmin.* HTTP
ignoreregex =
FILTEREOF

cat > /etc/fail2ban/jail.d/env-scanner.conf << 'JAILEOF'
[env-scanner]
enabled  = true
port     = http,https
filter   = env-scanner
logpath  = /var/log/nginx/access.log
maxretry = 3
findtime = 60
bantime  = 86400
JAILEOF

systemctl enable fail2ban
systemctl restart fail2ban
sleep 2
echo "fail2ban 상태: $(systemctl is-active fail2ban)"

echo "=== 3단계: Nginx 민감 파일 차단 ==="
cat > /etc/nginx/conf.d/block_sensitive.conf << 'NGINXEOF'
# 민감 경로 자동 차단 (444 = 응답 없이 연결 끊기)
geo $blocked_ip {
    default 0;
    34.125.246.29 1;
}
NGINXEOF

# 메인 nginx 설정에 deny 추가 (중복 방지)
for SITE in /etc/nginx/sites-enabled/*; do
    if ! grep -q "\.env" "$SITE" 2>/dev/null; then
        # server { 블록 첫 번째 location 앞에 삽입
        sed -i '/^    server_name/a\    location ~ /\\.env { deny all; return 444; }\n    location ~ /\\.git { deny all; return 444; }\n    location ~ /(wp-admin|phpMyAdmin|phpmyadmin) { deny all; return 444; }' "$SITE" 2>/dev/null || true
    fi
done

nginx -t && systemctl reload nginx
echo "nginx 재로드 완료"

echo "=== 4단계: iptables 영구 저장 ==="
mkdir -p /etc/iptables
iptables-save > /etc/iptables/rules.v4
echo "저장 완료"

echo ""
echo "=== 최종 차단 상태 ==="
iptables -L INPUT -n | grep -v "^$" | head -15
echo ""
fail2ban-client status 2>/dev/null || true
