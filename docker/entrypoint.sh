#!/bin/sh
# Container start-up: configure for the host, prepare the database, then serve.
set -e
cd /var/www/html

# Hosts like Render pass the port to listen on in $PORT.
PORT="${PORT:-80}"
sed -ri "s/^Listen [0-9]+/Listen ${PORT}/" /etc/apache2/ports.conf
sed -ri "s/<VirtualHost \*:[0-9]+>/<VirtualHost *:${PORT}>/" /etc/apache2/sites-available/000-default.conf

# Managed MySQL (e.g. Aiven) requires TLS with the provider's CA certificate.
if [ -n "$DB_CA_CERT" ]; then
    printf '%s\n' "$DB_CA_CERT" > /tmp/db-ca.pem
    export MYSQL_ATTR_SSL_CA=/tmp/db-ca.pem
fi

php artisan config:cache
php artisan route:cache
php artisan migrate --force
php artisan aimeos:setup
php artisan demo:seed

# Artisan ran as root; Apache runs as www-data.
chown -R www-data:www-data storage bootstrap/cache

exec apache2-foreground
